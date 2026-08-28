from pathlib import Path

from llm.config.models import ModelConfig

# ponytail: modelo fijo, no configurable por TOML como los de chat — un solo
# modelo de embeddings alcanza para este proyecto (ver kiss-solid.md: no
# agregar abstracción hasta que exista una necesidad real de intercambiarlo).
EMBEDDING_MODEL_NAME = "qwen3-embedding-0.6b"
_HF_REPO = "Qwen/Qwen3-Embedding-0.6B-GGUF"
_HF_FILE = "Qwen3-Embedding-0.6B-Q8_0.gguf"


def embedding_model_config(models_dir: Path) -> ModelConfig:
    return ModelConfig(
        name=EMBEDDING_MODEL_NAME,
        path=models_dir / _HF_FILE,
        n_ctx=2048,
        n_threads=8,
        n_gpu_layers=0,
        license="Apache-2.0",
        hf_repo=_HF_REPO,
        hf_file=_HF_FILE,
    )
