from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class Utilisateur(AbstractUser):
    ROLE_CHOICES =[
        ('citoyen', 'Citoyen'),
        ('admin', 'Administrateur'),
        ('chercheur', 'Chercheur/Scientifique'),
    ]
    
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citoyen')
    fcm_token = models.CharField(max_length=255, blank=True, null=True, help_text="Token Firebase")
    langue_preferee = models.CharField(max_length=2, choices=[('fr', 'Français'), ('en', 'English')], default='fr')
    
    villes_favorites = models.ManyToManyField('locations.Ville', blank=True, related_name="suivie_par")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} - {self.role}"