import json
from pathlib import Path
from typing import Any

import pytest
from django.test import AsyncClient

from core.router.llm_router import LLMRouter
from llm.services import device as device_service
from llm.services import router_singleton
from llm.tests.fakes import FakeBackend


def _install_fake_router(monkeypatch: pytest.MonkeyPatch, reply: str) -> None:
    router_singleton.reset()

    def fake_build_router(device: str) -> LLMRouter:
        configs = device_service.resolve_model_configs(device)
        return LLMRouter(
            configs,
            backend_factory=lambda config: FakeBackend(config, reply=reply),
        )

    monkeypatch.setattr(router_singleton, "build_router", fake_build_router)


@pytest.fixture(autouse=True)
def _memory_db_en_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("llm.views._MEMORY_DB_PATH", tmp_path / "memory.db")


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
