"""
Service to fetch weather data from Open-Meteo API.
- Historical: last 30 days
- Forecast: next 7 days
No API key needed. Free for non-commercial use.
"""

import logging
from datetime import date, timedelta
import requests
from locations.models import Ville
from meteo.models import ReleveMeteo

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

DAILY_PARAMS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "apparent_temperature_mean",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "daylight_duration",
    "sunshine_duration",
    "shortwave_radiation_sum",
    "et0_fao_evapotranspiration",
]


def fetch_meteo_for_city(ville, start_date, end_date):
    """Fetch weather data from Open-Meteo for a single city."""
    params = {
        "latitude": ville.latitude,
        "longitude": ville.longitude,
        "daily": ",".join(DAILY_PARAMS),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "auto",
    }

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("Open-Meteo error for %s: %s", ville.nom, e)
        return 0

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    if not dates:
        return 0

    objs = []
    for i, date_str in enumerate(dates):
        d = date.fromisoformat(date_str)

        def val(key, idx=i):
            values = daily.get(key, [])
            if idx < len(values) and values[idx] is not None:
                return float(values[idx])
            return None

        objs.append(ReleveMeteo(
            ville=ville,
            date=d,
            weather_code=int(val("weather_code")) if val("weather_code") is not None else None,
            temperature_2m_max=val("temperature_2m_max"),
            temperature_2m_min=val("temperature_2m_min"),
            temperature_2m_mean=val("temperature_2m_mean"),
            apparent_temperature_max=val("apparent_temperature_max"),
            apparent_temperature_min=val("apparent_temperature_min"),
            apparent_temperature_mean=val("apparent_temperature_mean"),
            precipitation_sum=val("precipitation_sum"),
            rain_sum=val("rain_sum"),
            snowfall_sum=val("snowfall_sum"),
            precipitation_hours=val("precipitation_hours"),
            wind_speed_10m_max=val("wind_speed_10m_max"),
            wind_gusts_10m_max=val("wind_gusts_10m_max"),
            wind_direction_10m_dominant=val("wind_direction_10m_dominant"),
            daylight_duration=val("daylight_duration"),
            sunshine_duration=val("sunshine_duration"),
            shortwave_radiation_sum=val("shortwave_radiation_sum"),
            et0_fao_evapotranspiration=val("et0_fao_evapotranspiration"),
        ))

    created = ReleveMeteo.objects.bulk_create(objs, ignore_conflicts=True)
    return len(created)


def fetch_recent_meteo_all_cities():
    """Fetch last 30 days + 7 days forecast for all 40 cities."""
    today = date.today()
    start = today - timedelta(days=30)
    end = today + timedelta(days=7)

    villes = Ville.objects.all()
    total = 0

    for ville in villes:
        count = fetch_meteo_for_city(ville, start, end)
        total += count
        logger.info("%s: %d records", ville.nom, count)

    return total
