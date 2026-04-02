"""
Fetch recent weather data from Open-Meteo API for all cities.
Only fetches data up to today (no future forecasts).
Run daily via cron to keep data up to date.

Usage:
  python manage.py fetch_meteo          # last 30 days up to today
  python manage.py fetch_meteo --days 7 # last 7 days up to today
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from locations.models import Ville
from meteo.open_meteo import fetch_meteo_for_city


class Command(BaseCommand):
    help = "Fetch weather data from Open-Meteo API"

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Number of past days to fetch')

    def handle(self, *args, **options):
        today = date.today()
        start = today - timedelta(days=options['days'])
        end = today

        villes = Ville.objects.all()
        total = 0
        errors = 0

        self.stdout.write(f"Fetching meteo data: {start} to {end} for {villes.count()} cities")

        for ville in villes:
            try:
                count = fetch_meteo_for_city(ville, start, end)
                total += count
                self.stdout.write(f"  {ville.nom}: {count} records")
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.WARNING(f"  {ville.nom}: ERROR - {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done: {total} records fetched, {errors} errors"))
