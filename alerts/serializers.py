from rest_framework import serializers
from .models import Alerte


class AlerteSerializer(serializers.ModelSerializer):
    ville_nom = serializers.CharField(source='ville.nom', read_only=True)
    ville_region = serializers.CharField(source='ville.region.nom', read_only=True)

    class Meta:
        model = Alerte
        fields = '__all__'
