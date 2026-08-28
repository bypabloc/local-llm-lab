import logging
import queue
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from llm.config.models import ModelConfig

logger = logging.getLogger(__name__)

DownloadEventKind = Literal["progress", "done", "error"]


@dataclass(frozen=True, slots=True)
class DownloadEvent:
    kind: DownloadEventKind
    payload: dict[str, Any]


class MissingHfMetadataError(ValueError):
    """El modelo no tiene hf_repo/hf_file configurados en models.toml."""


def _progress_tqdm_class(
    events: "queue.Queue[DownloadEvent | None]", model_name: str
) -> type[Any]:
    # ponytail: tqdm no trae stubs de tipos — aislado acá, no se propaga Any
    # más allá de esta función (ver .claude/rules/python-style.md).
    from tqdm.auto import tqdm  # type: ignore[import-untyped]

    class _ProgressTqdm(tqdm):  # type: ignore[misc]
        def update(self, n: int = 1) -> Any:
            result = super().update(n)
            events.put(
                DownloadEvent(
                    "progress",
                    {
                        "model": model_name,
                        "downloaded": int(self.n),
                        "total": int(self.total or 0),
                    },
                )
            )
            return result

    return _ProgressTqdm


def download_model(config: ModelConfig, models_dir: Path) -> Iterator[DownloadEvent]:
    """Descarga el .gguf de config vía hf_hub_download, emitiendo progreso.

    Corre la descarga real en un thread aparte (hf_hub_download es
    bloqueante y no coopera con generadores) y reenvía sus eventos por una
    queue — mismo patrón que `_chat_event_stream` en views.py.
    """
    if not config.hf_repo or not config.hf_file:
        logger.error(
            "download_model: %s no tiene hf_repo/hf_file configurados", config.name
        )
        raise MissingHfMetadataError(
            f"modelo '{config.name}' no tiene hf_repo/hf_file en models.toml"
        )
    hf_repo = config.hf_repo
    hf_file = config.hf_file

    logger.info(
        "download_model: inicio %s desde %s/%s -> %s",
        config.name,
        hf_repo,
        hf_file,
        models_dir,
    )
    models_dir.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import hf_hub_download

    events: queue.Queue[DownloadEvent | None] = queue.Queue()

    def run_download() -> None:
        try:
            hf_hub_download(
                repo_id=hf_repo,
                filename=hf_file,
                local_dir=models_dir,
                tqdm_class=_progress_tqdm_class(events, config.name),
            )
            logger.info("download_model: %s completo", config.name)
            events.put(DownloadEvent("done", {"model": config.name}))
        except Exception:
            logger.exception("download_model: fallo descargando %s", config.name)
            events.put(
                DownloadEvent("error", {"model": config.name, "text": "descarga falló"})
            )
        finally:
            events.put(None)

    thread = threading.Thread(target=run_download, daemon=True)
    thread.start()

    while True:
        event = events.get()
        if event is None:
            break
        yield event
