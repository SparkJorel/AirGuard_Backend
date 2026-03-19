from django.db import models

class ReleveMeteo(models.Model):
    ville = models.ForeignKey('locations.Ville', on_delete=models.CASCADE, related_name="releves_meteo")
    date = models.DateField()

    # Températures
    temperature_2m_max = models.FloatField(null=True, blank=True)
    temperature_2m_min = models.FloatField(null=True, blank=True)
    temperature_2m_mean = models.FloatField(null=True, blank=True)
    apparent_temperature_max = models.FloatField(null=True, blank=True)
    apparent_temperature_min = models.FloatField(null=True, blank=True)
    apparent_temperature_mean = models.FloatField(null=True, blank=True)

    # Précipitations et Humidité
    weather_code = models.IntegerField(null=True, blank=True)
    precipitation_sum = models.FloatField(null=True, blank=True)
    rain_sum = models.FloatField(null=True, blank=True)
    snowfall_sum = models.FloatField(null=True, blank=True, default=0.0)
    precipitation_hours = models.FloatField(null=True, blank=True)

    # Vent
    wind_speed_10m_max = models.FloatField(null=True, blank=True)
    wind_gusts_10m_max = models.FloatField(null=True, blank=True)
    wind_direction_10m_dominant = models.FloatField(null=True, blank=True)

    # Ensoleillement
    daylight_duration = models.FloatField(null=True, blank=True)
    sunshine_duration = models.FloatField(null=True, blank=True)
    shortwave_radiation_sum = models.FloatField(null=True, blank=True)

    # Agricole/Hydrique
    et0_fao_evapotranspiration = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('ville', 'date')

    def __str__(self):
        return f"Météo {self.ville.nom} - {self.date}"