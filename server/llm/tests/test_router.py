import pytest

from llm.router.errors import ModelNotFoundError
from llm.router.llm_router import LLMRouter

from .fakes import FakeBackend, make_model_config


def test_router_resuelve_modelo_por_nombre_logico() -> None:
    config = make_model_config("gemma4-e2b")
    router = LLMRouter({"gemma4-e2b": config}, backend_factory=FakeBackend)

    backend = router.get("gemma4-e2b")

    assert isinstance(backend, FakeBackend)
    assert backend.config == config


def test_router_lanza_model_not_found_si_no_existe_en_config() -> None:
    router = LLMRouter({}, backend_factory=FakeBackend)

    with pytest.raises(ModelNotFoundError):
        router.get("no-existe")


def test_router_cachea_backend_entre_llamadas() -> None:
    config = make_model_config("qwen3-4b")
    router = LLMRouter({"qwen3-4b": config}, backend_factory=FakeBackend)

    first = router.get("qwen3-4b")
    second = router.get("qwen3-4b")

    assert first is second


def test_router_unload_libera_y_permite_recargar_backend_nuevo() -> None:
    config = make_model_config("qwen3-4b")
    router = LLMRouter({"qwen3-4b": config}, backend_factory=FakeBackend)
    first = router.get("qwen3-4b")

    router.unload("qwen3-4b")
    second = router.get("qwen3-4b")

    assert isinstance(first, FakeBackend)
    assert first.closed is True
    assert second is not first


def test_router_unload_de_modelo_no_cargado_no_falla() -> None:
    router = LLMRouter({}, backend_factory=FakeBackend)

    router.unload("nunca-cargado")


def test_router_available_models_devuelve_nombres_ordenados() -> None:
    configs = {
        "zeta": make_model_config("zeta"),
        "alfa": make_model_config("alfa"),
    }
    router = LLMRouter(configs, backend_factory=FakeBackend)

    assert router.available_models() == ["alfa", "zeta"]
