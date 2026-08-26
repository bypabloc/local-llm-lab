import json
import os
import re
from dataclasses import dataclass, field
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_SEARCH_PATTERN = re.compile(r"^SEARCH:[ \t]*(\S.*)?$", re.MULTILINE)

_TAVILY_URL = "https://api.tavily.com/search"
_TAVILY_API_KEY_ENV_VAR = "TAVILY_API_KEY"
_SEARXNG_URL_ENV_VAR = "SEARXNG_URL"
_PROVIDER_ENV_VAR = "SEARCH_PROVIDER"


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    query: str
    results: list[SearchResult] = field(default_factory=list)
    error: str | None = None


def extract_search_query(text: str) -> str | None:
    """Devuelve la última consulta marcada con 'SEARCH: <query>' en `text`, o None."""
    matches = _SEARCH_PATTERN.findall(text)
    if not matches:
        return None
    query = matches[-1].strip()
    return query or None


def _fetch_json(request: Request, timeout_seconds: int) -> dict[str, object]:
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        payload: dict[str, object] = json.loads(response.read().decode("utf-8"))
        return payload


def _parse_flat_results(
    payload: dict[str, object], max_results: int, snippet_key: str
) -> list[SearchResult]:
    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        return []
    return [
        SearchResult(
            title=str(item.get("title", "")),
            url=str(item.get("url", "")),
            snippet=str(item.get(snippet_key, "")),
        )
        for item in raw_results[:max_results]
        if isinstance(item, dict)
    ]


def _search_tavily(query: str, max_results: int, timeout_seconds: int) -> SearchOutcome:
    api_key = os.environ.get(_TAVILY_API_KEY_ENV_VAR)
    if not api_key:
        return SearchOutcome(
            query=query,
            error=f"falta la variable de entorno {_TAVILY_API_KEY_ENV_VAR}",
        )

    body = json.dumps({"query": query, "max_results": max_results}).encode("utf-8")
    request = Request(
        _TAVILY_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        payload = _fetch_json(request, timeout_seconds)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return SearchOutcome(query=query, error=str(exc))

    return SearchOutcome(
        query=query, results=_parse_flat_results(payload, max_results, "content")
    )


def _search_searxng(
    query: str, max_results: int, timeout_seconds: int
) -> SearchOutcome:
    base_url = os.environ.get(_SEARXNG_URL_ENV_VAR)
    if not base_url:
        return SearchOutcome(
            query=query,
            error=f"falta la variable de entorno {_SEARXNG_URL_ENV_VAR}",
        )

    params = urlencode({"q": query, "format": "json"})
    request = Request(
        f"{base_url.rstrip('/')}/search?{params}",
        headers={"Accept": "application/json"},
    )
    try:
        payload = _fetch_json(request, timeout_seconds)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return SearchOutcome(query=query, error=str(exc))

    return SearchOutcome(
        query=query, results=_parse_flat_results(payload, max_results, "content")
    )


_PROVIDERS = {"tavily": _search_tavily, "searxng": _search_searxng}


def _available_providers() -> list[str]:
    available = []
    if os.environ.get(_TAVILY_API_KEY_ENV_VAR):
        available.append("tavily")
    if os.environ.get(_SEARXNG_URL_ENV_VAR):
        available.append("searxng")
    return available


def search_web(
    query: str, max_results: int = 5, timeout_seconds: int = 10
) -> SearchOutcome:
    """Busca `query` con el provider configurado (o auto-detectado).

    Providers disponibles:
    - `tavily`: requiere TAVILY_API_KEY (free tier sin tarjeta en tavily.com).
    - `searxng`: instancia propia, requiere SEARXNG_URL (ej. http://localhost:8888)
      — sin API key, útil para desarrollo local.

    Si SEARCH_PROVIDER no está seteada, se prioriza tavily y se cae a searxng
    si está configurado. Si el provider elegido (explícito o auto-detectado)
    falla y hay otro disponible sin que se haya pedido uno específico, se
    reintenta con el siguiente antes de devolver error.
    """
    explicit_provider = os.environ.get(_PROVIDER_ENV_VAR)
    if explicit_provider:
        provider = _PROVIDERS.get(explicit_provider)
        if provider is None:
            return SearchOutcome(
                query=query,
                error=(
                    f"provider de búsqueda desconocido: '{explicit_provider}' "
                    f"(disponibles: {', '.join(_PROVIDERS)})"
                ),
            )
        return provider(query, max_results, timeout_seconds)

    candidates = _available_providers()
    if not candidates:
        return SearchOutcome(
            query=query,
            error=(
                f"ningún provider de búsqueda configurado — seteá "
                f"{_TAVILY_API_KEY_ENV_VAR} o {_SEARXNG_URL_ENV_VAR}"
            ),
        )

    outcome = SearchOutcome(query=query)
    for name in candidates:
        outcome = _PROVIDERS[name](query, max_results, timeout_seconds)
        if outcome.error is None:
            return outcome
    return outcome
