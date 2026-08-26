from llm.shell.runner import extract_run_command, run_with_confirmation


def test_extract_run_command_devuelve_ultimo_comando_marcado() -> None:
    text = "voy a correr esto\nRUN: ls -la\nmas texto\nRUN: pwd"

    assert extract_run_command(text) == "pwd"


def test_extract_run_command_devuelve_none_sin_marcador() -> None:
    assert extract_run_command("respuesta sin comando") is None


def test_run_with_confirmation_bloquea_comando_peligroso_aunque_confirm_sea_true() -> (
    None
):
    outcome = run_with_confirmation("rm -rf /", confirm=True)

    assert outcome.executed is False
    assert outcome.blocked_reason is not None


def test_run_with_confirmation_no_ejecuta_si_confirm_es_false() -> None:
    outcome = run_with_confirmation("echo hola", confirm=False)

    assert outcome.executed is False
    assert outcome.blocked_reason is None


def test_run_with_confirmation_ejecuta_comando_seguro_confirmado() -> None:
    outcome = run_with_confirmation("echo hola", confirm=True)

    assert outcome.executed is True
    assert outcome.return_code == 0
    assert "hola" in outcome.stdout
