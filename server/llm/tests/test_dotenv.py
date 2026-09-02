import os
from pathlib import Path

import pytest

from llm.config.dotenv import load_dotenv


def test_load_dotenv_setea_variables_del_archivo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LLM_LAB_TEST_VAR", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text('LLM_LAB_TEST_VAR="hola"\n', encoding="utf-8")

    load_dotenv(env_file)

    assert os.environ["LLM_LAB_TEST_VAR"] == "hola"


def test_load_dotenv_no_pisa_variable_ya_seteada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_LAB_TEST_VAR", "ya-seteada")
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_LAB_TEST_VAR=del-archivo\n", encoding="utf-8")

    load_dotenv(env_file)

    assert os.environ["LLM_LAB_TEST_VAR"] == "ya-seteada"


def test_load_dotenv_ignora_comentarios_y_lineas_vacias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LLM_LAB_TEST_VAR", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("# comentario\n\nLLM_LAB_TEST_VAR=valor\n", encoding="utf-8")

    load_dotenv(env_file)

    assert os.environ["LLM_LAB_TEST_VAR"] == "valor"


def test_load_dotenv_no_falla_si_el_archivo_no_existe(tmp_path: Path) -> None:
    load_dotenv(tmp_path / "no-existe.env")
