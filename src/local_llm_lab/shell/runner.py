import re
import subprocess
from dataclasses import dataclass

from local_llm_lab.shell.blocklist import is_blocked, parse_shell_safe

_RUN_PATTERN = re.compile(r"^RUN:[ \t]*(\S.*)?$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class CommandOutcome:
    command: str
    executed: bool
    blocked_reason: str | None
    stdout: str
    stderr: str
    return_code: int | None


def extract_run_command(text: str) -> str | None:
    """Devuelve el último comando marcado con 'RUN: <comando>' en `text`, o None."""
    matches = _RUN_PATTERN.findall(text)
    if not matches:
        return None
    command = matches[-1].strip()
    return command or None


def run_with_confirmation(
    command: str, confirm: bool, timeout_seconds: int = 30
) -> CommandOutcome:
    """Ejecuta `command` si pasa el blocklist y `confirm` es True.

    `confirm` se decide afuera (ej. un prompt s/n al usuario) — esta función
    no pregunta nada, solo aplica la decisión de forma consistente.
    """
    reason = is_blocked(command)
    if reason is not None:
        return CommandOutcome(
            command=command,
            executed=False,
            blocked_reason=reason,
            stdout="",
            stderr="",
            return_code=None,
        )

    if not confirm:
        return CommandOutcome(
            command=command,
            executed=False,
            blocked_reason=None,
            stdout="",
            stderr="",
            return_code=None,
        )

    try:
        args = parse_shell_safe(command)
    except ValueError as exc:
        return CommandOutcome(
            command=command,
            executed=False,
            blocked_reason=f"comando no parseable: {exc}",
            stdout="",
            stderr="",
            return_code=None,
        )

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandOutcome(
            command=command,
            executed=False,
            blocked_reason=f"no se pudo ejecutar: {exc}",
            stdout="",
            stderr="",
            return_code=None,
        )
    return CommandOutcome(
        command=command,
        executed=True,
        blocked_reason=None,
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.returncode,
    )
