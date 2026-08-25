import json

from core.shell.location import (
    LocationOutcome,
    extract_ip_query,
    extract_location_query,
    extract_weather_query,
    get_location,
    get_public_ip,
    get_weather,
)

_IP_PAYLOAD = {"query": "200.1.2.3"}

_LOCATION_PAYLOAD = {
    "status": "success",
    "city": "Santiago",
    "country": "Chile",
    "lat": -33.4489,
    "lon": -70.6693,
}

_WEATHER_PAYLOAD = {
    "current": {
        "temperature_2m": 18.4,
        "weather_code": 3,
    }
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


def test_extract_ip_query_encuentra_marcador() -> None:
    text = "Necesito tu IP.\nIP:\nDame un momento."

    assert extract_ip_query(text) is True


def test_extract_ip_query_devuelve_false_sin_marcador() -> None:
    assert extract_ip_query("respuesta normal") is False


def test_extract_location_query_encuentra_marcador() -> None:
    text = "Necesito ubicarte.\nLOCATION:\nDame un momento."

    assert extract_location_query(text) is True


def test_extract_location_query_devuelve_false_sin_marcador() -> None:
    assert extract_location_query("respuesta normal") is False


def test_extract_weather_query_encuentra_marcador() -> None:
    text = "WEATHER:"

    assert extract_weather_query(text) is True


def test_extract_weather_query_devuelve_false_sin_marcador() -> None:
    assert extract_weather_query("respuesta normal") is False


def test_extract_ip_query_no_dispara_con_marcador_location() -> None:
    assert extract_ip_query("LOCATION:") is False


def test_extract_ip_query_no_dispara_con_marcador_weather() -> None:
    assert extract_ip_query("WEATHER:") is False


def test_extract_location_query_no_dispara_con_marcador_ip() -> None:
    assert extract_location_query("IP:") is False


def test_extract_weather_query_no_dispara_con_marcador_ip() -> None:
    assert extract_weather_query("IP:") is False


def test_get_public_ip_parsea_respuesta(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "core.shell.location.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_IP_PAYLOAD).encode("utf-8")),
    )

    outcome = get_public_ip()

    assert outcome.error is None
    assert outcome.ip == "200.1.2.3"


def test_get_public_ip_maneja_error_de_red(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def _raise(*args: object, **kwargs: object) -> None:
        raise TimeoutError("timed out")

    monkeypatch.setattr("core.shell.location.urlopen", _raise)

    outcome = get_public_ip()

    assert outcome.error is not None
    assert outcome.ip is None


def test_get_location_usa_ip_dada_y_parsea_ciudad(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "core.shell.location.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_LOCATION_PAYLOAD).encode("utf-8")),
    )

    outcome = get_location(ip="200.1.2.3")

    assert outcome.error is None
    assert outcome.city == "Santiago"
    assert outcome.country == "Chile"
    assert outcome.latitude == -33.4489
    assert outcome.longitude == -70.6693


def test_get_location_falla_si_status_no_es_success(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "core.shell.location.urlopen",
        lambda *a, **k: _FakeResponse(
            json.dumps({"status": "fail", "message": "invalid query"}).encode("utf-8")
        ),
    )

    outcome = get_location(ip="0.0.0.0")

    assert outcome.error is not None
    assert outcome.city is None


def test_get_location_resuelve_ip_propia_si_no_se_pasa(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []

    def _fake_urlopen(request: object, timeout: int) -> _FakeResponse:  # type: ignore[no-untyped-def]
        url = request.full_url  # type: ignore[attr-defined]
        calls.append(url)
        if "ip-api.com/json/" in url:
            return _FakeResponse(json.dumps(_LOCATION_PAYLOAD).encode("utf-8"))
        return _FakeResponse(json.dumps(_IP_PAYLOAD).encode("utf-8"))

    monkeypatch.setattr("core.shell.location.urlopen", _fake_urlopen)

    outcome = get_location(ip=None)

    assert outcome.error is None
    assert outcome.city == "Santiago"
    assert any("ip-api.com/json/200.1.2.3" in url for url in calls)


def test_get_location_propaga_error_si_no_pudo_resolver_ip(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def _raise(*args: object, **kwargs: object) -> None:
        raise TimeoutError("timed out")

    monkeypatch.setattr("core.shell.location.urlopen", _raise)

    outcome = get_location(ip=None)

    assert outcome.error is not None


def test_get_weather_parsea_temperatura(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "core.shell.location.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_WEATHER_PAYLOAD).encode("utf-8")),
    )

    outcome = get_weather(latitude=-33.4489, longitude=-70.6693)

    assert outcome.error is None
    assert outcome.temperature_celsius == 18.4
    assert outcome.weather_code == 3


def test_get_weather_maneja_json_invalido(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "core.shell.location.urlopen",
        lambda *a, **k: _FakeResponse(b"no es json"),
    )

    outcome = get_weather(latitude=0.0, longitude=0.0)

    assert outcome.error is not None
    assert outcome.temperature_celsius is None


def test_get_weather_para_ubicacion_actual_encadena_ip_location_y_clima(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    def _fake_urlopen(request: object, timeout: int) -> _FakeResponse:  # type: ignore[no-untyped-def]
        url = request.full_url  # type: ignore[attr-defined]
        if "ip-api.com/json/200.1.2.3" in url:
            return _FakeResponse(json.dumps(_LOCATION_PAYLOAD).encode("utf-8"))
        if "ip-api.com/json" in url and "/json/" not in url:
            return _FakeResponse(json.dumps(_IP_PAYLOAD).encode("utf-8"))
        return _FakeResponse(json.dumps(_WEATHER_PAYLOAD).encode("utf-8"))

    monkeypatch.setattr("core.shell.location.urlopen", _fake_urlopen)

    from core.shell.location import get_weather_for_current_location

    outcome = get_weather_for_current_location()

    assert outcome.error is None
    assert outcome.city == "Santiago"
    assert outcome.temperature_celsius == 18.4


def test_location_outcome_es_frozen() -> None:
    outcome = LocationOutcome(
        city="Santiago", country="Chile", latitude=0.0, longitude=0.0, error=None
    )

    assert outcome.city == "Santiago"
