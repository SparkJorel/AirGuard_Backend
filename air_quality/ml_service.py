import os
import math
import joblib
import numpy as np
import pandas as pd
from django.conf import settings

MODELS_DIR = os.path.join(settings.BASE_DIR, 'air_quality', 'ml_models')

AI_MODELS = {}
FEATURES = []
CITY_MAPPING = {}
REGION_MAPPING = {}


def load_models():
    global AI_MODELS, FEATURES, CITY_MAPPING, REGION_MAPPING
    try:
        pm25_data = joblib.load(os.path.join(MODELS_DIR, 'airguard_pm25_ensemble.joblib'))

        if isinstance(pm25_data, dict) and 'model' in pm25_data:
            AI_MODELS['pm25'] = pm25_data['model']
            FEATURES = pm25_data.get('features', [])
            CITY_MAPPING = pm25_data.get('city_mapping', {})
            REGION_MAPPING = pm25_data.get('region_mapping', {})
        else:
            AI_MODELS['pm25'] = pm25_data

        def extract_model(filename):
            data = joblib.load(os.path.join(MODELS_DIR, filename))
            return data['model'] if isinstance(data, dict) and 'model' in data else data

        AI_MODELS['heat_index'] = extract_model('airguard_heat_index.joblib')
        AI_MODELS['water_stress'] = extract_model('airguard_deficit_eau_cumule.joblib')
        AI_MODELS['flood_risk'] = extract_model('airguard_risque_inondation.joblib')
        AI_MODELS['extreme_heat'] = extract_model('airguard_chaleur_extreme.joblib')

        print("Les  modèles IA ont été chargés")
    except Exception as e:
        print(f"ERREUR: Impossible de charger les modèles: {e}")


load_models()


def get_aqi_category(pm25_value):
    if pm25_value <= 12.0: return 50, "Bon", "🟢"
    elif pm25_value <= 35.4: return 100, "Modéré", "🟡"
    elif pm25_value <= 55.4: return 150, "Sensible", "🟠"
    elif pm25_value <= 150.4: return 200, "Malsain", "🔴"
    elif pm25_value <= 250.4: return 300, "Très mauvais", "🟣"
    else: return 500, "Dangereux", "🟤"


def get_flood_category(val):
    if val <= 2: return "Risque faible"
    if val <= 4: return "Risque modéré"
    if val <= 6: return "Risque élevé"
    return "Alerte inondation"


