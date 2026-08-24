import dataclasses

import pytest

from local_llm_lab.backends.errors import BackendLoadError
from local_llm_lab.backends.llama_cpp_backend import LlamaCppBackend
from tests.unit.fakes import make_model_config


def test_carga_falla_si_modelo_no_existe_en_disco() -> None:
    config = make_model_config("no-descargado")

    with pytest.raises(BackendLoadError, match="no encontrado"):
        LlamaCppBackend(config)


def test_carga_falla_si_pide_gpu_sin_soporte_compilado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = dataclasses.replace(make_model_config("gpu-model"), n_gpu_layers=-1)

    monkeypatch.setattr(
        "llama_cpp.llama_supports_gpu_offload", lambda: False, raising=False
    )

    with pytest.raises(BackendLoadError, match="CUDA/Metal"):
        LlamaCppBackend._load(config)
