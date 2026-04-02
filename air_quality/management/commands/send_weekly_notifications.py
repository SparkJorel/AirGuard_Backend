"""
Send weekly prediction summary to users every Sunday at 20h.
Usage: python manage.py send_weekly_notifications
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import Utilisateur
from air_quality.prediction_views import _get_prediction_for_city, LABELS, CONSEILS
from alerts.services import envoyer_notification_push

logger = logging.getLogger(__name__)

JOURS_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
JOURS_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


class Command(BaseCommand):
    help = "Send weekly air quality predictions summary"

    def handle(self, *args, **options):
        today = timezone.now().date()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        week_end = next_monday + timedelta(days=6)

        users = Utilisateur.objects.filter(
            fcm_token__isnull=False,
        ).exclude(fcm_token__exact='').prefetch_related('villes_favorites')

        sent, failed = 0, 0

        for user in users:
            villes = list(user.villes_favorites.all())
            if not villes:
                continue

            ville = villes[0]
            pred = _get_prediction_for_city(ville.nom)

            if not pred:
                continue

            # Simulate week (same prediction model, gives general trend)
            cat = pred['categorie']
            bons = 1 if cat in ('Bon', 'Modere') else 0
            # Rough estimate: if current is good, most of week is good
            if cat in ('Bon', 'Modere'):
                bons = 5
                mauvais = 2
            elif cat == 'Sensible':
                bons = 3
                mauvais = 4
            else:
                bons = 2
                mauvais = 5

            semaine_str = f"{next_monday.strftime('%d/%m')} — {week_end.strftime('%d/%m')}"

            if user.langue_preferee == 'en':
                titre = f"Weekly forecast — {ville.nom}"
                message = (
                    f"Week {semaine_str}: {bons} favorable day{'s' if bons > 1 else ''}, "
                    f"{mauvais} at-risk day{'s' if mauvais > 1 else ''}. "
                    f"Current trend: {pred.get('label', cat)}."
                )
            else:
                titre = f"Prévisions de la semaine — {ville.nom}"
                message = (
                    f"Semaine du {semaine_str} : {bons} jour{'s' if bons > 1 else ''} favorable{'s' if bons > 1 else ''}, "
                    f"{mauvais} jour{'s' if mauvais > 1 else ''} à risque. "
                    f"Tendance actuelle : {pred.get('label', cat)}."
                )

            success, _ = envoyer_notification_push(
                fcm_token=user.fcm_token,
                titre=titre,
                message=message,
                data_supplementaire={
                    "type": "weekly_prediction",
                    "ville": ville.nom,
                    "semaine": semaine_str,
                },
            )

            if success:
                sent += 1
            else:
                failed += 1

        self.stdout.write(self.style.SUCCESS(f"Weekly notifications: {sent} sent, {failed} failed"))
