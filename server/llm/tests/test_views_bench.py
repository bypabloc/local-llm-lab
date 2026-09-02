import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.test import Client

from llm.router.llm_router import LLMRouter
from llm.services import device as device_service
from llm.services import router_singleton
from llm.tests.fakes import FakeBackend


@pytest.fixture(autouse=True)
def _fake_router(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    router_singleton.reset()

    def fake_build_router(device: str, models_dir: Path | None = None) -> LLMRouter:
        configs = device_service.resolve_model_configs(device, models_dir)
        return LLMRouter(
            configs,
            backend_factory=lambda config: FakeBackend(config, reply="respuesta fake"),
        )

    monkeypatch.setattr(router_singleton, "build_router", fake_build_router)
    yield
    router_singleton.reset()


def test_bench_devuelve_resultados_por_modelo(client: Client) -> None:
    response = client.post(
        "/api/bench",
        data=json.dumps(
            {
                "models": ["gemma4-e2b", "phi4-mini"],
                "prompt": "resumí Python",
                "max_tokens": 128,
                "no_think": False,
                "device": "cpu",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert {r["model"] for r in body["results"]} == {"gemma4-e2b", "phi4-mini"}
    for result in body["results"]:
        assert set(result) == {
            "model",
            "device",
            "tokens_per_second",
            "total_seconds",
            "prefill_seconds",
            "generation_seconds",
            "prompt_tokens",
            "completion_tokens",
            "rating",
            "no_think",
            "text",
        }
