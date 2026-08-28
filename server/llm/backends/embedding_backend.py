import logging
from pathlib import Path
from typing import Any

from llm.backends.errors import BackendLoadError
from llm.config.models import ModelConfig

logger = logging.getLogger(__name__)


class EmbeddingBackend:
    """Adaptador sobre llama-cpp-python en modo embedding (Qwen3-Embedding)."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._llm = self._load(config)

    @staticmethod
    def _load(config: ModelConfig) -> Any:
        from llama_cpp import Llama

        if not Path(config.path).exists():
            raise BackendLoadError(
                f"modelo de embeddings '{config.name}' no encontrado en {config.path}"
            )

        return Llama(
            model_path=str(config.path),
            n_ctx=config.n_ctx,
            n_threads=config.n_threads,
            n_gpu_layers=config.n_gpu_layers,
            embedding=True,
            verbose=False,
        )

    def embed(self, text: str) -> list[float]:
        logger.debug("embed: generando vector para texto de %d chars", len(text))
        result = self._llm.create_embedding(text)
        return list(result["data"][0]["embedding"])

    def close(self) -> None:
        self._llm.close()
