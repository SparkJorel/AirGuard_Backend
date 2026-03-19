from django.db import models

class Region(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nom

class Ville(models.Model):
    nom = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="villes")
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"{self.nom} ({self.region.nom})"