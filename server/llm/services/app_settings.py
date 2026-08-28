import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AppSettings:
    memory_db_path: str
    models_dir: str | None


def resolve_data_dir() -> Path | None:
    value = os.environ.get("LLM_LAB_DATA_DIR")
    data_dir = Path(value) if value else None
    logger.debug("resolve_data_dir: LLM_LAB_DATA_DIR=%r -> %s", value, data_dir)
    return data_dir


def default_settings(data_dir: Path) -> AppSettings:
    return AppSettings(memory_db_path=str(data_dir / "memory.db"), models_dir=None)


def load_settings(data_dir: Path) -> AppSettings:
    path = data_dir / "settings.json"
    if not path.exists():
        logger.debug("load_settings: %s no existe, usando defaults", path)
        return default_settings(data_dir)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("load_settings: fallo leyendo/parseando %s", path)
        raise
    defaults = default_settings(data_dir)
    models_dir = raw.get("models_dir")
    settings = AppSettings(
        memory_db_path=str(
            Path(raw.get("memory_db_path", defaults.memory_db_path)).expanduser()
        ),
        models_dir=str(Path(models_dir).expanduser()) if models_dir else None,
    )
    logger.debug("load_settings -> %s", settings)
    return settings


def save_settings(data_dir: Path, settings: AppSettings) -> None:
    settings = AppSettings(
        memory_db_path=str(Path(settings.memory_db_path).expanduser()),
        models_dir=(
            str(Path(settings.models_dir).expanduser()) if settings.models_dir else None
        ),
    )
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "settings.json").write_text(
            json.dumps(asdict(settings), indent=2), encoding="utf-8"
        )
    except Exception:
        logger.exception(
            "save_settings: fallo escribiendo settings.json en %s", data_dir
        )
        raise
    logger.info("save_settings: guardado en %s -> %s", data_dir, settings)
