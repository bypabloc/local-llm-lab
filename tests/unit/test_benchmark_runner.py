from core.benchmark.runner import run_benchmark
from tests.unit.fakes import FakeBackend, make_model_config


def test_run_benchmark_calcula_tokens_por_segundo() -> None:
    config = make_model_config("fake")
    backend = FakeBackend(config, reply="una dos tres cuatro cinco")

    result = run_benchmark("fake", backend, system="sos un asistente", user="hola")

    assert result.model_name == "fake"
    assert result.completion_tokens == 5
    assert result.tokens_per_second >= 0


def test_run_benchmark_rating_lento_si_no_hay_completion() -> None:
    config = make_model_config("fake")
    backend = FakeBackend(config, reply="")

    result = run_benchmark("fake", backend, system="", user="hola")

    assert result.completion_tokens == 0
    assert result.rating == "lento"
