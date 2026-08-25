from pathlib import Path

from core.config.dotenv import load_dotenv


def test_load_dotenv_setea_variables_del_archivo(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("MI_VAR_TEST", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("MI_VAR_TEST=hola\n", encoding="utf-8")

    load_dotenv(env_file)

    assert __import__("os").environ["MI_VAR_TEST"] == "hola"


def test_load_dotenv_no_pisa_variable_ya_seteada(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("MI_VAR_TEST", "valor_shell")
    env_file = tmp_path / ".env"
    env_file.write_text("MI_VAR_TEST=valor_archivo\n", encoding="utf-8")

    load_dotenv(env_file)

    assert __import__("os").environ["MI_VAR_TEST"] == "valor_shell"


def test_load_dotenv_ignora_comentarios_y_lineas_vacias(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.delenv("OTRA_VAR_TEST", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# esto es un comentario\n\nOTRA_VAR_TEST=valor\n", encoding="utf-8"
    )

    load_dotenv(env_file)

    assert __import__("os").environ["OTRA_VAR_TEST"] == "valor"


def test_load_dotenv_soporta_valores_con_comillas(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("VAR_COMILLAS_TEST", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text('VAR_COMILLAS_TEST="valor con espacios"\n', encoding="utf-8")

    load_dotenv(env_file)

    assert __import__("os").environ["VAR_COMILLAS_TEST"] == "valor con espacios"


def test_load_dotenv_no_falla_si_el_archivo_no_existe(tmp_path: Path) -> None:
    load_dotenv(tmp_path / "no_existe.env")
