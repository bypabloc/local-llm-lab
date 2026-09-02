import os
from pathlib import Path


def load_dotenv(path: Path) -> None:
    """Carga pares KEY=VALUE de `path` a `os.environ`, sin pisar lo ya seteado."""
    if not path.is_file():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
