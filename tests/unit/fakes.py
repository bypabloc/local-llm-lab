from collections.abc import Iterator
from pathlib import Path

from core.backends.protocol import ChatMessage, GenerationResult
from core.config.models import ModelConfig


class FakeBackend:
    """Implementa LLMBackend sin cargar ningún modelo real. Solo para tests."""

    def __init__(self, config: ModelConfig, reply: str = "ok") -> None:
        self.config = config
        self.reply = reply
        self.calls: list[tuple[str, str]] = []
        self.closed = False

    def generate(
        self, system: str, user: str, max_tokens: int, no_think: bool = False
    ) -> GenerationResult:
        self.calls.append((system, user))
        return GenerationResult(
            text=self.reply,
            prompt_tokens=len(system.split()) + len(user.split()),
            completion_tokens=len(self.reply.split()),
        )

    def stream_chat(
        self, messages: list[ChatMessage], max_tokens: int
    ) -> Iterator[str]:
        self.calls.append((messages[-2]["content"], messages[-1]["content"]))
        # ponytail: yield char por char en vez de por palabra, para que
        # "".join(chunks) reconstruya el texto exacto sin perder espacios
        # — refleja el contrato real de llama-cpp-python (fragmentos crudos).
        yield from self.reply

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def close(self) -> None:
        self.closed = True


def make_model_config(name: str = "fake-model") -> ModelConfig:
    return ModelConfig(
        name=name,
        path=Path(f"models/{name}.gguf"),
        n_ctx=4096,
        n_threads=4,
        n_gpu_layers=0,
        license="Apache-2.0",
    )
