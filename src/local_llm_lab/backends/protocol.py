from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol, TypedDict


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    prompt_tokens: int
    completion_tokens: int


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMBackend(Protocol):
    """Interfaz mínima que el router y el benchmark necesitan de un modelo cargado."""

    def generate(
        self, system: str, user: str, max_tokens: int, no_think: bool = False
    ) -> GenerationResult: ...

    def stream_chat(
        self, messages: list[ChatMessage], max_tokens: int
    ) -> Iterator[str]: ...

    def count_tokens(self, text: str) -> int: ...
