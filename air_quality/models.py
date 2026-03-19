from django.db import models

class QualiteAir(models.Model):
    CATEGORIE_CHOICES =[
        ('Bon', 'Bon (0-50)'),
        ('Modere', 'Modéré (51-100)'),
        ('Sensible', 'Sensible (101-150)'),
        ('Malsain', 'Malsain (151-200)'),
        ('Tres_malsain', 'Très malsain (201-300)'),
        ('Dangereux', 'Dangereux (300+)'),
    ]

    ville = models.ForeignKey('locations.Ville', on_delete=models.CASCADE, related_name="qualite_air")
    date_cible = models.DateField()
    
    valeur_pm25 = models.FloatField()
    indice_aqi = models.IntegerField()
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)
    
    est_prediction = models.BooleanField(default=False)
    facteurs_aggravants = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('ville', 'date_cible', 'est_prediction')

    def __str__(self):
        type_donnee = "Prédiction" if self.est_prediction else "Réel"
        return f"AQI {self.ville.nom} ({self.date_cible}) - {self.indice_aqi} [{type_donnee}]"