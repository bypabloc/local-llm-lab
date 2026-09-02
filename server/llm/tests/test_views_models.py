import json

from django.test import Client


def test_get_models_lista_los_modelos_del_toml(client: Client) -> None:
    response = client.get("/api/models")

    assert response.status_code == 200
    body = json.loads(response.content)
    names = {m["name"] for m in body["models"]}
    assert names == {
        "qwen3-4b",
        "qwen3-8b",
        "phi4-mini",
        "gemma4-e2b",
        "gemma4-e4b",
        "agy",
        "qwen3-embedding-0.6b",
    }
