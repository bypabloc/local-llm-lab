from local_llm_lab.shell.runner import extract_run_command, run_with_confirmation


def test_extract_run_command_encuentra_marcador() -> None:
    text = "Puedo ayudarte con eso.\nRUN: ls -la\nEso lista los archivos."

    command = extract_run_command(text)

    assert command == "ls -la"


def test_extract_run_command_toma_la_ultima_linea_run() -> None:
    text = "RUN: echo primero\nAlgo de texto.\nRUN: echo segundo"

    command = extract_run_command(text)

    assert command == "echo segundo"


def test_extract_run_command_devuelve_none_sin_marcador() -> None:
    text = "Esta es una respuesta normal sin comandos."

    command = extract_run_command(text)

    assert command is None


def test_extract_run_command_ignora_marcador_vacio() -> None:
    text = "RUN:   \nsin comando real"

    command = extract_run_command(text)

    assert command is None


def test_run_with_confirmation_bloquea_comando_peligroso_aunque_confirm_sea_true() -> (
    None
):
    outcome = run_with_confirmation("rm -rf /", confirm=True)

    assert outcome.executed is False
    assert outcome.blocked_reason is not None


def test_run_with_confirmation_no_ejecuta_sin_confirmar() -> None:
    outcome = run_with_confirmation("echo hola", confirm=False)

    assert outcome.executed is False
    assert outcome.blocked_reason is None


def test_run_with_confirmation_ejecuta_comando_seguro_confirmado() -> None:
    outcome = run_with_confirmation("echo hola", confirm=True)

    assert outcome.executed is True
    assert outcome.return_code == 0
    assert "hola" in outcome.stdout


def test_run_with_confirmation_no_crashea_con_binario_inexistente() -> None:
    outcome = run_with_confirmation('search "algo que el modelo alucinó"', confirm=True)

    assert outcome.executed is False
    assert outcome.blocked_reason is not None
