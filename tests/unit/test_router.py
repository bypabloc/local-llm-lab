import pytest

from core.router.errors import ModelNotFoundError
from core.router.llm_router import LLMRouter
from tests.unit.fakes import FakeBackend, make_model_config


def test_router_resuelve_modelo_por_nombre_logico() -> None:
    config = make_model_config("qwen3-4b")
    router = LLMRouter({"qwen3-4b": config}, backend_factory=FakeBackend)

    backend = router.get("qwen3-4b")

    assert isinstance(backend, FakeBackend)
    assert backend.config.name == "qwen3-4b"


def test_router_lanza_model_not_found_si_no_existe_en_config() -> None:
    router = LLMRouter({}, backend_factory=FakeBackend)

    with pytest.raises(ModelNotFoundError):
        router.get("no-existe")


def test_router_cachea_backend_ya_cargado() -> None:
    config = make_model_config("qwen3-4b")
    router = LLMRouter({"qwen3-4b": config}, backend_factory=FakeBackend)

    first = router.get("qwen3-4b")
    second = router.get("qwen3-4b")

    assert first is second


def test_available_models_lista_nombres_ordenados() -> None:
    configs = {
        "phi4-mini": make_model_config("phi4-mini"),
        "qwen3-4b": make_model_config("qwen3-4b"),
    }
    router = LLMRouter(configs, backend_factory=FakeBackend)

    assert router.available_models() == ["phi4-mini", "qwen3-4b"]


def test_unload_libera_backend_y_siguiente_get_recarga() -> None:
    config = make_model_config("qwen3-4b")
    router = LLMRouter({"qwen3-4b": config}, backend_factory=FakeBackend)

    first = router.get("qwen3-4b")
    router.unload("qwen3-4b")
    second = router.get("qwen3-4b")

    assert first is not second
    assert first.closed is True
    assert second.closed is False


def test_unload_de_modelo_no_cargado_no_falla() -> None:
    router = LLMRouter({}, backend_factory=FakeBackend)

    router.unload("nunca-cargado")
