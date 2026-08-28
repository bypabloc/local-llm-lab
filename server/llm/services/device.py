import dataclasses
import logging
import os
from pathlib import Path

from llm.backends.llama_cpp_backend import LlamaCppBackend
from llm.config.models import ModelConfig, load_model_configs
from llm.router.llm_router import LLMRouter

logger = logging.getLogger(__name__)

# ponytail: -1 = todas las capas a GPU (offload completo), igual que cli/main.py.
_GPU_LAYERS_FULL_OFFLOAD = -1


class InvalidDeviceError(ValueError):
    """El valor de device pedido no es 'cpu' ni 'gpu'."""


def detect_device() -> str:
    """gpu si llama-cpp-python tiene soporte CUDA/Metal compilado, sino cpu."""
    from llama_cpp import llama_supports_gpu_offload

    device = "gpu" if llama_supports_gpu_offload() else "cpu"
    logger.debug("detect_device -> %s", device)
    return device


def resolve_device(device: str | None) -> str:
    if device is None:
        return detect_device()
    if device not in ("cpu", "gpu"):
        logger.error("resolve_device: valor invalido recibido=%r", device)
        raise InvalidDeviceError(f"device debe ser 'cpu' o 'gpu', recibido '{device}'")
    return device


def resolve_project_root() -> Path | None:
    """Raíz del repo (donde vive models/) — override explícito para el
    sidecar empaquetado, donde __file__ apunta a la carpeta temporal de
    PyInstaller y no al checkout real del repo."""
    value = os.environ.get("LLM_LAB_PROJECT_ROOT")
    root = Path(value) if value else None
    logger.debug("resolve_project_root -> %s", root)
    return root


def resolve_model_configs(
    device: str, models_dir: Path | None = None
) -> dict[str, ModelConfig]:
    logger.debug("resolve_model_configs: device=%s models_dir=%s", device, models_dir)
    try:
        configs = load_model_configs(
            project_root=resolve_project_root(), models_dir=models_dir
        )
    except Exception:
        logger.exception(
            "resolve_model_configs: fallo cargando configs (models_dir=%s)",
            models_dir,
        )
        raise
    if device == "gpu":
        configs = {
            name: dataclasses.replace(config, n_gpu_layers=_GPU_LAYERS_FULL_OFFLOAD)
            for name, config in configs.items()
        }
    logger.debug("resolve_model_configs -> %d configs", len(configs))
    return configs


def build_router(device: str, models_dir: Path | None = None) -> LLMRouter:
    logger.info("build_router: device=%s models_dir=%s", device, models_dir)
    return LLMRouter(
        resolve_model_configs(device, models_dir), backend_factory=LlamaCppBackend
    )
