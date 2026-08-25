import re

_REMEMBER_PATTERN = re.compile(r"^REMEMBER:[ \t]*(\S.*)?$", re.MULTILINE)


def extract_remember_note(text: str) -> str | None:
    """Devuelve el último hecho marcado con 'REMEMBER: <hecho>' en `text`, o None."""
    matches = _REMEMBER_PATTERN.findall(text)
    if not matches:
        return None
    note = matches[-1].strip()
    return note or None
