import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from locations.models import Ville
from alerts.models import Alerte


MESSAGES = {
    "critique": {
        "fr": "Qualité de l'air dangereuse. Restez à l'intérieur et évitez toute activité physique extérieure.",
        "en": "Dangerous air quality. Stay indoors and avoid all outdoor physical activity.",
    },
    "grave": {
        "fr": "Qualité de l'air malsaine. Limitez les sorties prolongées, surtout pour les personnes sensibles.",
        "en": "Unhealthy air quality. Limit prolonged outdoor exposure, especially for sensitive groups.",
    },
    "modere": {
        "fr": "Qualité de l'air modérée. Les personnes asthmatiques doivent rester vigilantes.",
        "en": "Moderate air quality. People with asthma should remain vigilant.",
    },
}


class Command(BaseCommand):
    help = "Crée des alertes de démonstration"

    def handle(self, *args, **options):
        villes = list(Ville.objects.all())
        if not villes:
            self.stderr.write(self.style.ERROR("Aucune ville. Lancez seed_locations d'abord."))
            return

        now = timezone.now()
        created = 0

        # 5 alertes actives récentes
        for i in range(5):
            ville = random.choice(villes)
            niveau = random.choice(["critique", "grave", "modere"])
            Alerte.objects.create(
                ville=ville,
                niveau_severite=niveau,
                message_fr=MESSAGES[niveau]["fr"],
                message_en=MESSAGES[niveau]["en"],
                est_active=True,
            )
            created += 1

        # 15 alertes historiques (résolues)
        for i in range(15):
            ville = random.choice(villes)
            niveau = random.choice(["critique", "grave", "modere"])
            alerte = Alerte.objects.create(
                ville=ville,
                niveau_severite=niveau,
                message_fr=MESSAGES[niveau]["fr"],
                message_en=MESSAGES[niveau]["en"],
                est_active=False,
            )
            # Backdate
            alerte.date_creation = now - timedelta(days=random.randint(1, 30))
            alerte.save(update_fields=["date_creation"])
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Terminé : {created} alertes créées (5 actives, 15 résolues)."))
