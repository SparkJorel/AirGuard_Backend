from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from locations.views import RegionViewSet, VilleViewSet
from meteo.views import ReleveMeteoViewSet
from air_quality.views import QualiteAirViewSet
from alerts.views import AlerteViewSet
from users.views import UtilisateurViewSet
from air_quality.import_views import import_dataset
from alerts.auto_alerts_view import scan_alerts

router = DefaultRouter()
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'villes', VilleViewSet, basename='ville')
router.register(r'meteo', ReleveMeteoViewSet, basename='relevemeteo')
router.register(r'air-quality', QualiteAirViewSet, basename='qualiteair')
router.register(r'alerts', AlerteViewSet, basename='alerte')
router.register(r'users', UtilisateurViewSet, basename='utilisateur')

urlpatterns =[
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    
    path('api/v1/data/import/', import_dataset, name='import_dataset'),
    path('api/v1/alerts/scan/', scan_alerts, name='scan_alerts'),
    path('api/v1/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]