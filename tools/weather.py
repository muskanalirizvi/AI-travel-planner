"""Weather tool backed by the free Open-Meteo geocoding + forecast APIs."""

from typing import Optional

import httpx
from langchain_core.tools import tool

from tools.net import system_certs_context, use_system_certs

_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_CURRENT_FIELDS = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,"
    "precipitation,weather_code,wind_speed_10m"
)

_WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


def _client() -> httpx.Client:
    verify = system_certs_context() if use_system_certs() else True
    return httpx.Client(verify=verify, timeout=10.0)


def _geocode(location: str) -> tuple[float, float, str]:
    with _client() as client:
        response = client.get(_GEOCODING_URL, params={"name": location, "count": 1})
    response.raise_for_status()
    results = response.json().get("results")
    if not results:
        raise ValueError(f"no location found matching '{location}'")
    match = results[0]
    label = ", ".join(
        part for part in (match.get("name"), match.get("admin1"), match.get("country")) if part
    )
    return match["latitude"], match["longitude"], label


def _fetch_current_weather(latitude: float, longitude: float) -> dict:
    with _client() as client:
        response = client.get(
            _FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": _CURRENT_FIELDS,
                "timezone": "auto",
            },
        )
    response.raise_for_status()
    data = response.json()
    if "current" not in data:
        raise ValueError("forecast API returned no current conditions")
    return data["current"]


@tool
def get_weather(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> str:
    """Get the current weather for a city or coordinates.

    Provide either `location` (a city name, e.g. "Karachi" or "Paris, France")
    or both `latitude` and `longitude`. Use this for questions like "what's
    the weather in Karachi right now" or trip-planning questions about
    current conditions at a destination. Uses the free Open-Meteo API (no
    key required); city names are resolved via Open-Meteo's geocoding
    service and only the best match is used.
    """
    label = location
    try:
        if location and (latitude is None or longitude is None):
            latitude, longitude, label = _geocode(location.strip())
        elif latitude is None or longitude is None:
            return "Error: provide either a location name or both latitude and longitude."

        current = _fetch_current_weather(latitude, longitude)
    except httpx.HTTPError as exc:
        return f"Error fetching weather: {exc}"
    except ValueError as exc:
        return f"Error: {exc}"

    condition = _WEATHER_CODES.get(
        current["weather_code"], f"weather code {current['weather_code']}"
    )
    where = f" in {label}" if label else f" at ({latitude:.4f}, {longitude:.4f})"
    return (
        f"Current weather{where}: {condition}, {current['temperature_2m']}°C "
        f"(feels like {current['apparent_temperature']}°C), "
        f"humidity {current['relative_humidity_2m']}%, "
        f"wind {current['wind_speed_10m']} km/h, as of {current['time']}."
    )
