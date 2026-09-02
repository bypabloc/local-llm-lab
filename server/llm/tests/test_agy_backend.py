import json
from collections.abc import Iterator
from typing import Any

import pytest

from llm.backends.agy_backend import AgyBackend
from llm.config.models import ModelConfig

_STREAM_JSON_LINES = [
    {
        "event": "init",
        "conversation_id": "abc",
        "init": {"cwd": "/repo", "tools": [], "permission_mode": "request-review"},
    },
    {
        "event": "step_update",
        "step_update": {
            "conversation_id": "abc",
            "step_index": 0,
            "state": "DONE",
            "step_type": "user_input",
        },
    },
    {
        "event": "step_update",
        "step_update": {
            "conversation_id": "abc",
            "step_index": 1,
            "state": "ACTIVE",
            "step_type": "agent_response",
            "text_delta": "Hola",
        },
    },
    {
        "event": "step_update",
        "step_update": {
            "conversation_id": "abc",
            "step_index": 1,
            "state": "DONE",
            "step_type": "agent_response",
            "text_delta": " mundo.\n",
            "duration_seconds": 1.2,
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "thinking_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 120,
            },
        },
    },
    {
        "event": "result",
        "result": {
            "conversation_id": "abc",
            "status": "SUCCESS",
            "response": "Hola mundo.\n",
            "duration_seconds": 1.2,
            "num_turns": 1,
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "thinking_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 120,
            },
        },
    },
]


def _config() -> ModelConfig:
    return ModelConfig(
        name="agy",
        path=None,
        n_ctx=0,
        n_threads=0,
        n_gpu_layers=0,
        license="proprietary",
        backend="agy",
    )


class _FakeProcess:
    def __init__(self, lines: list[dict[str, Any]]) -> None:
        self._lines = lines
        self.returncode = 0

    def stdout_lines(self) -> Iterator[str]:
        for line in self._lines:
            yield json.dumps(line)

    def wait(self) -> int:
        return self.returncode


def test_stream_chat_yield_solo_los_text_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProcess(_STREAM_JSON_LINES)
    backend = AgyBackend(_config())
    monkeypatch.setattr(backend, "_run_stream_json", lambda prompt: fake.stdout_lines())

    chunks = list(
        backend.stream_chat(
            messages=[{"role": "user", "content": "hola"}], max_tokens=100
        )
    )

    assert chunks == ["Hola", " mundo.\n"]


def test_stream_chat_ignora_lineas_sin_text_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lines = [_STREAM_JSON_LINES[0], _STREAM_JSON_LINES[1], _STREAM_JSON_LINES[4]]
    fake = _FakeProcess(lines)
    backend = AgyBackend(_config())
    monkeypatch.setattr(backend, "_run_stream_json", lambda prompt: fake.stdout_lines())

    chunks = list(
        backend.stream_chat(
            messages=[{"role": "user", "content": "hola"}], max_tokens=100
        )
    )

    assert chunks == []


def test_stream_chat_ignora_lineas_json_invalidas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = AgyBackend(_config())
    monkeypatch.setattr(
        backend,
        "_run_stream_json",
        lambda prompt: iter(["no es json", json.dumps(_STREAM_JSON_LINES[2])]),
    )

    chunks = list(
        backend.stream_chat(
            messages=[{"role": "user", "content": "hola"}], max_tokens=100
        )
    )

    assert chunks == ["Hola"]


def test_generate_junta_todo_el_texto_y_usa_usage_real(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeProcess(_STREAM_JSON_LINES)
    backend = AgyBackend(_config())
    monkeypatch.setattr(backend, "_run_stream_json", lambda prompt: fake.stdout_lines())

    result = backend.generate(system="eres util", user="hola", max_tokens=100)

    assert result.text == "Hola mundo.\n"
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 20


def test_generate_agrega_sufijo_no_think(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_run(prompt: str) -> Iterator[str]:
        captured["prompt"] = prompt
        return iter([json.dumps(_STREAM_JSON_LINES[4])])

    backend = AgyBackend(_config())
    monkeypatch.setattr(backend, "_run_stream_json", fake_run)

    backend.generate(system="eres util", user="hola", max_tokens=100, no_think=True)

    assert captured["prompt"].endswith("/no_think")


def test_count_tokens_aproxima_sin_llamar_al_cli() -> None:
    backend = AgyBackend(_config())

    assert backend.count_tokens("a" * 40) == 10
