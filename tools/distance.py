"""Driving distance/time tool backed by the free OpenRouteService API."""

import os
import re

import httpx
from langchain_core.tools import tool

from tools.net import system_certs_context, use_system_certs

_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"

_COORD_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def _client() -> httpx.Client:
    verify = system_certs_context() if use_system_certs() else True
    return httpx.Client(verify=verify, timeout=15.0)


def _resolve(location: str, api_key: str) -> tuple[float, float, str]:
    """Resolve a location string to (longitude, latitude, label).

    Accepts either a "lat,lon" coordinate pair or a place name, which is
    resolved via ORS geocoding. ORS's free geocoder indexes raw
    OpenStreetMap POI names with no popularity ranking, so a famous
    landmark's top match is sometimes an unrelated same-named business
    (e.g. "Burj Khalifa" can rank a same-named cafe above the actual
    tower). When the top match is an OpenStreetMap "venue" hit, we prefer
    a same-query geonames match instead, since geonames' landmark data is
    curated and less prone to this collision. This does not fully fix
    landmark nicknames with no canonical alias in either dataset (e.g.
    "Eiffel Tower" vs. the indexed "Tour Eiffel") -- official/full names
    resolve more reliably than nicknames.
    """
    match = _COORD_RE.match(location)
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        return lon, lat, f"({lat}, {lon})"

    with _client() as client:
        response = client.get(
            _GEOCODE_URL,
            params={"api_key": api_key, "text": location, "size": 20},
        )
    response.raise_for_status()
    features = response.json().get("features")
    if not features:
        raise ValueError(f"no location found matching '{location}'")

    best = features[0]
    best_props = best["properties"]
    if best_props.get("source") == "openstreetmap" and best_props.get("layer") == "venue":
        geonames_match = next(
            (f for f in features if f["properties"].get("source") == "geonames"), None
        )
        if geonames_match is not None:
            best = geonames_match

    lon, lat = best["geometry"]["coordinates"]
    label = best["properties"].get("label", location)
    return lon, lat, label


@tool
def get_distance(origin: str, destination: str) -> str:
    """Get driving distance and estimated travel time between two locations.

    Provide `origin` and `destination` as place names (e.g. "Dubai
    Airport", "Burj Khalifa") or as "lat,lon" coordinate pairs. Use this
    for trip-planning questions like "distance between Dubai airport and
    Burj Khalifa" or "how long to drive from Karachi to Hyderabad". Backed
    by the free OpenRouteService API (requires ORS_API_KEY from
    openrouteservice.org). Returns driving distance/time only, not flight
    distance. Well-known official names (e.g. "Dubai International
    Airport") and city/address names resolve most reliably; obscure
    nicknames may occasionally match the wrong place.
    """
    api_key = os.getenv("ORS_API_KEY")
    if not api_key:
        return "Error: ORS_API_KEY is not set in the environment; the distance tool is unavailable."

    try:
        origin_lon, origin_lat, origin_label = _resolve(origin.strip(), api_key)
        dest_lon, dest_lat, dest_label = _resolve(destination.strip(), api_key)

        with _client() as client:
            response = client.post(
                _DIRECTIONS_URL,
                headers={"Authorization": api_key, "Content-Type": "application/json"},
                json={
                    "coordinates": [[origin_lon, origin_lat], [dest_lon, dest_lat]],
                    # Unlimited snap radius: points inside large complexes
                    # (airport terminals, etc.) can be >350m from the
                    # nearest routable road, ORS's default snap limit.
                    "radiuses": [-1, -1],
                },
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Error fetching route: {exc}"
    except ValueError as exc:
        return f"Error: {exc}"

    data = response.json()
    routes = data.get("routes")
    if not routes:
        return f"Error: no driving route found between '{origin_label}' and '{dest_label}'."

    summary = routes[0]["summary"]
    distance_km = summary["distance"] / 1000
    duration_min = summary["duration"] / 60

    if duration_min >= 60:
        duration_str = f"{int(duration_min // 60)}h {int(duration_min % 60)}m"
    else:
        duration_str = f"{int(duration_min)} min"

    return (
        f"Driving distance from {origin_label} to {dest_label}: "
        f"{distance_km:.1f} km, approx. {duration_str}."
    )
