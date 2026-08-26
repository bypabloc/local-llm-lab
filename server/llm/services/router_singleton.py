import threading
from pathlib import Path

from llm.router.llm_router import LLMRouter
from llm.services.device import build_router

_lock = threading.Lock()
_routers: dict[tuple[str, str | None], LLMRouter] = {}


def get_router(device: str, models_dir: Path | None = None) -> LLMRouter:
    key = (device, str(models_dir) if models_dir else None)
    if key in _routers:
        return _routers[key]
    with _lock:
        if key not in _routers:
            _routers[key] = build_router(device, models_dir)
        return _routers[key]


def reset() -> None:
    """Solo para tests: descarta los routers cacheados sin liberar backends."""
    with _lock:
        _routers.clear()
