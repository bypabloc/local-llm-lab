import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppSettings:
    memory_db_path: str
    models_dir: str | None


def resolve_data_dir() -> Path | None:
    value = os.environ.get("LLM_LAB_DATA_DIR")
    return Path(value) if value else None


def default_settings(data_dir: Path) -> AppSettings:
    return AppSettings(memory_db_path=str(data_dir / "memory.db"), models_dir=None)


def load_settings(data_dir: Path) -> AppSettings:
    path = data_dir / "settings.json"
    if not path.exists():
        return default_settings(data_dir)
    raw = json.loads(path.read_text(encoding="utf-8"))
    defaults = default_settings(data_dir)
    return AppSettings(
        memory_db_path=raw.get("memory_db_path", defaults.memory_db_path),
        models_dir=raw.get("models_dir"),
    )


def save_settings(data_dir: Path, settings: AppSettings) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "settings.json").write_text(
        json.dumps(asdict(settings), indent=2), encoding="utf-8"
    )
