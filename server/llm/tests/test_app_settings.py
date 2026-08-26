from pathlib import Path

import pytest

from llm.services.app_settings import (
    AppSettings,
    default_settings,
    load_settings,
    resolve_data_dir,
    save_settings,
)


def test_resolve_data_dir_usa_env_var_si_esta_seteada(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LLM_LAB_DATA_DIR", str(tmp_path))

    assert resolve_data_dir() == tmp_path


def test_resolve_data_dir_none_si_no_hay_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_LAB_DATA_DIR", raising=False)

    assert resolve_data_dir() is None


def test_default_settings_usa_memory_db_en_data_dir_y_models_dir_none(
    tmp_path: Path,
) -> None:
    settings = default_settings(tmp_path)

    assert settings == AppSettings(
        memory_db_path=str(tmp_path / "memory.db"), models_dir=None
    )


def test_load_settings_devuelve_default_si_no_existe_settings_json(
    tmp_path: Path,
) -> None:
    settings = load_settings(tmp_path)

    assert settings == default_settings(tmp_path)


def test_save_settings_luego_load_settings_persiste_los_valores(
    tmp_path: Path,
) -> None:
    original = AppSettings(
        memory_db_path=str(tmp_path / "custom" / "memory.db"),
        models_dir=str(tmp_path / "custom" / "models"),
    )

    save_settings(tmp_path, original)

    assert load_settings(tmp_path) == original


def test_load_settings_usa_default_para_claves_faltantes_en_json_viejo(
    tmp_path: Path,
) -> None:
    (tmp_path / "settings.json").write_text("{}", encoding="utf-8")

    settings = load_settings(tmp_path)

    assert settings == default_settings(tmp_path)
