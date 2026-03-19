from rest_framework import viewsets
from .models import Alerte
from .serializers import AlerteSerializer

class AlerteViewSet(viewsets.ModelViewSet):
    queryset = Alerte.objects.all().order_by('-date_creation')
    serializer_class = AlerteSerializer