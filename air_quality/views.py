from rest_framework import viewsets
from .models import QualiteAir
from .serializers import QualiteAirSerializer

class QualiteAirViewSet(viewsets.ModelViewSet):
    queryset = QualiteAir.objects.all().order_by('-date_cible')
    serializer_class = QualiteAirSerializer