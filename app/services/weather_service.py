"""Weather service using Open-Meteo (free, no API key required).

Provides current weather from coordinates and forward/reverse geocoding so the
Outfit Generator can auto-fetch weather with an optional manual override.
"""
import httpx

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Open-Meteo WMO weather codes -> human labels + our internal condition buckets.
_WMO = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm w/ hail",
    99: "Thunderstorm w/ heavy hail",
}


def describe_code(code: int) -> str:
    return _WMO.get(code, "Unknown")


def condition_bucket(code: int, temp_c: float | None, wind_kmh: float | None) -> str:
    """Map raw data to one of the wardrobe weather buckets (Hot/Cold/Rain/...)."""
    if code in {71, 73, 75, 77, 85, 86}:
        return "Snow"
    if code in {51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}:
        return "Rain"
    if wind_kmh is not None and wind_kmh >= 25:
        return "Windy"
    if temp_c is not None and temp_c <= 12:
        return "Cold"
    if temp_c is not None and temp_c >= 26:
        return "Hot"
    return "Mild"


async def geocode(name: str) -> dict | None:
    """City name -> coordinates."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            GEOCODE_URL, params={"name": name, "count": 1, "language": "en"}
        )
        resp.raise_for_status()
        data = resp.json()
    results = data.get("results") or []
    if not results:
        return None
    r = results[0]
    label = ", ".join(
        p for p in [r.get("name"), r.get("admin1"), r.get("country")] if p
    )
    return {"latitude": r["latitude"], "longitude": r["longitude"], "name": label}


async def get_current_weather(
    latitude: float, longitude: float, location_name: str | None = None
) -> dict:
    """Fetch current weather for coordinates via Open-Meteo."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
        "wind_speed_unit": "kmh",
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(FORECAST_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current", {})
    code = int(current.get("weather_code", -1))
    temp = current.get("temperature_2m")
    wind = current.get("wind_speed_10m")
    condition = describe_code(code)
    bucket = condition_bucket(code, temp, wind)

    return {
        "temperature_c": temp,
        "wind_kmh": wind,
        "humidity": current.get("relative_humidity_2m"),
        "weather_code": code,
        "condition": condition,
        "bucket": bucket,
        "location_name": location_name,
        "source": "open-meteo",
    }
