import threading

from core.router.llm_router import LLMRouter
from llm.services.device import build_router

_lock = threading.Lock()
_routers: dict[str, LLMRouter] = {}


def get_router(device: str) -> LLMRouter:
    if device in _routers:
        return _routers[device]
    with _lock:
        if device not in _routers:
            _routers[device] = build_router(device)
        return _routers[device]


def reset() -> None:
    """Solo para tests: descarta los routers cacheados sin liberar backends."""
    with _lock:
        _routers.clear()
