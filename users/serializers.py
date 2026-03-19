from rest_framework import serializers
from .models import Utilisateur

class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields =['id', 'email', 'first_name', 'last_name', 'role', 'langue_preferee', 'villes_favorites']