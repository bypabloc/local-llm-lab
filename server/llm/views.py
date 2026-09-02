import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict
from pathlib import Path
from typing import Any

from django.http import HttpRequest, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from llm.backends.protocol import ChatMessage
from llm.benchmark.runner import run_benchmark
from llm.config.embedding_model import EMBEDDING_MODEL_NAME, embedding_model_config
from llm.config.models import load_model_configs
from llm.memory import MemoryStore
from llm.personalities import get_persona, resolve_agent_name
from llm.services.app_settings import (
    AppSettings,
    load_settings,
    resolve_data_dir,
    save_settings,
)
from llm.services.chat_turn import run_chat_turn
from llm.services.device import resolve_device, resolve_project_root
from llm.services.embedding_singleton import get_embed_fn
from llm.services.model_downloads import download_model
from llm.services.router_singleton import get_router
from llm.services.shell_confirm import confirm_and_run
from llm.services.system_prompt import build_system_prompt

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_data_dir() -> Path:
    data_dir = resolve_data_dir() or (resolve_project_root() or _REPO_ROOT) / "data"
    logger.debug("_resolve_data_dir -> %s", data_dir)
    return data_dir


def _current_settings() -> AppSettings:
    settings = load_settings(_resolve_data_dir())
    logger.debug("_current_settings -> %s", settings)
    return settings


@require_GET
def list_models(request: HttpRequest) -> JsonResponse:
    logger.info("list_models: inicio")
    try:
        settings = _current_settings()
        models_dir = Path(settings.models_dir) if settings.models_dir else None
        logger.debug("list_models: models_dir=%s", models_dir)
        configs = load_model_configs(models_dir=models_dir)
        models = [
            {
                "name": name,
                "n_ctx": config.n_ctx,
                "license": config.license,
                "is_downloaded": config.path.exists() if config.path else True,
                "downloadable": bool(config.hf_repo and config.hf_file),
                "kind": "chat",
            }
            for name, config in sorted(configs.items())
        ]

        embedding_config = embedding_model_config(models_dir or (_REPO_ROOT / "models"))
        models.append(
            {
                "name": embedding_config.name,
                "n_ctx": embedding_config.n_ctx,
                "license": embedding_config.license,
                "is_downloaded": embedding_config.path is not None
                and embedding_config.path.exists(),
                "downloadable": True,
                "kind": "embedding",
            }
        )
        logger.info("list_models: %d modelos encontrados", len(models))
        return JsonResponse({"models": models})
    except Exception:
        logger.exception("list_models: fallo inesperado")
        raise


async def _download_event_stream(
    config_name: str, models_dir: Path
) -> AsyncIterator[bytes]:
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    def produce() -> None:
        try:
            settings = _current_settings()
            configs_dir = (
                Path(settings.models_dir) if settings.models_dir else models_dir
            )
            configs = load_model_configs(models_dir=configs_dir)
            config = configs.get(config_name)
            if config is None and config_name == EMBEDDING_MODEL_NAME:
                config = embedding_model_config(configs_dir)
            if config is None:
                raise ValueError(f"modelo '{config_name}' no existe en models.toml")
            for event in download_model(config, configs_dir):
                logger.debug("_download_event_stream.produce: evento=%s", event.kind)
                asyncio.run_coroutine_threadsafe(queue.put(asdict(event)), loop)
        except Exception:
            logger.exception("_download_event_stream.produce: fallo inesperado")
            asyncio.run_coroutine_threadsafe(
                queue.put(
                    {
                        "kind": "error",
                        "payload": {"model": config_name, "text": "error interno"},
                    }
                ),
                loop,
            )
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    loop.run_in_executor(None, produce)

    while True:
        event = await queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n".encode()


@csrf_exempt
@require_POST
async def download_model_view(request: HttpRequest) -> StreamingHttpResponse:
    logger.info("download_model_view: inicio")
    body = json.loads(request.body)
    model_name = body["model"]
    settings = _current_settings()
    models_dir = (
        Path(settings.models_dir) if settings.models_dir else _REPO_ROOT / "models"
    )
    return StreamingHttpResponse(
        _download_event_stream(model_name, models_dir),
        content_type="text/event-stream",
    )


@require_GET
def list_settings(request: HttpRequest) -> JsonResponse:
    logger.info("list_settings: inicio")
    try:
        settings = _current_settings()
        return JsonResponse(asdict(settings))
    except Exception:
        logger.exception("list_settings: fallo inesperado")
        raise


@csrf_exempt
@require_POST
def update_settings(request: HttpRequest) -> JsonResponse:
    logger.info("update_settings: inicio")
    try:
        body = json.loads(request.body)
        logger.debug("update_settings: body=%s", body)
        settings = AppSettings(
            memory_db_path=body["memory_db_path"], models_dir=body.get("models_dir")
        )
        save_settings(_resolve_data_dir(), settings)
        logger.info("update_settings: guardado ok")
        return JsonResponse(asdict(settings))
    except Exception:
        logger.exception("update_settings: fallo inesperado")
        raise


@csrf_exempt
@require_POST
def shell_confirm(request: HttpRequest) -> JsonResponse:
    logger.info("shell_confirm: inicio")
    try:
        body = json.loads(request.body)
        command = body["command"]
        logger.debug("shell_confirm: command=%s", command)
        outcome = confirm_and_run(command)
        logger.info(
            "shell_confirm: ejecutado=%s return_code=%s",
            outcome.executed,
            outcome.return_code,
        )
        return JsonResponse(
            {
                "command": outcome.command,
                "executed": outcome.executed,
                "blocked_reason": outcome.blocked_reason,
                "stdout": outcome.stdout,
                "stderr": outcome.stderr,
                "return_code": outcome.return_code,
            }
        )
    except Exception:
        logger.exception("shell_confirm: fallo inesperado")
        raise


