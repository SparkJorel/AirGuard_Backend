import os
import math
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
import pandas as pd

from locations.models import Ville
from meteo.models import ReleveMeteo
from air_quality.models import QualiteAir


def safe_float(val):
    """Convert any value to float, return None if impossible."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def compute_pm25_proxy(row):
    """Compute PM2.5 proxy from meteo variables (same formula as starter notebook)."""
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

    # Determine dry season (Nov-Feb)
    time_val = row.get("time")
    month = 1
    if hasattr(time_val, "month"):
        month = time_val.month
    is_dry = 1 if month >= 11 or month <= 2 else 0

    pm25 = (
        0.35 * temp
        + 0.25 * (radiation / 100)
        + 0.20 * et0
        + 8.0 * is_no_wind
        + 5.0 * is_no_rain
        + 4.0 * is_dry
        + 2.0 * sunshine_ratio
    )
    return max(pm25, 0)


def pm25_to_aqi(pm25):
    """Convert PM2.5 proxy to AQI index and category."""
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


class Command(BaseCommand):
    help = "Charge les données météo du dataset et génère les données AQI"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Chemin vers le fichier Excel du dataset",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Nombre max de lignes à importer (pour tester)",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        if not file_path:
            # Try common locations
            candidates = [
                os.path.join(settings.BASE_DIR, "..", "HACKATHON-INDABAX-CAMEROON-2026-main", "data", "Dataset_complet_Meteo.xlsx"),
                os.path.join(settings.BASE_DIR, "..", "data", "Dataset_complet_Meteo.xlsx"),
                os.path.join(settings.BASE_DIR, "data", "Dataset_complet_Meteo.xlsx"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    file_path = c
                    break

        if not file_path or not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(
                "Dataset non trouvé. Utilisez --file pour spécifier le chemin."
            ))
            return

        self.stdout.write(f"Chargement de {file_path}...")
        nrows = options["limit"]
        df = pd.read_excel(file_path, nrows=nrows)
        self.stdout.write(f"  {len(df)} lignes chargées")

        # Convert numeric columns
        numeric_cols = [
            "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
            "apparent_temperature_max", "apparent_temperature_min", "apparent_temperature_mean",
            "wind_speed_10m_max", "wind_gusts_10m_max", "shortwave_radiation_sum",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Build ville lookup
        ville_lookup = {}
        for v in Ville.objects.all():
            ville_lookup[v.nom] = v

        if not ville_lookup:
            self.stderr.write(self.style.ERROR(
                "Aucune ville en base. Lancez d'abord: python manage.py seed_locations"
            ))
            return

        meteo_created = 0
        aqi_created = 0
        skipped = 0

        # Process in batches
        meteo_batch = []
        aqi_batch = []
        batch_size = 500

        for _, row in df.iterrows():
            city_name = row.get("city")
            ville = ville_lookup.get(city_name)
            if not ville:
                skipped += 1
                continue

            # Parse date
            time_val = row.get("time")
            if hasattr(time_val, "date"):
                date = time_val.date()
            else:
                try:
                    date = datetime.strptime(str(time_val)[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    skipped += 1
                    continue

            # Create meteo record
            meteo_batch.append(ReleveMeteo(
                ville=ville,
                date=date,
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

            # Compute AQI
            pm25 = compute_pm25_proxy(row)
            aqi_val, categorie = pm25_to_aqi(pm25)
            aqi_batch.append(QualiteAir(
                ville=ville,
                date_cible=date,
                valeur_pm25=round(pm25, 2),
                indice_aqi=aqi_val,
                categorie=categorie,
                est_prediction=False,
                facteurs_aggravants=None,
            ))

            if len(meteo_batch) >= batch_size:
                ReleveMeteo.objects.bulk_create(meteo_batch, ignore_conflicts=True)
                QualiteAir.objects.bulk_create(aqi_batch, ignore_conflicts=True)
                meteo_created += len(meteo_batch)
                aqi_created += len(aqi_batch)
                self.stdout.write(f"  {meteo_created} météo, {aqi_created} AQI...")
                meteo_batch = []
                aqi_batch = []

        # Final batch
        if meteo_batch:
            ReleveMeteo.objects.bulk_create(meteo_batch, ignore_conflicts=True)
            QualiteAir.objects.bulk_create(aqi_batch, ignore_conflicts=True)
            meteo_created += len(meteo_batch)
            aqi_created += len(aqi_batch)

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé : {meteo_created} relevés météo, {aqi_created} données AQI créées. {skipped} lignes ignorées."
        ))
