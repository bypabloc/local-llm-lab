from llm.shell.location import (
    extract_ip_query,
    extract_location_query,
    extract_weather_query,
)


def test_extract_ip_query_detecta_marcador() -> None:
    assert extract_ip_query("texto\nIP:\nmas texto") is True


def test_extract_ip_query_sin_marcador() -> None:
    assert extract_ip_query("sin marcador") is False


def test_extract_location_query_detecta_marcador() -> None:
    assert extract_location_query("LOCATION:") is True


def test_extract_weather_query_detecta_marcador() -> None:
    assert extract_weather_query("WEATHER:") is True


def test_extract_weather_query_sin_marcador() -> None:
    assert extract_weather_query("sin marcador") is False
