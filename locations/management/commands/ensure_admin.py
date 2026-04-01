from django.core.management.base import BaseCommand
from users.models import Utilisateur


class Command(BaseCommand):
    help = "Crée le superuser admin s'il n'existe pas"

    def handle(self, *args, **options):
        if Utilisateur.objects.filter(email='admin@airguard.cm').exists():
            self.stdout.write("Admin existe déjà.")
            return

        Utilisateur.objects.create_superuser(
            username='admin',
            email='admin@airguard.cm',
            password='12345678',
            role='admin',
        )
        self.stdout.write(self.style.SUCCESS("Superuser admin@airguard.cm créé."))