def build_features_from_db(ville_nom):
    """Build the 53 features from the latest meteo data in database."""
    from locations.models import Ville
    from meteo.models import ReleveMeteo

    try:
        ville = Ville.objects.select_related('region').get(nom=ville_nom)
    except Ville.DoesNotExist:
        return None

    # Get last 30 days of REAL meteo (not future forecasts)
    from django.utils import timezone
    today = timezone.now().date()
    releves = list(
        ReleveMeteo.objects.filter(ville=ville, date__lte=today)
        .order_by('-date')[:30]
    )

    if not releves:
        return None

    latest = releves[0]
    date = latest.date

    # Safe getter
    def sf(val):
        if val is None:
            return 0.0
        return float(val)

    temp_mean = sf(latest.temperature_2m_mean)
    temp_max = sf(latest.temperature_2m_max)
    temp_min = sf(latest.temperature_2m_min)
    app_temp_mean = sf(latest.apparent_temperature_mean)
    app_temp_max = sf(latest.apparent_temperature_max)
    precip = sf(latest.precipitation_sum)
    rain = sf(latest.rain_sum)
    precip_hours = sf(latest.precipitation_hours)
    wind_max = sf(latest.wind_speed_10m_max)
    wind_gusts = sf(latest.wind_gusts_10m_max)
    radiation = sf(latest.shortwave_radiation_sum)
    et0 = sf(latest.et0_fao_evapotranspiration)
    sunshine = sf(latest.sunshine_duration)
    daylight = sf(latest.daylight_duration) or 1.0

    # Derived features
    temp_amplitude = temp_max - temp_min
    sunshine_ratio = sunshine / daylight if daylight > 0 else 0
    humidity_est = max(0, min(100, 100 - (temp_mean - app_temp_mean) * 5))
    is_no_wind = 1.0 if wind_max < 5 else 0.0
    is_no_rain = 1.0 if precip < 0.1 else 0.0
    month = date.month
    is_dry_season = 1.0 if month >= 11 or month <= 2 else 0.0

    # Temporal encoding
    day_of_year = date.timetuple().tm_yday
    month_sin = math.sin(2 * math.pi * month / 12)
    month_cos = math.cos(2 * math.pi * month / 12)
    dow = date.weekday()
    dow_sin = math.sin(2 * math.pi * dow / 7)
    dow_cos = math.cos(2 * math.pi * dow / 7)
    quarter = (month - 1) // 3 + 1
    year = date.year

    # Lag and rolling features from historical data
    temps = [sf(r.temperature_2m_mean) for r in releves]
    winds = [sf(r.wind_speed_10m_max) for r in releves]
    rains = [sf(r.precipitation_sum) for r in releves]

    def lag(arr, n):
        return arr[n] if n < len(arr) else 0.0

    def roll_mean(arr, n):
        s = arr[:n]
        return sum(s) / len(s) if s else 0.0

    def roll_std(arr, n):
        s = arr[:n]
        if len(s) < 2:
            return 0.0
        m = sum(s) / len(s)
        return math.sqrt(sum((x - m) ** 2 for x in s) / len(s))

    def roll_sum(arr, n):
        return sum(arr[:n])

    features = {
        'temperature_2m_mean': temp_mean,
        'temperature_2m_max': temp_max,
        'temperature_2m_min': temp_min,
        'apparent_temperature_mean': app_temp_mean,
        'apparent_temperature_max': app_temp_max,
        'precipitation_sum': precip,
        'rain_sum': rain,
        'precipitation_hours': precip_hours,
        'wind_speed_10m_max': wind_max,
        'wind_gusts_10m_max': wind_gusts,
        'shortwave_radiation_sum': radiation,
        'et0_fao_evapotranspiration': et0,
        'sunshine_duration': sunshine,
        'daylight_duration': daylight,
        'temp_amplitude': temp_amplitude,
        'sunshine_ratio': sunshine_ratio,
        'humidity_est': humidity_est,
        'is_no_wind': is_no_wind,
        'is_no_rain': is_no_rain,
        'is_dry_season': is_dry_season,
        'month_sin': month_sin,
        'month_cos': month_cos,
        'dow_sin': dow_sin,
        'dow_cos': dow_cos,
        'day_of_year': float(day_of_year),
        'quarter': float(quarter),
        'year': float(year),
        'temp_lag1': lag(temps, 1),
        'temp_lag2': lag(temps, 2),
        'temp_lag3': lag(temps, 3),
        'temp_lag7': lag(temps, 7),
        'temp_lag14': lag(temps, 14),
        'temp_lag30': lag(temps, 29),
        'wind_lag1': lag(winds, 1),
        'wind_lag7': lag(winds, 7),
        'wind_lag14': lag(winds, 14),
        'rain_lag1': lag(rains, 1),
        'rain_lag7': lag(rains, 7),
        'rain_lag14': lag(rains, 14),
        'temp_roll3_mean': roll_mean(temps, 3),
        'temp_roll7_mean': roll_mean(temps, 7),
        'temp_roll14_mean': roll_mean(temps, 14),
        'temp_roll30_mean': roll_mean(temps, 30),
        'temp_roll7_std': roll_std(temps, 7),
        'temp_roll30_std': roll_std(temps, 30),
        'rain_roll3_sum': roll_sum(rains, 3),
        'rain_roll7_sum': roll_sum(rains, 7),
        'rain_roll14_sum': roll_sum(rains, 14),
        'rain_roll30_sum': roll_sum(rains, 30),
        'latitude': ville.latitude,
        'longitude': ville.longitude,
        'region_enc': float(REGION_MAPPING.get(ville.region.nom, 0)),
        'city_enc': float(CITY_MAPPING.get(ville_nom, 0)),
    }

    return features


def predire_tous_les_indicateurs(ville_nom, meteo_data):
    if not AI_MODELS:
        return {"error": "Les modèles ML ne sont pas disponibles sur le serveur."}

    if ville_nom not in CITY_MAPPING:
        return {"error": f"La ville '{ville_nom}' n'est pas reconnue par le modèle."}

    # Build features from DB if no meteo_data provided
    if not meteo_data:
        features = build_features_from_db(ville_nom)
        if features is None:
            return {"error": f"Pas de données météo en base pour '{ville_nom}'."}
    else:
        features = {'city_enc': CITY_MAPPING[ville_nom]}
        for f in FEATURES:
            if f != 'city_enc':
                features[f] = meteo_data.get(f, 0.0)

    df_input = pd.DataFrame([features])[FEATURES]

    try:
        pred_pm25 = AI_MODELS['pm25'].predict(df_input)[0]
        pred_heat = AI_MODELS['heat_index'].predict(df_input)[0]
        pred_water = AI_MODELS['water_stress'].predict(df_input)[0]
        pred_flood = AI_MODELS['flood_risk'].predict(df_input)[0]
        pred_extreme = AI_MODELS['extreme_heat'].predict(df_input)[0]
    except Exception as e:
        return {"error": f"Erreur lors de la prédiction : {str(e)}"}

    aqi_val, aqi_label, aqi_color = get_aqi_category(pred_pm25)

    return {
        "ville": ville_nom,
        "predictions": {
            "qualite_air": {
                "pm25_proxy_ugm3": round(float(pred_pm25), 2),
                "aqi_estime": aqi_val,
                "categorie": aqi_label,
                "alerte_couleur": aqi_color
            },
            "chaleur_sante": {
                "heat_index_ressenti": round(float(pred_heat), 2),
                "chaleur_extreme_0_10": round(float(pred_extreme), 2),
                "avertissement": "Danger" if pred_extreme > 7 else "Normal"
            },
            "risques_naturels": {
                "stress_hydrique_agricole": round(float(pred_water), 2),
                "risque_inondation_0_10": round(float(pred_flood), 2),
                "categorie_inondation": get_flood_category(pred_flood)
            }
        }
    }
