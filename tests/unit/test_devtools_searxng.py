import subprocess
from pathlib import Path
from urllib.error import URLError

from devtools.searxng.main import SearxngUnavailableError, ensure_running


def test_ensure_running_no_hace_nada_si_ya_responde(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("devtools.searxng.main.urlopen", lambda *a, **k: object())
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "devtools.searxng.main.subprocess.run",
        lambda args, **k: calls.append(args),
    )

    ensure_running("http://localhost:8888", compose_file=Path("fake.yml"))

    assert calls == []


def test_ensure_running_levanta_compose_si_no_responde(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    healthcheck_calls = {"count": 0}

    def _fake_urlopen(*args: object, **kwargs: object) -> object:
        healthcheck_calls["count"] += 1
        if healthcheck_calls["count"] == 1:
            raise URLError("conexión rechazada")
        return object()

    monkeypatch.setattr("devtools.searxng.main.urlopen", _fake_urlopen)

    compose_calls: list[list[str]] = []

    def _fake_run(
        args: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        compose_calls.append(args)
        return subprocess.CompletedProcess(args, returncode=0)

    monkeypatch.setattr("devtools.searxng.main.subprocess.run", _fake_run)

    ensure_running(
        "http://localhost:8888", compose_file=Path("fake.yml"), retry_delay_seconds=0
    )

    assert len(compose_calls) == 1
    assert "up" in compose_calls[0]
    assert "-d" in compose_calls[0]
    assert healthcheck_calls["count"] == 2


def test_ensure_running_lanza_error_si_sigue_sin_responder(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def _raise(*args: object, **kwargs: object) -> object:
        raise URLError("conexión rechazada")

    monkeypatch.setattr("devtools.searxng.main.urlopen", _raise)
    monkeypatch.setattr(
        "devtools.searxng.main.subprocess.run",
        lambda args, **k: subprocess.CompletedProcess(args, returncode=0),
    )

    try:
        ensure_running(
            "http://localhost:8888",
            compose_file=Path("fake.yml"),
            retry_delay_seconds=0,
        )
    except SearxngUnavailableError:
        pass
    else:
        raise AssertionError("se esperaba SearxngUnavailableError")


def test_ensure_running_lanza_error_si_docker_compose_falla(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def _raise_urlopen(*args: object, **kwargs: object) -> object:
        raise URLError("conexión rechazada")

    monkeypatch.setattr("devtools.searxng.main.urlopen", _raise_urlopen)
    monkeypatch.setattr(
        "devtools.searxng.main.subprocess.run",
        lambda args, **k: (_ for _ in ()).throw(
            FileNotFoundError("docker no instalado")
        ),
    )

    try:
        ensure_running("http://localhost:8888", compose_file=Path("fake.yml"))
    except SearxngUnavailableError as exc:
        assert "docker" in str(exc).lower()
    else:
        raise AssertionError("se esperaba SearxngUnavailableError")


def test_ensure_running_ignora_urls_no_locales(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "devtools.searxng.main.subprocess.run",
        lambda args, **k: calls.append(args),
    )

    ensure_running("https://searxng.example.com", compose_file=Path("fake.yml"))

    assert calls == []
