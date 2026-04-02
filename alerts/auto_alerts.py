"""
Service de génération automatique d'alertes par le modèle ML.
Analyse les dernières données AQI et crée des alertes brouillon
avec recommandations détaillées pour résidents et visiteurs.
"""

from django.utils import timezone
from locations.models import Ville
from air_quality.models import QualiteAir
from alerts.models import Alerte


# Seuils de déclenchement
SEUILS = {
    'modere': {'aqi_min': 101, 'aqi_max': 150},
    'grave': {'aqi_min': 151, 'aqi_max': 200},
    'critique': {'aqi_min': 201, 'aqi_max': 999},
}

RECOMMANDATIONS = {
    'modere': {
        'residents_fr': (
            "Recommandations pour les résidents :\n"
            "• Les personnes sensibles (asthmatiques, enfants, personnes âgées) doivent limiter les activités prolongées en extérieur\n"
            "• Fermez les fenêtres aux heures de pointe (7h-9h et 17h-19h)\n"
            "• Privilégiez les activités sportives en intérieur\n"
            "• Si vous ressentez des irritations (yeux, gorge), restez à l'intérieur\n"
            "• Hydratez-vous régulièrement"
        ),
        'residents_en': (
            "Recommendations for residents:\n"
            "• Sensitive groups (asthma, children, elderly) should limit prolonged outdoor activities\n"
            "• Close windows during peak hours (7-9am and 5-7pm)\n"
            "• Prefer indoor sports activities\n"
            "• If you experience irritation (eyes, throat), stay indoors\n"
            "• Stay well hydrated"
        ),
        'visiteurs_fr': (
            "Recommandations pour les visiteurs :\n"
            "• La qualité de l'air est dégradée dans cette zone\n"
            "• Si vous prévoyez de vous y rendre, limitez votre temps en extérieur\n"
            "• Emportez un masque de protection si vous êtes sensible\n"
            "• Évitez les activités physiques intenses en plein air\n"
            "• Consultez l'évolution de l'AQI avant votre déplacement"
        ),
        'visiteurs_en': (
            "Recommendations for visitors:\n"
            "• Air quality is degraded in this area\n"
            "• If you plan to visit, limit your time outdoors\n"
            "• Bring a protective mask if you are sensitive\n"
            "• Avoid intense outdoor physical activities\n"
            "• Check AQI trends before traveling"
        ),
        'duree': '24 à 48 heures',
    },
    'grave': {
        'residents_fr': (
            "ALERTE SANTÉ — Recommandations urgentes pour les résidents :\n"
            "• RESTEZ À L'INTÉRIEUR autant que possible\n"
            "• Fermez toutes les fenêtres et portes — utilisez un ventilateur avec filtre si disponible\n"
            "• Les personnes asthmatiques doivent garder leur inhalateur à portée de main\n"
            "• Portez un masque FFP2/N95 si vous devez absolument sortir\n"
            "• Ne faites AUCUNE activité sportive en extérieur\n"
            "• Surveillez les enfants et les personnes âgées — signes à observer : toux, essoufflement, irritation des yeux\n"
            "• Évitez de cuisiner avec des combustibles (charbon, bois) — cela aggrave la pollution intérieure\n"
            "• Si vous avez des difficultés respiratoires, consultez un médecin immédiatement"
        ),
        'residents_en': (
            "HEALTH ALERT — Urgent recommendations for residents:\n"
            "• STAY INDOORS as much as possible\n"
            "• Close all windows and doors — use a fan with filter if available\n"
            "• Asthma patients must keep their inhaler within reach\n"
            "• Wear an FFP2/N95 mask if you absolutely must go outside\n"
            "• Do NOT exercise outdoors\n"
            "• Monitor children and elderly — watch for: coughing, shortness of breath, eye irritation\n"
            "• Avoid cooking with combustibles (charcoal, wood) — it worsens indoor pollution\n"
            "• If you experience breathing difficulties, see a doctor immediately"
        ),
        'visiteurs_fr': (
            "ALERTE — Recommandations pour les personnes hors de la zone :\n"
            "• ÉVITEZ de vous rendre dans cette ville pendant cette période si possible\n"
            "• Si vous devez y aller : portez un masque FFP2/N95, limitez votre séjour au strict minimum\n"
            "• Gardez les vitres de votre véhicule fermées et la climatisation en mode recirculation\n"
            "• Reportez tout déplacement non essentiel de 48 à 72 heures\n"
            "• Si vous êtes une personne à risque (asthme, maladie cardiaque, grossesse), ne vous déplacez pas vers cette zone"
        ),
        'visiteurs_en': (
            "ALERT — Recommendations for people outside the area:\n"
            "• AVOID traveling to this city during this period if possible\n"
            "• If you must go: wear an FFP2/N95 mask, limit your stay to the strict minimum\n"
            "• Keep vehicle windows closed and AC on recirculation mode\n"
            "• Postpone any non-essential travel by 48 to 72 hours\n"
            "• If you are at risk (asthma, heart disease, pregnancy), do not travel to this area"
        ),
        'duree': '48 à 72 heures',
    },
    'critique': {
        'residents_fr': (
            "🚨 URGENCE SANITAIRE — Recommandations critiques pour les résidents :\n"
            "• NE SORTEZ PAS — Restez confiné à l'intérieur impérativement\n"
            "• Scellez les ouvertures (fenêtres, portes) avec des serviettes humides si nécessaire\n"
            "• Les personnes vulnérables (enfants de moins de 5 ans, personnes âgées de plus de 65 ans, femmes enceintes, malades chroniques) doivent être évacuées si possible vers une zone sûre\n"
            "• Portez un masque FFP2/N95 même à l'intérieur si vous sentez une odeur ou irritation\n"
            "• NE FAITES PAS de feu, ne cuisinez pas au charbon ou au bois\n"
            "• Appelez les urgences (119) si vous ressentez : douleurs thoraciques, essoufflement sévère, vertiges\n"
            "• Hydratez-vous abondamment — buvez au moins 2 litres d'eau par jour\n"
            "• Préparez un kit d'urgence : médicaments, eau, masques, lampe torche\n"
            "• Suivez les consignes des autorités sanitaires locales\n"
            "• Si vous devez absolument quitter votre domicile, couvrez votre nez et bouche, et minimisez le temps dehors"
        ),
        'residents_en': (
            "🚨 HEALTH EMERGENCY — Critical recommendations for residents:\n"
            "• DO NOT GO OUTSIDE — Stay confined indoors\n"
            "• Seal openings (windows, doors) with wet towels if necessary\n"
            "• Vulnerable people (children under 5, elderly over 65, pregnant women, chronically ill) should be evacuated to a safe area if possible\n"
            "• Wear an FFP2/N95 mask even indoors if you smell or feel irritation\n"
            "• DO NOT make fires, do not cook with charcoal or wood\n"
            "• Call emergency services (119) if you experience: chest pain, severe shortness of breath, dizziness\n"
            "• Stay well hydrated — drink at least 2 liters of water per day\n"
            "• Prepare an emergency kit: medications, water, masks, flashlight\n"
            "• Follow local health authority guidelines\n"
            "• If you absolutely must leave home, cover your nose and mouth, minimize time outdoors"
        ),
        'visiteurs_fr': (
            "🚨 URGENCE — NE VOUS RENDEZ PAS dans cette zone :\n"
            "• INTERDICTION FORMELLE de se rendre dans cette ville — danger sanitaire immédiat\n"
            "• Si vous êtes en route, faites demi-tour ou contournez la zone\n"
            "• Si vous êtes déjà sur place, quittez la ville dès que possible par le chemin le plus court\n"
            "• Gardez toutes les vitres fermées dans votre véhicule\n"
            "• Si vous ne pouvez pas partir, réfugiez-vous dans un bâtiment fermé et suivez les consignes des résidents\n"
            "• Informez vos proches de votre situation et localisation\n"
            "• Cette alerte est valable pour une durée estimée de 72h à 1 semaine"
        ),
        'visiteurs_en': (
            "🚨 EMERGENCY — DO NOT TRAVEL to this area:\n"
            "• STRICTLY FORBIDDEN to travel to this city — immediate health danger\n"
            "• If you are en route, turn back or bypass the area\n"
            "• If you are already there, leave the city as soon as possible via the shortest route\n"
            "• Keep all vehicle windows closed\n"
            "• If you cannot leave, take shelter in a closed building and follow resident guidelines\n"
            "• Inform your relatives of your situation and location\n"
            "• This alert is valid for an estimated 72 hours to 1 week"
        ),
        'duree': '72 heures à 1 semaine',
    },
}


