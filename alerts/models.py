from django.db import models


class Alerte(models.Model):
    NIVEAU_CHOICES = [
        ('modere', 'Modéré'),
        ('grave', 'Grave'),
        ('critique', 'Critique'),
    ]

    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('publiee', 'Publiée'),
        ('ignoree', 'Ignorée'),
    ]

    SOURCE_CHOICES = [
        ('ml', 'Modèle ML'),
        ('admin', 'Administrateur'),
    ]

    ville = models.ForeignKey('locations.Ville', on_delete=models.CASCADE, related_name="alertes")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_publication = models.DateTimeField(null=True, blank=True)
    niveau_severite = models.CharField(max_length=20, choices=NIVEAU_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='admin')

    message_fr = models.TextField()
    message_en = models.TextField()

    # Recommandations pour les résidents de la ville
    recommandations_residents_fr = models.TextField(blank=True, default='')
    recommandations_residents_en = models.TextField(blank=True, default='')

    # Recommandations pour les visiteurs / personnes hors ville
    recommandations_visiteurs_fr = models.TextField(blank=True, default='')
    recommandations_visiteurs_en = models.TextField(blank=True, default='')

    # Durée estimée de l'alerte
    duree_estimee = models.CharField(max_length=100, blank=True, default='')

    # Données ML ayant déclenché l'alerte
    donnees_declencheur = models.JSONField(null=True, blank=True)

    est_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"Alerte {self.niveau_severite} [{self.statut}] - {self.ville.nom}"
