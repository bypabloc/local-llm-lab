from collections.abc import Iterator
from pathlib import Path
from typing import Any

from local_llm_lab.backends.errors import BackendLoadError
from local_llm_lab.backends.protocol import ChatMessage, GenerationResult
from local_llm_lab.config.models import ModelConfig


class LlamaCppBackend:
    """Adaptador sobre llama-cpp-python. Implementa LLMBackend."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._llm = self._load(config)

    @staticmethod
    def _load(config: ModelConfig) -> Any:
        from llama_cpp import Llama, llama_supports_gpu_offload

        if config.n_gpu_layers != 0 and not llama_supports_gpu_offload():
            raise BackendLoadError(
                "se pidió GPU pero llama-cpp-python está compilado sin soporte "
                "CUDA/Metal (build CPU-only). Recompilar con "
                "CMAKE_ARGS='-DGGML_CUDA=on' pip install llama-cpp-python "
                "--force-reinstall --no-cache-dir. "
                "Ver .claude/rules/research-context.md"
            )

        if not Path(config.path).exists():
            raise BackendLoadError(
                f"modelo '{config.name}' no encontrado en {config.path}"
            )

        return Llama(
            model_path=str(config.path),
            n_ctx=config.n_ctx,
            n_threads=config.n_threads,
            n_gpu_layers=config.n_gpu_layers,
            verbose=False,
        )

    def generate(
        self, system: str, user: str, max_tokens: int, no_think: bool = False
    ) -> GenerationResult:
        # ponytail: /no_think es el switch documentado por Qwen para desactivar
        # thinking sin tocar la API; otros modelos lo ignoran como texto normal.
        user_content = f"{user} /no_think" if no_think else user
        response = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
        )
        choice = response["choices"][0]["message"]["content"]
        usage = response["usage"]
        return GenerationResult(
            text=choice,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
        )

    def stream_chat(
        self, messages: list[ChatMessage], max_tokens: int
    ) -> Iterator[str]:
        stream = self._llm.create_chat_completion(
            messages=list(messages),
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk["choices"][0]["delta"]
            content = delta.get("content")
            if content:
                yield content

    def count_tokens(self, text: str) -> int:
        return len(self._llm.tokenize(text.encode("utf-8")))

    def close(self) -> None:
        """Libera la VRAM/RAM del modelo cargado. Ver LLMRouter.unload."""
        self._llm.close()
