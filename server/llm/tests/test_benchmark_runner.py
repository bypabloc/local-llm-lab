from llm.benchmark.runner import run_benchmark

from .fakes import FakeBackend, make_model_config


def test_run_benchmark_devuelve_resultado_con_metricas() -> None:
    backend = FakeBackend(config=make_model_config(), reply="uno dos tres")

    result = run_benchmark("fake-model", backend, system="sys", user="hola")

    assert result.model_name == "fake-model"
    assert result.completion_tokens == 3
    assert result.total_seconds == result.prefill_seconds + result.generation_seconds
    assert result.text == "uno dos tres"


def test_run_benchmark_sin_tokens_completados_no_divide_por_cero() -> None:
    backend = FakeBackend(config=make_model_config(), reply="")

    result = run_benchmark("fake-model", backend, system="sys", user="hola")

    assert result.completion_tokens == 0
    assert result.tokens_per_second == 0.0
    assert result.generation_seconds == 0.0


def test_benchmark_result_rating_fluido_sobre_umbral() -> None:
    backend = FakeBackend(config=make_model_config(), reply="x")
    result = run_benchmark("fake-model", backend, system="", user="")

    assert result.rating in {"fluido", "aceptable", "lento"}
