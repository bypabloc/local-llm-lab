import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import asdict
from pathlib import Path
from typing import Any

from django.http import HttpRequest, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from llm.backends.protocol import ChatMessage
from llm.benchmark.runner import run_benchmark
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
from llm.services.router_singleton import get_router
from llm.services.shell_confirm import confirm_and_run
from llm.services.system_prompt import build_system_prompt

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_data_dir() -> Path:
    return resolve_data_dir() or (resolve_project_root() or _REPO_ROOT) / "data"


def _current_settings() -> AppSettings:
    return load_settings(_resolve_data_dir())


@require_GET
def list_models(request: HttpRequest) -> JsonResponse:
    settings = _current_settings()
    models_dir = Path(settings.models_dir) if settings.models_dir else None
    configs = load_model_configs(models_dir=models_dir)
    models = [
        {"name": name, "n_ctx": config.n_ctx, "license": config.license}
        for name, config in sorted(configs.items())
    ]
    return JsonResponse({"models": models})


@require_GET
def list_settings(request: HttpRequest) -> JsonResponse:
    return JsonResponse(asdict(_current_settings()))


@csrf_exempt
@require_POST
def update_settings(request: HttpRequest) -> JsonResponse:
    body = json.loads(request.body)
    settings = AppSettings(
        memory_db_path=body["memory_db_path"], models_dir=body.get("models_dir")
    )
    save_settings(_resolve_data_dir(), settings)
    return JsonResponse(asdict(settings))


@csrf_exempt
@require_POST
def shell_confirm(request: HttpRequest) -> JsonResponse:
    body = json.loads(request.body)
    command = body["command"]
    outcome = confirm_and_run(command)
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


@csrf_exempt
@require_POST
def bench(request: HttpRequest) -> JsonResponse:
    body = json.loads(request.body)
    device = resolve_device(body.get("device"))
    settings = _current_settings()
    models_dir = Path(settings.models_dir) if settings.models_dir else None
    router = get_router(device, models_dir)

    results = []
    for model_name in body["models"]:
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
    return JsonResponse({"results": results})


async def _chat_event_stream(
    backend: Any,
    history: list[ChatMessage],
    memory_db_path: Path,
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
        memory_store = MemoryStore(memory_db_path)
        for event in run_chat_turn(
            backend,
            history,
            memory_store,
            max_tokens,
            no_think,
            allow_shell,
            allow_search,
        ):
            asyncio.run_coroutine_threadsafe(queue.put(asdict(event)), loop)
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
    body = json.loads(request.body)
    device = resolve_device(body.get("device"))
    settings = _current_settings()
    models_dir = Path(settings.models_dir) if settings.models_dir else None
    router = get_router(device, models_dir)
    backend = router.get(body["model"])

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

    return StreamingHttpResponse(
        _chat_event_stream(
            backend,
            history,
            Path(settings.memory_db_path),
            body.get("max_tokens", 1024),
            body.get("no_think", False),
            allow_shell,
            allow_search,
        ),
        content_type="text/event-stream",
    )
