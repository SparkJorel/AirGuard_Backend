from rest_framework import serializers
from .models import Utilisateur


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'langue_preferee', 'villes_favorites', 'fcm_token']
        extra_kwargs = {
            'fcm_token': {'required': False},
        }


class FCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(max_length=255)
