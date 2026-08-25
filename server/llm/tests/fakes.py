from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from core.backends.protocol import ChatMessage, GenerationResult
from core.config.models import ModelConfig


@dataclass
class FakeBackend:
    """Copia adaptada de tests/unit/fakes.py, sin acoplar server/ a tests/ de core."""

    config: ModelConfig
    reply: str = "ok"
    calls: list[tuple[str, str]] = field(default_factory=list)
    stream_calls: list[list[ChatMessage]] = field(default_factory=list)
    closed: bool = False

    def generate(
        self, system: str, user: str, max_tokens: int, no_think: bool = False
    ) -> GenerationResult:
        self.calls.append((system, user))
        return GenerationResult(
            text=self.reply,
            prompt_tokens=len(f"{system} {user}".split()),
            completion_tokens=len(self.reply.split()),
        )

    def stream_chat(
        self, messages: list[ChatMessage], max_tokens: int
    ) -> Iterator[str]:
        self.stream_calls.append(list(messages))
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