def determiner_niveau(aqi):
    if aqi >= 201:
        return 'critique'
    elif aqi >= 151:
        return 'grave'
    elif aqi >= 101:
        return 'modere'
    return None


def generer_alertes_automatiques():
    """
    Analyse les dernières données AQI de chaque ville.
    Crée des alertes brouillon si les seuils sont dépassés.
    Retourne le nombre d'alertes créées.
    """
    aujourd_hui = timezone.now().date()
    alerts_to_create = []

    from django.db.models import Max, Subquery, OuterRef

    # Get the actual AQI records for the latest date per city
    latest_aqis = QualiteAir.objects.filter(
        est_prediction=False,
        date_cible=Subquery(
            QualiteAir.objects.filter(
                ville=OuterRef('ville'),
                est_prediction=False,
            ).order_by('-date_cible').values('date_cible')[:1]
        ),
    ).select_related('ville')

    # Get cities that already have active alerts today
    villes_with_alerts = set(
        Alerte.objects.filter(
            statut__in=['brouillon', 'publiee'],
            est_active=True,
            date_creation__date__gte=aujourd_hui,
        ).values_list('ville_id', flat=True)
    )

    for dernier_aqi in latest_aqis:
        ville = dernier_aqi.ville

        niveau = determiner_niveau(dernier_aqi.indice_aqi)
        if not niveau:
            continue

        if ville.id in villes_with_alerts:
            continue

        reco = RECOMMANDATIONS[niveau]

        alerts_to_create.append(Alerte(
            ville=ville,
            niveau_severite=niveau,
            statut='brouillon',
            source='ml',
            message_fr=f"Alerte automatique : l'indice AQI à {ville.nom} a atteint {dernier_aqi.indice_aqi} ({dernier_aqi.categorie}). Qualité de l'air {niveau}.",
            message_en=f"Automatic alert: AQI index in {ville.nom} reached {dernier_aqi.indice_aqi} ({dernier_aqi.categorie}). Air quality {niveau}.",
            recommandations_residents_fr=reco['residents_fr'],
            recommandations_residents_en=reco['residents_en'],
            recommandations_visiteurs_fr=reco['visiteurs_fr'],
            recommandations_visiteurs_en=reco['visiteurs_en'],
            duree_estimee=reco['duree'],
            donnees_declencheur={
                'aqi': dernier_aqi.indice_aqi,
                'pm25': dernier_aqi.valeur_pm25,
                'categorie': dernier_aqi.categorie,
                'date': str(dernier_aqi.date_cible),
            },
        ))

    if alerts_to_create:
        Alerte.objects.bulk_create(alerts_to_create)

    return len(alerts_to_create)
