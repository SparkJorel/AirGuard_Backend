from rest_framework import serializers
from .models import QualiteAir

class QualiteAirSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualiteAir
        fields = '__all__'