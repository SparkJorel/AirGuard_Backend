from rest_framework import viewsets
from .models import ReleveMeteo
from .serializers import ReleveMeteoSerializer

class ReleveMeteoViewSet(viewsets.ModelViewSet):
    queryset = ReleveMeteo.objects.all().order_by('-date')
    serializer_class = ReleveMeteoSerializer