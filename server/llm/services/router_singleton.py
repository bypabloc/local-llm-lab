import logging
import threading
from pathlib import Path

from llm.router.llm_router import LLMRouter
from llm.services.device import build_router

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_routers: dict[tuple[str, str | None], LLMRouter] = {}


def get_router(device: str, models_dir: Path | None = None) -> LLMRouter:
    key = (device, str(models_dir) if models_dir else None)
    logger.debug("get_router: key=%s cacheado=%s", key, key in _routers)
    if key in _routers:
        return _routers[key]
    with _lock:
        if key not in _routers:
            try:
                logger.info("get_router: construyendo router nuevo para %s", key)
                _routers[key] = build_router(device, models_dir)
            except Exception:
                logger.exception("get_router: fallo construyendo router para %s", key)
                raise
        return _routers[key]


def reset() -> None:
    """Solo para tests: descarta los routers cacheados sin liberar backends."""
    with _lock:
        _routers.clear()