@csrf_exempt
@require_POST
def bench(request: HttpRequest) -> JsonResponse:
    logger.info("bench: inicio")
    try:
        body = json.loads(request.body)
        device = resolve_device(body.get("device"))
        logger.debug("bench: device=%s", device)
        settings = _current_settings()
        models_dir = Path(settings.models_dir) if settings.models_dir else None
        router = get_router(device, models_dir)

        results = []
        for model_name in body["models"]:
            logger.info("bench: corriendo modelo=%s", model_name)
            backend = router.get(model_name)
            result = run_benchmark(
                model_name,
                backend,
                system=body.get("system_file_content", ""),
                user=body["prompt"],
                max_tokens=body.get("max_tokens", 1024),
                no_think=body.get("no_think", False),
            )
            router.unload(model_name)
            logger.info(
                "bench: modelo=%s tok/s=%.2f", model_name, result.tokens_per_second
            )
            results.append(
                {
                    "model": result.model_name,
                    "device": device,
                    "tokens_per_second": result.tokens_per_second,
                    "total_seconds": result.total_seconds,
                    "prefill_seconds": result.prefill_seconds,
                    "generation_seconds": result.generation_seconds,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "rating": result.rating,
                    "no_think": result.no_think,
                    "text": result.text,
                }
            )
        logger.info("bench: fin, %d resultados", len(results))
        return JsonResponse({"results": results})
    except Exception:
        logger.exception("bench: fallo inesperado")
        raise


_embeddings_backfilled = False


def _backfill_embeddings_once(memory_store: MemoryStore) -> None:
    """Completa embeddings de hechos guardados antes de que el modelo de
    embeddings estuviera disponible. Una sola vez por proceso — hechos ya
    embebidos no se reprocesan (backfill_embeddings ya filtra eso), pero
    evita la query de chequeo en cada turno de chat una vez confirmado."""
    global _embeddings_backfilled
    if _embeddings_backfilled:
        return
    count = memory_store.backfill_embeddings()
    if count:
        logger.info("_backfill_embeddings_once: %d hecho(s) completados", count)
    _embeddings_backfilled = True


async def _chat_event_stream(
    backend: Any,
    history: list[ChatMessage],
    memory_db_path: Path,
    models_dir: Path,
    max_tokens: int,
    no_think: bool,
    allow_shell: bool,
    allow_search: bool,
) -> AsyncIterator[bytes]:
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    def produce() -> None:
        # ponytail: MemoryStore (sqlite3) no tolera cruzar threads — se crea
        # acá, en el mismo thread del executor que la va a usar.
        try:
            logger.debug(
                "_chat_event_stream.produce: abriendo MemoryStore en %s",
                memory_db_path,
            )
            embed_fn = get_embed_fn(models_dir)
            logger.debug(
                "_chat_event_stream.produce: recall semántico %s",
                "habilitado" if embed_fn is not None else "deshabilitado",
            )
            memory_store = MemoryStore(memory_db_path, embed_fn=embed_fn)
            _backfill_embeddings_once(memory_store)
            for event in run_chat_turn(
                backend,
                history,
                memory_store,
                max_tokens,
                no_think,
                allow_shell,
                allow_search,
            ):
                logger.debug("_chat_event_stream.produce: evento=%s", event.kind)
                asyncio.run_coroutine_threadsafe(queue.put(asdict(event)), loop)
        except Exception:
            logger.exception("_chat_event_stream.produce: fallo inesperado")
            asyncio.run_coroutine_threadsafe(
                queue.put({"kind": "error", "payload": {"text": "error interno"}}),
                loop,
            )
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    loop.run_in_executor(None, produce)

    while True:
        event = await queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n".encode()


@csrf_exempt
@require_POST
async def chat(request: HttpRequest) -> StreamingHttpResponse:
    logger.info("chat: inicio")
    try:
        body = json.loads(request.body)
        device = resolve_device(body.get("device"))
        logger.debug("chat: device=%s model=%s", device, body.get("model"))
        settings = _current_settings()
        models_dir = Path(settings.models_dir) if settings.models_dir else None
        logger.debug(
            "chat: models_dir=%s memory_db_path=%s",
            models_dir,
            settings.memory_db_path,
        )
        router = get_router(device, models_dir)
        backend = router.get(body["model"])
        logger.debug("chat: backend resuelto para %s", body["model"])

        persona = get_persona(resolve_agent_name(body.get("agent")))
        allow_shell = body.get("allow_shell", False)
        allow_search = body.get("allow_search", False)

        history: list[ChatMessage] = list(body["history"])
        is_first_turn = not any(m["role"] == "system" for m in history)
        if is_first_turn:
            system_prompt = build_system_prompt(
                persona, body.get("system_file_content", ""), allow_shell, allow_search
            )
            if system_prompt:
                history.insert(0, {"role": "system", "content": system_prompt})

        logger.info("chat: iniciando stream, %d mensajes en history", len(history))
        return StreamingHttpResponse(
            _chat_event_stream(
                backend,
                history,
                Path(settings.memory_db_path),
                models_dir or (_REPO_ROOT / "models"),
                body.get("max_tokens", 1024),
                body.get("no_think", False),
                allow_shell,
                allow_search,
            ),
            content_type="text/event-stream",
        )
    except Exception:
        logger.exception("chat: fallo inesperado antes de iniciar el stream")
        raise
