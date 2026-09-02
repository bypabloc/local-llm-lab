import json
import time
from pathlib import Path
from typing import Any

import pytest
from django.test import AsyncClient

from llm.router.llm_router import LLMRouter
from llm.services import device as device_service
from llm.services import router_singleton
from llm.tests.fakes import FakeBackend


def _install_fake_router(
    monkeypatch: pytest.MonkeyPatch, reply: str, stream_delay_seconds: float = 0.0
) -> None:
    router_singleton.reset()

    def fake_build_router(device: str, models_dir: Path | None = None) -> LLMRouter:
        configs = device_service.resolve_model_configs(device, models_dir)
        return LLMRouter(
            configs,
            backend_factory=lambda config: FakeBackend(
                config, reply=reply, stream_delay_seconds=stream_delay_seconds
            ),
        )

    monkeypatch.setattr(router_singleton, "build_router", fake_build_router)


@pytest.fixture(autouse=True)
def _memory_db_en_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_LAB_DATA_DIR", str(tmp_path))


def _parse_sse(raw: bytes) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for chunk in raw.decode("utf-8").split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        assert chunk.startswith("data: ")
        events.append(json.loads(chunk[len("data: ") :]))
    return events


@pytest.mark.asyncio
async def test_chat_streamea_tokens_y_termina_con_assistant_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_router(monkeypatch, reply="hola mundo")
    client = AsyncClient()

    response = await client.post(
        "/api/chat",
        data=json.dumps(
            {
                "model": "gemma4-e2b",
                "device": "cpu",
                "agent": "gemma",
                "max_tokens": 128,
                "no_think": False,
                "allow_shell": False,
                "allow_search": False,
                "system_file_content": "",
                "history": [{"role": "user", "content": "hola"}],
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    streaming_content: object = getattr(response, "streaming_content")  # noqa: B009
    body = b"".join([chunk async for chunk in streaming_content])  # type: ignore[attr-defined]
    events = _parse_sse(body)

    tokens = [e for e in events if e["kind"] == "token"]
    assert "".join(str(e["payload"]["text"]) for e in tokens) == "hola mundo"
    assert events[-1]["kind"] == "assistant_done"


@pytest.mark.asyncio
async def test_chat_con_run_corta_el_stream_con_run_proposed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_router(monkeypatch, reply="RUN: ls -la")
    client = AsyncClient()

    response = await client.post(
        "/api/chat",
        data=json.dumps(
            {
                "model": "gemma4-e2b",
                "device": "cpu",
                "agent": "gemma",
                "max_tokens": 128,
                "no_think": False,
                "allow_shell": True,
                "allow_search": False,
                "system_file_content": "",
                "history": [{"role": "user", "content": "listá archivos"}],
            }
        ),
        content_type="application/json",
    )

    streaming_content: object = getattr(response, "streaming_content")  # noqa: B009
    body = b"".join([chunk async for chunk in streaming_content])  # type: ignore[attr-defined]
    events = _parse_sse(body)

    assert events[-1]["kind"] == "run_proposed"


@pytest.mark.asyncio
async def test_chat_emite_el_primer_token_sin_esperar_a_que_termine_la_generacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Bug real: `await loop.run_in_executor(None, produce)` bloqueaba hasta
    # terminar TODA la generación antes de emitir el primer chunk SSE — la UI
    # recibía la respuesta completa de golpe en vez de token a token.
    _install_fake_router(monkeypatch, reply="hola mundo", stream_delay_seconds=0.05)
    client = AsyncClient()

    start = time.monotonic()
    response = await client.post(
        "/api/chat",
        data=json.dumps(
            {
                "model": "gemma4-e2b",
                "device": "cpu",
                "agent": "gemma",
                "max_tokens": 128,
                "no_think": False,
                "allow_shell": False,
                "allow_search": False,
                "system_file_content": "",
                "history": [{"role": "user", "content": "hola"}],
            }
        ),
        content_type="application/json",
    )

    streaming_content: object = getattr(response, "streaming_content")  # noqa: B009
    first_chunk_elapsed: float | None = None
    async for _chunk in streaming_content:  # type: ignore[attr-defined]
        first_chunk_elapsed = time.monotonic() - start
        break

    assert first_chunk_elapsed is not None
    # "hola mundo" son 10 caracteres * 0.05s = 0.5s de generación total.
    # El primer chunk debe llegar mucho antes de que termine toda la
    # generación — si vuelve a bufferizar, esto tarda ~0.5s en vez de <0.2s.
    assert first_chunk_elapsed < 0.2
