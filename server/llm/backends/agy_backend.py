import json
import logging
import subprocess
from collections.abc import Iterator

from llm.backends.protocol import ChatMessage, GenerationResult
from llm.config.models import ModelConfig

logger = logging.getLogger(__name__)

# ponytail: aproximación grosera (chars/4), no vale la pena tokenizar de
# verdad para un backend cuyo único uso real de count_tokens es mostrar un
# número orientativo en la UI antes de generar.
_CHARS_PER_TOKEN_ESTIMATE = 4


class AgyBackend:
    """Adaptador sobre el CLI `agy` (Antigravity), autenticado por OAuth con
    la suscripción Google AI Pro/Ultra del usuario. No corre en el proceso
    Python: lanza `agy` como subprocess por cada turno. Ver
    .claude/rules/ (o pedir contexto) sobre por qué no hay tok/s reales de
    inferencia local aquí — la medición de duración/usage viene del propio
    CLI, no de este backend."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config

    def _run_stream_json(self, prompt: str) -> Iterator[str]:
        process = subprocess.Popen(
            ["agy", "--print", prompt, "--output-format", "stream-json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdout is not None
        try:
            yield from process.stdout
        finally:
            process.stdout.close()
            process.wait()

    @staticmethod
    def _build_prompt(system: str, messages: list[ChatMessage]) -> str:
        parts = [system] if system else []
        parts.extend(msg["content"] for msg in messages)
        return "\n\n".join(parts)

    def generate(
        self, system: str, user: str, max_tokens: int, no_think: bool = False
    ) -> GenerationResult:
        user_content = f"{user} /no_think" if no_think else user
        prompt = self._build_prompt(system, [{"role": "user", "content": user_content}])
        text_parts: list[str] = []
        usage = {"input_tokens": 0, "output_tokens": 0}
        for line in self._run_stream_json(prompt):
            event, delta, line_usage = self._parse_line(line)
            if delta:
                text_parts.append(delta)
            if line_usage:
                usage = line_usage
        return GenerationResult(
            text="".join(text_parts),
            prompt_tokens=usage["input_tokens"],
            completion_tokens=usage["output_tokens"],
        )

    def stream_chat(
        self, messages: list[ChatMessage], max_tokens: int
    ) -> Iterator[str]:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        rest = [m for m in messages if m["role"] != "system"]
        prompt = self._build_prompt(system, rest)
        for line in self._run_stream_json(prompt):
            _, delta, _ = self._parse_line(line)
            if delta:
                yield delta

    @staticmethod
    def _parse_line(line: str) -> tuple[str | None, str | None, dict[str, int] | None]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("agy stream: línea no-JSON ignorada: %r", line)
            return None, None, None
        step_update = payload.get("step_update")
        if not step_update or step_update.get("step_type") != "agent_response":
            return payload.get("event"), None, None
        return (
            payload.get("event"),
            step_update.get("text_delta"),
            step_update.get("usage"),
        )

    def count_tokens(self, text: str) -> int:
        return len(text) // _CHARS_PER_TOKEN_ESTIMATE

    def close(self) -> None:
        """No-op: no hay proceso persistente que cerrar (subprocess por turno)."""
