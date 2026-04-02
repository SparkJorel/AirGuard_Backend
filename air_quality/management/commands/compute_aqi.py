"""
Compute PM2.5 proxy and AQI for all meteo records that don't have an AQI entry yet.
Usage: python manage.py compute_aqi
"""

from django.core.management.base import BaseCommand
from meteo.models import ReleveMeteo
from air_quality.models import QualiteAir


def compute_pm25(meteo):
    """Estimate PM2.5 from meteorological variables."""
    temp = meteo.temperature_2m_mean or 0
    radiation = meteo.shortwave_radiation_sum or 0
    et0 = meteo.et0_fao_evapotranspiration or 0
    wind = meteo.wind_speed_10m_max or 5
    precip = meteo.precipitation_sum or 0
    sunshine = meteo.sunshine_duration or 0
    daylight = meteo.daylight_duration or 1

    is_no_wind = 1 if wind < 5 else 0
    is_no_rain = 1 if precip < 0.1 else 0
    sunshine_ratio = sunshine / daylight if daylight > 0 else 0
    month = meteo.date.month
    is_dry = 1 if month >= 11 or month <= 2 else 0

    pm25 = (
        0.35 * temp + 0.25 * (radiation / 100) + 0.20 * et0
        + 8.0 * is_no_wind + 5.0 * is_no_rain + 4.0 * is_dry + 2.0 * sunshine_ratio
    )
    return max(pm25, 0)


def pm25_to_aqi(pm25):
    """Convert PM2.5 value to AQI index and category."""
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
    help = "Compute AQI for meteo records without AQI data"

    def handle(self, *args, **options):
        # Find meteo records that don't have a corresponding AQI entry
        existing = set(
            QualiteAir.objects.filter(est_prediction=False)
            .values_list('ville_id', 'date_cible')
        )

        meteo_records = ReleveMeteo.objects.select_related('ville').all()

        objs = []
        for m in meteo_records:
            if (m.ville_id, m.date) in existing:
                continue

            pm25 = compute_pm25(m)
            aqi_val, categorie = pm25_to_aqi(pm25)

            objs.append(QualiteAir(
                ville=m.ville,
                date_cible=m.date,
                valeur_pm25=round(pm25, 2),
                indice_aqi=aqi_val,
                categorie=categorie,
                est_prediction=False,
            ))

        if objs:
            QualiteAir.objects.bulk_create(objs, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"Computed AQI for {len(objs)} new records"))
