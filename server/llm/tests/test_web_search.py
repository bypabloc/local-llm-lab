import pytest

from llm.shell.web_search import extract_search_query, search_web


def test_extract_search_query_devuelve_ultima_consulta_marcada() -> None:
    text = "algo\nSEARCH: clima en santiago\nmas\nSEARCH: dolar hoy"

    assert extract_search_query(text) == "dolar hoy"


def test_extract_search_query_sin_marcador() -> None:
    assert extract_search_query("sin marcador") is None


def test_search_web_sin_provider_configurado_devuelve_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    monkeypatch.delenv("SEARCH_PROVIDER", raising=False)

    outcome = search_web("clima")

    assert outcome.error is not None
    assert outcome.results == []


def test_search_web_provider_explicito_desconocido_devuelve_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEARCH_PROVIDER", "provider-inexistente")

    outcome = search_web("clima")

    assert outcome.error is not None
    assert "desconocido" in outcome.error


def test_search_web_provider_explicito_sin_api_key_devuelve_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEARCH_PROVIDER", "tavily")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    outcome = search_web("clima")

    assert outcome.error is not None
    assert "TAVILY_API_KEY" in outcome.error
