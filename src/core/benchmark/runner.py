import time
from dataclasses import dataclass

from core.backends.protocol import LLMBackend

# Umbrales de .claude/rules/research-context.md
FLUENT_TOK_S = 10.0
ACCEPTABLE_TOK_S = 5.0


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    model_name: str
    prefill_seconds: float
    generation_seconds: float
    prompt_tokens: int
    completion_tokens: int
    text: str
    no_think: bool

    @property
    def total_seconds(self) -> float:
        return self.prefill_seconds + self.generation_seconds

    @property
    def tokens_per_second(self) -> float:
        if self.generation_seconds <= 0:
            return 0.0
        return self.completion_tokens / self.generation_seconds

    @property
    def rating(self) -> str:
        tok_s = self.tokens_per_second
        if tok_s >= FLUENT_TOK_S:
            return "fluido"
        if tok_s >= ACCEPTABLE_TOK_S:
            return "aceptable"
        return "lento"


def run_benchmark(
    model_name: str,
    backend: LLMBackend,
    system: str,
    user: str,
    max_tokens: int = 1024,
    no_think: bool = False,
) -> BenchmarkResult:
    prefill_start = time.perf_counter()
    result = backend.generate(
        system=system, user=user, max_tokens=max_tokens, no_think=no_think
    )
    total_elapsed = time.perf_counter() - prefill_start

    # llama-cpp-python no expone prefill/decode por separado en la API de
    # alto nivel create_chat_completion; se aproxima el prefill como el
    # tiempo total menos el tiempo estimado de generación por token, usando
    # el conteo real de tokens completados. Ver .claude/agents/llm-perf-reviewer.md
    # antes de confiar en esta cifra para decisiones críticas.
    completion_tokens = result.completion_tokens
    if completion_tokens > 0:
        avg_token_time = total_elapsed / (completion_tokens + 1)
        prefill_seconds = avg_token_time
        generation_seconds = total_elapsed - prefill_seconds
    else:
        prefill_seconds = total_elapsed
        generation_seconds = 0.0

    return BenchmarkResult(
        model_name=model_name,
        prefill_seconds=prefill_seconds,
        generation_seconds=generation_seconds,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=completion_tokens,
        text=result.text,
        no_think=no_think,
    )
