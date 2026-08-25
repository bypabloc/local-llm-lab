import os

# ponytail: autobahn.nvx es una aceleración Cython de websockets que
# requiere compilar C en runtime — no soportado dentro de un binario
# PyInstaller congelado. No la usamos (SSE es HTTP, no websockets). Debe
# setearse ANTES de importar daphne, que importa autobahn a nivel de módulo.
os.environ.setdefault("AUTOBAHN_USE_NVX", "0")

import django
from daphne.server import Server  # type: ignore[import-untyped]
from django.core.handlers.asgi import ASGIHandler


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
    django.setup()

    from django.core.asgi import get_asgi_application

    application: ASGIHandler = get_asgi_application()
    port = int(os.environ.get("LLM_LAB_SERVER_PORT", "8000"))
    Server(
        application=application,
        endpoints=[f"tcp:port={port}:interface=127.0.0.1"],
    ).run()


if __name__ == "__main__":
    main()
