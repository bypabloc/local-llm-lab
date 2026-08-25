from core.shell.runner import CommandOutcome, run_with_confirmation


def confirm_and_run(command: str) -> CommandOutcome:
    """El usuario ya confirmó en la UI — el blocklist sigue aplicando igual."""
    return run_with_confirmation(command, confirm=True)
