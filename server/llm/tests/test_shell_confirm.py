from llm.services.shell_confirm import confirm_and_run


def test_comando_bloqueado_no_se_ejecuta() -> None:
    outcome = confirm_and_run("rm -rf /")

    assert outcome.executed is False
    assert outcome.blocked_reason is not None


def test_comando_permitido_se_ejecuta_y_devuelve_stdout() -> None:
    outcome = confirm_and_run("echo hola")

    assert outcome.executed is True
    assert outcome.blocked_reason is None
    assert "hola" in outcome.stdout
