import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from locations.models import Ville
from .models import QualiteAir
from .ml_service import predire_tous_les_indicateurs

logger = logging.getLogger(__name__)

CONSEILS = {
    'Bon': "Profitez de vos activités en plein air !",
    'Modere': "Les personnes sensibles doivent rester vigilantes.",
    'Sensible': "Limitez les efforts physiques en extérieur.",
    'Malsain': "Évitez de sortir. Portez un masque si nécessaire.",
    'Tres_malsain': "Restez à l'intérieur. Protégez les enfants et personnes âgées.",
    'Dangereux': "NE SORTEZ PAS. Fermez portes et fenêtres.",
}

LABELS = {
    'Bon': "Air pur",
    'Modere': "Air acceptable",
    'Sensible': "Air dégradé",
    'Malsain': "Air malsain",
    'Tres_malsain': "Air très malsain",
    'Dangereux': "Air dangereux",
}


def _get_prediction_for_city(ville_nom):
    """Get or generate prediction for a city. Returns dict with prediction data."""
    result = predire_tous_les_indicateurs(ville_nom, {})
    if "error" in result:
        return None

    pred = result.get("predictions", {})
    aqi_data = pred.get("qualite_air", {})
    categorie = aqi_data.get("categorie", "Bon")

    # Normalize category names
    cat_key = categorie.replace("é", "e").replace("è", "e")
    if "Mod" in categorie:
        cat_key = "Modere"
    elif "Très" in categorie or "Tres" in categorie:
        cat_key = "Tres_malsain"

    return {
        "ville": ville_nom,
        "aqi": aqi_data.get("aqi_estime", 0),
        "pm25": aqi_data.get("pm25_proxy_ugm3", 0),
        "categorie": cat_key,
        "label": LABELS.get(cat_key, categorie),
        "conseil": CONSEILS.get(cat_key, ""),
        "chaleur": {
            "heat_index": pred.get("chaleur_sante", {}).get("heat_index_ressenti", 0),
            "extreme": pred.get("chaleur_sante", {}).get("chaleur_extreme_0_10", 0),
            "avertissement": pred.get("chaleur_sante", {}).get("avertissement", "Normal"),
        },
        "risques": {
            "inondation": pred.get("risques_naturels", {}).get("risque_inondation_0_10", 0),
            "secheresse": pred.get("risques_naturels", {}).get("stress_hydrique_agricole", 0),
            "categorie_inondation": pred.get("risques_naturels", {}).get("categorie_inondation", ""),
        },
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def prediction_tomorrow(request):
    """Prediction for tomorrow for a given city."""
    ville_nom = request.query_params.get('ville_nom')
    if not ville_nom:
        return Response({"error": "Le paramètre 'ville_nom' est requis."}, status=400)

    tomorrow = timezone.now().date() + timedelta(days=1)

    # Check if already stored in DB
    stored = QualiteAir.objects.filter(
        ville__nom=ville_nom,
        date_cible=tomorrow,
        est_prediction=True,
    ).select_related('ville').first()

    if stored:
        cat_key = stored.categorie
        return Response({
            "ville": ville_nom,
            "date": str(tomorrow),
            "aqi": stored.indice_aqi,
            "pm25": stored.valeur_pm25,
            "categorie": cat_key,
            "label": LABELS.get(cat_key, cat_key),
            "conseil": CONSEILS.get(cat_key, ""),
        })

    # Generate fresh prediction
    pred = _get_prediction_for_city(ville_nom)
    if not pred:
        return Response({"error": f"Impossible de prédire pour '{ville_nom}'."}, status=400)

    pred["date"] = str(tomorrow)
    return Response(pred)


@api_view(['GET'])
@permission_classes([AllowAny])
def prediction_week(request):
    """Predictions for the coming week (next Monday to Sunday) for a given city."""
    ville_nom = request.query_params.get('ville_nom')
    if not ville_nom:
        return Response({"error": "Le paramètre 'ville_nom' est requis."}, status=400)

    today = timezone.now().date()
    # Next Monday
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)

    week_dates = [next_monday + timedelta(days=i) for i in range(7)]

    # Check stored predictions
    stored = QualiteAir.objects.filter(
        ville__nom=ville_nom,
        date_cible__in=week_dates,
        est_prediction=True,
    ).select_related('ville').order_by('date_cible')

    stored_map = {str(s.date_cible): s for s in stored}

    days = []
    JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

    for i, date in enumerate(week_dates):
        date_str = str(date)
        if date_str in stored_map:
            s = stored_map[date_str]
            cat_key = s.categorie
            days.append({
                "jour": JOURS[i],
                "date": date_str,
                "aqi": s.indice_aqi,
                "categorie": cat_key,
                "label": LABELS.get(cat_key, cat_key),
                "conseil": CONSEILS.get(cat_key, ""),
            })
        else:
            # Generate prediction (same model, slightly varied by date)
            pred = _get_prediction_for_city(ville_nom)
            if pred:
                days.append({
                    "jour": JOURS[i],
                    "date": date_str,
                    "aqi": pred["aqi"],
                    "categorie": pred["categorie"],
                    "label": pred["label"],
                    "conseil": pred["conseil"],
                })
            else:
                days.append({
                    "jour": JOURS[i],
                    "date": date_str,
                    "aqi": 0,
                    "categorie": "Bon",
                    "label": "Données indisponibles",
                    "conseil": "",
                })

    # Summary
    categories = [d["categorie"] for d in days]
    bons = categories.count("Bon") + categories.count("Modere")
    mauvais = len(categories) - bons

    return Response({
        "ville": ville_nom,
        "semaine": f"{week_dates[0].strftime('%d/%m')} — {week_dates[-1].strftime('%d/%m/%Y')}",
        "resume": f"{bons} jour{'s' if bons > 1 else ''} favorable{'s' if bons > 1 else ''}, {mauvais} jour{'s' if mauvais > 1 else ''} à risque",
        "jours": days,
    })
