"""Levanta/verifica el contenedor SearXNG usado como provider de búsqueda local.

Uso: uv run python devtools/run.py searxng [--url URL]
"""

import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

_DEFAULT_COMPOSE_FILE = Path(__file__).parent / "docker-compose.yml"
_LOCAL_HOSTS = ("localhost", "127.0.0.1")


class SearxngUnavailableError(Exception):
    pass


def _is_local_url(url: str) -> bool:
    return any(host in url for host in _LOCAL_HOSTS)


def _healthcheck(url: str, timeout_seconds: float) -> bool:
    request = Request(f"{url.rstrip('/')}/search?q=ping&format=json")
    try:
        urlopen(request, timeout=timeout_seconds)  # noqa: S310
    except (URLError, TimeoutError, OSError):
        return False
    return True


def _compose_up(compose_file: Path) -> None:
    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except FileNotFoundError as exc:
        raise SearxngUnavailableError(
            "no se encontró el comando 'docker' — instalalo o levantá "
            "SearXNG manualmente"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SearxngUnavailableError(
            f"'docker compose up' falló: {exc.stderr}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SearxngUnavailableError("'docker compose up' superó el timeout") from exc


def ensure_running(
    url: str,
    compose_file: Path = _DEFAULT_COMPOSE_FILE,
    healthcheck_timeout_seconds: float = 2.0,
    retry_delay_seconds: float = 3.0,
) -> None:
    """Verifica que SearXNG responda en `url`; si no, lo levanta con Docker Compose.

    Solo actúa sobre URLs locales (localhost/127.0.0.1) — no tiene sentido
    intentar levantar un contenedor para una instancia remota.
    """
    if not _is_local_url(url):
        return

    if _healthcheck(url, healthcheck_timeout_seconds):
        return

    _compose_up(compose_file)
    time.sleep(retry_delay_seconds)

    if not _healthcheck(url, healthcheck_timeout_seconds):
        raise SearxngUnavailableError(
            f"SearXNG no respondió en {url} después de levantar el contenedor"
        )
