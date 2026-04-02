"""
Send daily personalized notifications to users about tomorrow's air quality.
Run every day at 20h via cron.
Usage: python manage.py send_daily_notifications
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import Utilisateur
from air_quality.prediction_views import _get_prediction_for_city
from alerts.services import envoyer_notification_push

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send daily air quality notifications for tomorrow"

    def handle(self, *args, **options):
        tomorrow = timezone.now().date() + timedelta(days=1)
        users = Utilisateur.objects.filter(
            fcm_token__isnull=False,
        ).exclude(fcm_token__exact='').prefetch_related('villes_favorites')

        sent, failed = 0, 0

        for user in users:
            villes = list(user.villes_favorites.all())
            if not villes:
                continue

            # Use first favorite city (city of residence)
            ville = villes[0]
            pred = _get_prediction_for_city(ville.nom)

            if not pred:
                continue

            titre = f"Qualité de l'air demain — {ville.nom}"

            if user.langue_preferee == 'en':
                labels_en = {
                    'Bon': 'Clean air', 'Modere': 'Acceptable air',
                    'Sensible': 'Degraded air', 'Malsain': 'Unhealthy air',
                    'Tres_malsain': 'Very unhealthy', 'Dangereux': 'Dangerous',
                }
                conseils_en = {
                    'Bon': 'Enjoy outdoor activities!',
                    'Modere': 'Sensitive people should be cautious.',
                    'Sensible': 'Limit prolonged outdoor exertion.',
                    'Malsain': 'Avoid going outside. Wear a mask if needed.',
                    'Tres_malsain': 'Stay indoors. Protect children and elderly.',
                    'Dangereux': 'DO NOT go outside. Close doors and windows.',
                }
                titre = f"Tomorrow's air quality — {ville.nom}"
                message = f"{labels_en.get(pred['categorie'], pred['categorie'])}. {conseils_en.get(pred['categorie'], '')}"
            else:
                message = f"{pred['label']}. {pred['conseil']}"

            success, _ = envoyer_notification_push(
                fcm_token=user.fcm_token,
                titre=titre,
                message=message,
                data_supplementaire={
                    "type": "daily_prediction",
                    "ville": ville.nom,
                    "aqi": str(pred['aqi']),
                    "categorie": pred['categorie'],
                    "date": str(tomorrow),
                },
            )

            if success:
                sent += 1
            else:
                failed += 1

        self.stdout.write(self.style.SUCCESS(f"Daily notifications: {sent} sent, {failed} failed"))
