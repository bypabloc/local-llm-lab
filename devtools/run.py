"""devtools entrypoint. Despacha al módulo según el primer argumento.

Uso: uv run python devtools/run.py <comando> [flags]

Comandos:
  searxng    Verifica/levanta el contenedor SearXNG usado para búsqueda web.
"""

import os
import sys
from collections.abc import Callable

from devtools.searxng.main import SearxngUnavailableError, ensure_running

COMMANDS: dict[str, Callable[[list[str]], int]] = {}


def _run_searxng(argv: list[str]) -> int:
    url = os.environ.get("SEARXNG_URL", "http://localhost:8888")
    if "--url" in argv:
        url = argv[argv.index("--url") + 1]

    try:
        ensure_running(url)
    except SearxngUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"SearXNG disponible en {url}")
    return 0


COMMANDS["searxng"] = _run_searxng


def _print_help() -> None:
    print(__doc__)
    print("COMANDOS:")
    for name in COMMANDS:
        print(f"  {name}")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("--help", "-h"):
        _print_help()
        return 0

    command, rest = argv[0], argv[1:]
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"comando desconocido: {command}", file=sys.stderr)
        _print_help()
        return 2

    return handler(rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
