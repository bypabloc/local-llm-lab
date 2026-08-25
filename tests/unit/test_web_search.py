import json
from urllib.error import URLError

from core.shell.web_search import extract_search_query, search_web

_TAVILY_PAYLOAD = {
    "results": [
        {
            "title": "Claude Opus 5.1 release notes",
            "url": "https://example.com/opus",
            "content": "Opus 5.1 mejora razonamiento y coding.",
        },
        {
            "title": "Claude Sonnet 5.1 overview",
            "url": "https://example.com/sonnet",
            "content": "Sonnet 5.1 es más rápido para uso diario.",
        },
    ]
}

_SEARXNG_PAYLOAD = {
    "results": [
        {
            "title": "Claude Opus 5.1 release notes",
            "url": "https://example.com/opus",
            "content": "Opus 5.1 mejora razonamiento y coding.",
        },
        {
            "title": "Claude Sonnet 5.1 overview",
            "url": "https://example.com/sonnet",
            "content": "Sonnet 5.1 es más rápido para uso diario.",
        },
    ]
}


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _clear_provider_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("SEARCH_PROVIDER", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SEARXNG_URL", raising=False)


def test_extract_search_query_encuentra_marcador() -> None:
    text = "Necesito buscar eso.\nSEARCH: clima en Santiago hoy\nDame un momento."

    query = extract_search_query(text)

    assert query == "clima en Santiago hoy"


def test_extract_search_query_toma_la_ultima_linea_search() -> None:
    text = "SEARCH: primero\nalgo\nSEARCH: segundo"

    query = extract_search_query(text)

    assert query == "segundo"


def test_extract_search_query_devuelve_none_sin_marcador() -> None:
    query = extract_search_query("respuesta normal sin buscar nada")

    assert query is None


def test_extract_search_query_ignora_marcador_vacio() -> None:
    query = extract_search_query("SEARCH:   \nsin query real")

    assert query is None


def test_search_web_sin_ningun_provider_configurado_devuelve_error(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    _clear_provider_env(monkeypatch)

    outcome = search_web("algo")

    assert outcome.error is not None
    assert outcome.results == []


def test_search_web_tavily_parsea_resultados(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake-key")
    monkeypatch.setattr(
        "core.shell.web_search.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_TAVILY_PAYLOAD).encode("utf-8")),
    )

    outcome = search_web("opus 5.1 vs sonnet 5.1")

    assert outcome.error is None
    assert len(outcome.results) == 2
    assert outcome.results[0].title == "Claude Opus 5.1 release notes"
    assert outcome.results[0].url == "https://example.com/opus"
    assert "razonamiento" in outcome.results[0].snippet
    assert outcome.results[1].title == "Claude Sonnet 5.1 overview"


def test_search_web_tavily_limita_a_max_results(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake-key")
    monkeypatch.setattr(
        "core.shell.web_search.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_TAVILY_PAYLOAD).encode("utf-8")),
    )

    outcome = search_web("algo", max_results=1)

    assert len(outcome.results) == 1


def test_search_web_tavily_sin_resultados_no_es_error(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake-key")
    monkeypatch.setattr(
        "core.shell.web_search.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps({"results": []}).encode()),
    )

    outcome = search_web("query sin resultados")

    assert outcome.error is None
    assert outcome.results == []


def test_search_web_tavily_maneja_json_invalido(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake-key")
    monkeypatch.setattr(
        "core.shell.web_search.urlopen",
        lambda *a, **k: _FakeResponse(b"no es json"),
    )

    outcome = search_web("algo")

    assert outcome.error is not None
    assert outcome.results == []


def test_search_web_searxng_parsea_resultados(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8888")
    monkeypatch.setattr(
        "core.shell.web_search.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_SEARXNG_PAYLOAD).encode("utf-8")),
    )

    outcome = search_web("opus 5.1 vs sonnet 5.1")

    assert outcome.error is None
    assert len(outcome.results) == 2
    assert outcome.results[0].title == "Claude Opus 5.1 release notes"
    assert outcome.results[0].url == "https://example.com/opus"
    assert "razonamiento" in outcome.results[0].snippet


def test_search_web_prioriza_tavily_sobre_searxng_si_ambos_configurados(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake-key")
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8888")

    calls: list[str] = []

    def _fake_urlopen(request: object, timeout: int) -> _FakeResponse:  # type: ignore[no-untyped-def]
        calls.append(request.full_url)  # type: ignore[attr-defined]
        return _FakeResponse(json.dumps(_TAVILY_PAYLOAD).encode("utf-8"))

    monkeypatch.setattr(
        "core.shell.web_search.urlopen",
        _fake_urlopen,
    )

    outcome = search_web("algo")

    assert outcome.error is None
    assert calls == ["https://api.tavily.com/search"]


def test_search_web_cae_a_searxng_si_tavily_falla_y_no_hay_provider_explicito(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake-key")
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8888")

    def _fake_urlopen(request: object, timeout: int) -> _FakeResponse:  # type: ignore[no-untyped-def]
        url = request.full_url  # type: ignore[attr-defined]
        if "tavily" in url:
            raise URLError("tavily caído")
        return _FakeResponse(json.dumps(_SEARXNG_PAYLOAD).encode("utf-8"))

    monkeypatch.setattr("core.shell.web_search.urlopen", _fake_urlopen)

    outcome = search_web("algo")

    assert outcome.error is None
    assert len(outcome.results) == 2


def test_search_web_provider_explicito_searxng_prioriza_searxng(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("SEARCH_PROVIDER", "searxng")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake-key")
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8888")

    calls: list[str] = []

    def _fake_urlopen(request: object, timeout: int) -> _FakeResponse:  # type: ignore[no-untyped-def]
        calls.append(request.full_url)  # type: ignore[attr-defined]
        return _FakeResponse(json.dumps(_SEARXNG_PAYLOAD).encode("utf-8"))

    monkeypatch.setattr("core.shell.web_search.urlopen", _fake_urlopen)

    outcome = search_web("algo")

    assert outcome.error is None
    assert len(calls) == 1
    assert "localhost:8888" in calls[0]


def test_search_web_provider_desconocido_devuelve_error(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("SEARCH_PROVIDER", "google")

    outcome = search_web("algo")

    assert outcome.error is not None
    assert outcome.results == []


def test_search_web_maneja_timeout(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake-key")

    def _raise(*args: object, **kwargs: object) -> None:
        raise TimeoutError("timed out")

    monkeypatch.setattr("core.shell.web_search.urlopen", _raise)

    outcome = search_web("algo", timeout_seconds=1)

    assert outcome.error is not None
    assert outcome.results == []
