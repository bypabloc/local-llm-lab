from pathlib import Path

import pytest

from core.backends.llama_cpp_backend import LlamaCppBackend
from core.config.models import load_model_configs

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _model_available(name: str) -> bool:
    configs = load_model_configs(project_root=PROJECT_ROOT)
    return name in configs and configs[name].path.exists()


@pytest.mark.skipif(
    not _model_available("qwen3-4b"),
    reason="modelo qwen3-4b GGUF no descargado en models/",
)
def test_genera_respuesta_con_modelo_real() -> None:
    configs = load_model_configs(project_root=PROJECT_ROOT)
    backend = LlamaCppBackend(configs["qwen3-4b"])

    result = backend.generate(
        system="Sos un asistente breve.", user="Decí 'hola' y nada más.", max_tokens=32
    )

    assert result.text
    assert result.completion_tokens > 0
