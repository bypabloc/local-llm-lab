import dataclasses
import os
from pathlib import Path

from core.backends.llama_cpp_backend import LlamaCppBackend
from core.config.models import ModelConfig, load_model_configs
from core.router.llm_router import LLMRouter

# ponytail: -1 = todas las capas a GPU (offload completo), igual que cli/main.py.
_GPU_LAYERS_FULL_OFFLOAD = -1


class InvalidDeviceError(ValueError):
    """El valor de device pedido no es 'cpu' ni 'gpu'."""


def detect_device() -> str:
    """gpu si llama-cpp-python tiene soporte CUDA/Metal compilado, sino cpu."""
    from llama_cpp import llama_supports_gpu_offload

    return "gpu" if llama_supports_gpu_offload() else "cpu"


def resolve_device(device: str | None) -> str:
    if device is None:
        return detect_device()
    if device not in ("cpu", "gpu"):
        raise InvalidDeviceError(f"device debe ser 'cpu' o 'gpu', recibido '{device}'")
    return device


def resolve_project_root() -> Path | None:
    """Raíz del repo (donde vive models/) — override explícito para el
    sidecar empaquetado, donde __file__ apunta a la carpeta temporal de
    PyInstaller y no al checkout real del repo."""
    value = os.environ.get("LLM_LAB_PROJECT_ROOT")
    return Path(value) if value else None


def resolve_model_configs(device: str) -> dict[str, ModelConfig]:
    configs = load_model_configs(project_root=resolve_project_root())
    if device == "gpu":
        configs = {
            name: dataclasses.replace(config, n_gpu_layers=_GPU_LAYERS_FULL_OFFLOAD)
            for name, config in configs.items()
        }
    return configs


def build_router(device: str) -> LLMRouter:
    return LLMRouter(resolve_model_configs(device), backend_factory=LlamaCppBackend)
