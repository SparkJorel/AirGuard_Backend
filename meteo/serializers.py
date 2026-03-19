from rest_framework import serializers
from .models import ReleveMeteo

class ReleveMeteoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleveMeteo
        fields = '__all__'