"""
Generate predictions for all 40 cities for tomorrow and/or the next week.
Usage:
  python manage.py generate_predictions          # tomorrow only
  python manage.py generate_predictions --week    # full week (Mon-Sun)
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from locations.models import Ville
from air_quality.models import QualiteAir
from air_quality.ml_service import predire_tous_les_indicateurs


def pm25_to_aqi_cat(pm25):
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
    help = "Generate ML predictions for all cities"

    def add_arguments(self, parser):
        parser.add_argument('--week', action='store_true', help='Generate for full week (Mon-Sun)')

    def handle(self, *args, **options):
        today = timezone.now().date()
        villes = Ville.objects.all()

        if options['week']:
            # Next Monday to Sunday
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            dates = [today + timedelta(days=days_until_monday + i) for i in range(7)]
            self.stdout.write(f"Generating week predictions: {dates[0]} to {dates[-1]}")
        else:
            dates = [today + timedelta(days=1)]
            self.stdout.write(f"Generating prediction for: {dates[0]}")

        created = 0
        errors = 0

        for ville in villes:
            result = predire_tous_les_indicateurs(ville.nom, {})
            if "error" in result:
                errors += 1
                self.stdout.write(self.style.WARNING(f"  {ville.nom}: {result['error']}"))
                continue

            pred = result.get("predictions", {}).get("qualite_air", {})
            pm25 = pred.get("pm25_proxy_ugm3", 0)
            aqi, categorie = pm25_to_aqi_cat(pm25)

            objs = []
            for date in dates:
                objs.append(QualiteAir(
                    ville=ville,
                    date_cible=date,
                    valeur_pm25=round(pm25, 2),
                    indice_aqi=aqi,
                    categorie=categorie,
                    est_prediction=True,
                ))

            QualiteAir.objects.bulk_create(objs, ignore_conflicts=True)
            created += len(objs)
            self.stdout.write(f"  {ville.nom}: {len(objs)} predictions")

        self.stdout.write(self.style.SUCCESS(f"Done: {created} predictions, {errors} errors"))
