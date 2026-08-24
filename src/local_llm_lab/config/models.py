import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).parent / "models.toml"


@dataclass(frozen=True, slots=True)
class ModelConfig:
    name: str
    path: Path
    n_ctx: int
    n_threads: int
    n_gpu_layers: int
    license: str


def load_model_configs(
    config_path: Path = DEFAULT_CONFIG_PATH,
    project_root: Path | None = None,
) -> dict[str, ModelConfig]:
    root = project_root or config_path.parent.parent.parent.parent
    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    configs: dict[str, ModelConfig] = {}
    for name, entry in raw.get("models", {}).items():
        configs[name] = ModelConfig(
            name=name,
            path=root / entry["path"],
            n_ctx=entry["n_ctx"],
            n_threads=entry.get("n_threads", 8),
            n_gpu_layers=entry.get("n_gpu_layers", 0),
            license=entry.get("license", "unknown"),
        )
    return configs
