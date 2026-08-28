import pytest

from llm.services.device import (
    InvalidDeviceError,
    build_router,
    resolve_device,
)


def test_resolve_device_pasa_cpu_directo() -> None:
    assert resolve_device("cpu") == "cpu"


def test_resolve_device_pasa_gpu_directo() -> None:
    assert resolve_device("gpu") == "gpu"


def test_resolve_device_autodetecta_si_es_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llama_cpp.llama_supports_gpu_offload", lambda: True, raising=False
    )
    assert resolve_device(None) == "gpu"


def test_resolve_device_lanza_si_valor_invalido() -> None:
    with pytest.raises(InvalidDeviceError, match="'raro'"):
        resolve_device("raro")


def test_build_router_expone_los_modelos_configurados() -> None:
    router = build_router("cpu")

    assert set(router.available_models()) == {
        "qwen3-4b",
        "qwen3-8b",
        "phi4-mini",
        "gemma4-e2b",
        "gemma4-e4b",
    }


def test_build_router_es_independiente_por_llamada() -> None:
    assert build_router("cpu") is not build_router("cpu")


def test_build_router_gpu_fuerza_n_gpu_layers_full_offload() -> None:
    from llm.services.device import resolve_model_configs

    configs = resolve_model_configs("gpu")

    assert all(config.n_gpu_layers == -1 for config in configs.values())


def test_build_router_cpu_respeta_n_gpu_layers_del_toml() -> None:
    from llm.config.models import load_model_configs
    from llm.services.device import resolve_model_configs

    configs = resolve_model_configs("cpu")
    original = load_model_configs()

    assert configs["gemma4-e2b"].n_gpu_layers == original["gemma4-e2b"].n_gpu_layers
