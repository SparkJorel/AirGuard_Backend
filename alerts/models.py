from django.db import models

class Alerte(models.Model):
    NIVEAU_CHOICES =[
        ('modere', 'Modéré'),
        ('grave', 'Grave'),
        ('critique', 'Critique'),
    ]

    ville = models.ForeignKey('locations.Ville', on_delete=models.CASCADE, related_name="alertes")
    date_creation = models.DateTimeField(auto_now_add=True)
    niveau_severite = models.CharField(max_length=20, choices=NIVEAU_CHOICES)
    
    message_fr = models.TextField()
    message_en = models.TextField()
    
    est_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Alerte {self.niveau_severite} - {self.ville.nom} ({self.date_creation.strftime('%Y-%m-%d')})"