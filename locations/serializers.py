from rest_framework import serializers
from .models import Region, Ville

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'

class VilleSerializer(serializers.ModelSerializer):
    # On ajoute le nom de la région en lecture seule pour que le Front-end l'affiche facilement
    region_nom = serializers.CharField(source='region.nom', read_only=True)

    class Meta:
        model = Ville
        fields = '__all__'