import json
from pathlib import Path

import pytest
from django.test import Client


@pytest.fixture(autouse=True)
def _data_dir_en_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_LAB_DATA_DIR", str(tmp_path))


def test_get_settings_devuelve_defaults_sin_configuracion_previa(
    client: Client, tmp_path: Path
) -> None:
    response = client.get("/api/settings")

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body == {
        "memory_db_path": str(tmp_path / "memory.db"),
        "models_dir": None,
    }


def test_post_settings_guarda_y_get_posterior_refleja_el_cambio(
    client: Client, tmp_path: Path
) -> None:
    nuevo_memory_db = str(tmp_path / "custom" / "memory.db")
    nuevo_models_dir = str(tmp_path / "custom" / "models")

    post_response = client.post(
        "/api/settings/update",
        data=json.dumps(
            {"memory_db_path": nuevo_memory_db, "models_dir": nuevo_models_dir}
        ),
        content_type="application/json",
    )
    assert post_response.status_code == 200

    get_response = client.get("/api/settings")
    body = json.loads(get_response.content)
    assert body == {"memory_db_path": nuevo_memory_db, "models_dir": nuevo_models_dir}
