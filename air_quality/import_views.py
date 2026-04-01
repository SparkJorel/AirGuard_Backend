import math
from datetime import datetime
import pandas as pd
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from locations.models import Ville
from meteo.models import ReleveMeteo
from air_quality.models import QualiteAir


def safe_float(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def compute_pm25_proxy(row):
    temp = safe_float(row.get("temperature_2m_mean")) or 0
    radiation = safe_float(row.get("shortwave_radiation_sum")) or 0
    et0 = safe_float(row.get("et0_fao_evapotranspiration")) or 0
    wind = safe_float(row.get("wind_speed_10m_max")) or 5
    precip = safe_float(row.get("precipitation_sum")) or 0
    sunshine = safe_float(row.get("sunshine_duration")) or 0
    daylight = safe_float(row.get("daylight_duration")) or 1

    is_no_wind = 1 if wind < 5 else 0
    is_no_rain = 1 if precip < 0.1 else 0
    sunshine_ratio = sunshine / daylight if daylight > 0 else 0

    time_val = row.get("time")
    month = 1
    if hasattr(time_val, "month"):
        month = time_val.month
    is_dry = 1 if month >= 11 or month <= 2 else 0

    pm25 = (
        0.35 * temp + 0.25 * (radiation / 100) + 0.20 * et0
        + 8.0 * is_no_wind + 5.0 * is_no_rain + 4.0 * is_dry + 2.0 * sunshine_ratio
    )
    return max(pm25, 0)


def pm25_to_aqi(pm25):
    if pm25 <= 12:
        return int(pm25 / 12 * 50), "Bon"
    elif pm25 <= 35.4:
        return int(50 + (pm25 - 12) / 23.4 * 50), "Modere"
    elif pm25 <= 55.4:
        return int(100 + (pm25 - 35.4) / 20 * 50), "Sensible"
    elif pm25 <= 150.4:
        return int(150 + (pm25 - 55.4) / 95 * 50), "Malsain"
    elif pm25 <= 250.4:
        return int(200 + (pm25 - 150.4) / 100 * 100), "Tres_malsain"
    else:
        return min(int(300 + (pm25 - 250.4) / 150 * 200), 500), "Dangereux"


@api_view(["POST"])
@parser_classes([MultiPartParser])
def import_dataset(request):
    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Aucun fichier fourni."}, status=400)

    name = file.name.lower()
    if not (name.endswith(".xlsx") or name.endswith(".csv")):
        return Response({"error": "Format non supporté. Utilisez .xlsx ou .csv"}, status=400)

    try:
        if name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        return Response({"error": f"Impossible de lire le fichier : {str(e)}"}, status=400)

    # Convert numeric columns
    numeric_cols = [
        "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
        "apparent_temperature_max", "apparent_temperature_min", "apparent_temperature_mean",
        "wind_speed_10m_max", "wind_gusts_10m_max", "shortwave_radiation_sum",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    ville_lookup = {v.nom: v for v in Ville.objects.all()}
    if not ville_lookup:
        return Response({"error": "Aucune ville en base. Lancez seed_locations d'abord."}, status=400)

    meteo_batch = []
    aqi_batch = []
    skipped = 0

    for _, row in df.iterrows():
        ville = ville_lookup.get(row.get("city"))
        if not ville:
            skipped += 1
            continue

        time_val = row.get("time")
        if hasattr(time_val, "date"):
            date = time_val.date()
        else:
            try:
                date = datetime.strptime(str(time_val)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                skipped += 1
                continue

        meteo_batch.append(ReleveMeteo(
            ville=ville, date=date,
            temperature_2m_max=safe_float(row.get("temperature_2m_max")),
            temperature_2m_min=safe_float(row.get("temperature_2m_min")),
            temperature_2m_mean=safe_float(row.get("temperature_2m_mean")),
            apparent_temperature_max=safe_float(row.get("apparent_temperature_max")),
            apparent_temperature_min=safe_float(row.get("apparent_temperature_min")),
            apparent_temperature_mean=safe_float(row.get("apparent_temperature_mean")),
            weather_code=int(row["weather_code"]) if safe_float(row.get("weather_code")) is not None else None,
            precipitation_sum=safe_float(row.get("precipitation_sum")),
            rain_sum=safe_float(row.get("rain_sum")),
            snowfall_sum=safe_float(row.get("snowfall_sum")),
            precipitation_hours=safe_float(row.get("precipitation_hours")),
            wind_speed_10m_max=safe_float(row.get("wind_speed_10m_max")),
            wind_gusts_10m_max=safe_float(row.get("wind_gusts_10m_max")),
            wind_direction_10m_dominant=safe_float(row.get("wind_direction_10m_dominant")),
            daylight_duration=safe_float(row.get("daylight_duration")),
            sunshine_duration=safe_float(row.get("sunshine_duration")),
            shortwave_radiation_sum=safe_float(row.get("shortwave_radiation_sum")),
            et0_fao_evapotranspiration=safe_float(row.get("et0_fao_evapotranspiration")),
        ))

        pm25 = compute_pm25_proxy(row)
        aqi_val, categorie = pm25_to_aqi(pm25)
        aqi_batch.append(QualiteAir(
            ville=ville, date_cible=date,
            valeur_pm25=round(pm25, 2), indice_aqi=aqi_val,
            categorie=categorie, est_prediction=False,
        ))

    meteo_count = len(meteo_batch)
    aqi_count = len(aqi_batch)
    ReleveMeteo.objects.bulk_create(meteo_batch, ignore_conflicts=True)
    QualiteAir.objects.bulk_create(aqi_batch, ignore_conflicts=True)

    return Response({
        "success": True,
        "meteo_importes": meteo_count,
        "aqi_generes": aqi_count,
        "lignes_ignorees": skipped,
        "total_lignes": len(df),
    })
