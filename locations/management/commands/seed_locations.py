from django.core.management.base import BaseCommand
from locations.models import Region, Ville


REGIONS_ET_VILLES = {
    "Adamaoua": [
        ("Meiganga", 6.52, 14.29),
        ("Ngaoundere", 7.32, 13.58),
        ("Tibati", 6.46, 12.62),
        ("Tignere", 7.37, 12.65),
    ],
    "Centre": [
        ("Akonolinga", 3.77, 12.25),
        ("Bafia", 4.75, 11.23),
        ("Mbalmayo", 3.51, 11.50),
        ("Yaounde", 3.85, 11.52),
    ],
    "Est": [
        ("Abong-Mbang", 3.98, 13.17),
        ("Batouri", 4.43, 14.36),
        ("Bertoua", 4.57, 13.68),
        ("Yokadouma", 3.51, 15.05),
    ],
    "Extreme-Nord": [
        ("Kousseri", 12.08, 15.03),
        ("Maroua", 10.59, 14.32),
        ("Mokolo", 10.74, 13.80),
        ("Yagoua", 10.34, 15.23),
    ],
    "Littoral": [
        ("Douala", 4.05, 9.77),
        ("Edea", 3.80, 10.13),
        ("Loum", 4.71, 9.73),
        ("Nkongsamba", 4.95, 9.93),
    ],
    "Nord": [
        ("Garoua", 9.30, 13.40),
        ("Guider", 9.93, 13.94),
        ("Poli", 8.47, 13.24),
        ("Touboro", 7.76, 15.36),
    ],
    "Nord-Ouest": [
        ("Bamenda", 5.96, 10.15),
        ("Kumbo", 6.20, 10.66),
        ("Mbengwi", 5.99, 10.00),
        ("Wum", 6.38, 10.07),
    ],
    "Ouest": [
        ("Bafoussam", 5.48, 10.42),
        ("Dschang", 5.44, 10.05),
        ("Foumban", 5.72, 10.90),
        ("Mbouda", 5.62, 10.25),
    ],
    "Sud": [
        ("Ambam", 2.38, 11.28),
        ("Ebolowa", 2.91, 11.15),
        ("Kribi", 2.95, 9.91),
        ("Sangmelima", 2.93, 11.98),
    ],
    "Sud-Ouest": [
        ("Buea", 4.15, 9.24),
        ("Kumba", 4.63, 9.44),
        ("Limbe", 4.01, 9.21),
        ("Mamfe", 5.75, 9.31),
    ],
}


class Command(BaseCommand):
    help = "Peuple la base avec les 10 régions et 40 villes du Cameroun"

    def handle(self, *args, **options):
        total_villes = 0
        for region_nom, villes in REGIONS_ET_VILLES.items():
            region, created = Region.objects.get_or_create(nom=region_nom)
            status = "créée" if created else "existante"
            self.stdout.write(f"  Région: {region_nom} ({status})")

            for ville_nom, lat, lon in villes:
                _, v_created = Ville.objects.get_or_create(
                    nom=ville_nom,
                    region=region,
                    defaults={"latitude": lat, "longitude": lon},
                )
                if v_created:
                    total_villes += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé : 10 régions, {total_villes} nouvelles villes ajoutées."
        ))
