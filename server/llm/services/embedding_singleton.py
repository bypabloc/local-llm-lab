import logging
import threading
from pathlib import Path

from llm.backends.embedding_backend import EmbeddingBackend
from llm.backends.errors import BackendLoadError
from llm.config.embedding_model import embedding_model_config
from llm.memory.store import EmbedFn

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_backend: EmbeddingBackend | None = None
_load_failed = False


def get_embed_fn(models_dir: Path) -> EmbedFn | None:
    """Devuelve una función embed(text) -> vector, o None si el modelo de
    embeddings no está descargado — la memoria sigue funcionando solo con
    búsqueda léxica (FTS5) en ese caso, degradación elegante, no error."""
    global _backend, _load_failed
    if _backend is not None:
        return _backend.embed
    if _load_failed:
        return None
    with _lock:
        if _backend is not None:
            return _backend.embed
        if _load_failed:
            return None
        try:
            logger.info("get_embed_fn: cargando modelo de embeddings")
            _backend = EmbeddingBackend(embedding_model_config(models_dir))
        except BackendLoadError:
            logger.info(
                "get_embed_fn: modelo de embeddings no descargado, "
                "recall semántico deshabilitado"
            )
            _load_failed = True
            return None
    return _backend.embed


def reset() -> None:
    """Solo para tests: descarta el backend cacheado sin liberar VRAM/RAM."""
    global _backend, _load_failed
    with _lock:
        _backend = None
        _load_failed = False
