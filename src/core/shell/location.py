import json
import re
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_IP_PATTERN = re.compile(r"^IP:", re.MULTILINE)
_LOCATION_PATTERN = re.compile(r"^LOCATION:", re.MULTILINE)
_WEATHER_PATTERN = re.compile(r"^WEATHER:", re.MULTILINE)

# ponytail: ip-api.com free tier no soporta HTTPS (403 "SSL unavailable for
# this endpoint"), solo HTTP plano. HTTPS requiere key de pago.
_IP_URL = "http://ip-api.com/json"
_LOCATION_URL = "http://ip-api.com/json/{ip}"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(frozen=True, slots=True)
class IpOutcome:
    ip: str | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class LocationOutcome:
    city: str | None
    country: str | None
    latitude: float | None
    longitude: float | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class WeatherOutcome:
    temperature_celsius: float | None
    weather_code: int | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class WeatherForLocationOutcome:
    city: str | None
    country: str | None
    temperature_celsius: float | None
    weather_code: int | None
    error: str | None = None


def extract_ip_query(text: str) -> bool:
    """True si `text` contiene el marcador 'IP:'."""
    return bool(_IP_PATTERN.search(text))


def extract_location_query(text: str) -> bool:
    """True si `text` contiene el marcador 'LOCATION:'."""
    return bool(_LOCATION_PATTERN.search(text))


def extract_weather_query(text: str) -> bool:
    """True si `text` contiene el marcador 'WEATHER:'."""
    return bool(_WEATHER_PATTERN.search(text))


def _fetch_json(request: Request, timeout_seconds: int) -> dict[str, object]:
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        payload: dict[str, object] = json.loads(response.read().decode("utf-8"))
        return payload


def get_public_ip(timeout_seconds: int = 10) -> IpOutcome:
    """Resuelve la IP pública actual vía ip-api.com."""
    try:
        payload = _fetch_json(Request(_IP_URL), timeout_seconds)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return IpOutcome(ip=None, error=str(exc))
    return IpOutcome(ip=str(payload.get("query", "")) or None)


def get_location(ip: str | None = None, timeout_seconds: int = 10) -> LocationOutcome:
    """Geolocaliza `ip` (o la IP pública propia si no se pasa) vía ip-api.com."""
    if ip is None:
        ip_outcome = get_public_ip(timeout_seconds)
        if ip_outcome.ip is None:
            return LocationOutcome(
                city=None,
                country=None,
                latitude=None,
                longitude=None,
                error=ip_outcome.error or "no se pudo resolver la IP pública",
            )
        ip = ip_outcome.ip

    try:
        payload = _fetch_json(Request(_LOCATION_URL.format(ip=ip)), timeout_seconds)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return LocationOutcome(
            city=None, country=None, latitude=None, longitude=None, error=str(exc)
        )

    if payload.get("status") != "success":
        return LocationOutcome(
            city=None,
            country=None,
            latitude=None,
            longitude=None,
            error=str(payload.get("message", "geolocalización falló")),
        )

    return LocationOutcome(
        city=str(payload.get("city", "")) or None,
        country=str(payload.get("country", "")) or None,
        latitude=float(payload["lat"]) if "lat" in payload else None,  # type: ignore[arg-type]
        longitude=float(payload["lon"]) if "lon" in payload else None,  # type: ignore[arg-type]
    )


def get_weather(
    latitude: float, longitude: float, timeout_seconds: int = 10
) -> WeatherOutcome:
    """Clima actual en `latitude`/`longitude` vía Open-Meteo."""
    params = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code",
        }
    )
    try:
        payload = _fetch_json(Request(f"{_WEATHER_URL}?{params}"), timeout_seconds)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return WeatherOutcome(
            temperature_celsius=None, weather_code=None, error=str(exc)
        )

    current = payload.get("current")
    if not isinstance(current, dict):
        return WeatherOutcome(
            temperature_celsius=None,
            weather_code=None,
            error="respuesta de Open-Meteo sin datos 'current'",
        )

    return WeatherOutcome(
        temperature_celsius=float(current["temperature_2m"])
        if "temperature_2m" in current
        else None,
        weather_code=int(current["weather_code"])
        if "weather_code" in current
        else None,
    )


def get_weather_for_current_location(
    timeout_seconds: int = 10,
) -> WeatherForLocationOutcome:
    """Encadena get_location + get_weather para la IP pública actual."""
    location = get_location(ip=None, timeout_seconds=timeout_seconds)
    if (
        location.error is not None
        or location.latitude is None
        or location.longitude is None
    ):
        return WeatherForLocationOutcome(
            city=None,
            country=None,
            temperature_celsius=None,
            weather_code=None,
            error=location.error or "ubicación sin coordenadas",
        )

    weather = get_weather(location.latitude, location.longitude, timeout_seconds)
    return WeatherForLocationOutcome(
        city=location.city,
        country=location.country,
        temperature_celsius=weather.temperature_celsius,
        weather_code=weather.weather_code,
        error=weather.error,
    )
