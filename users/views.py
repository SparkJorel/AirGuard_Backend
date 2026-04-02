from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Utilisateur
from .serializers import UtilisateurSerializer, FCMTokenSerializer


class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """Get or update current user's profile."""
        user = request.user
        if request.method == 'PATCH':
            for field in ['first_name', 'last_name', 'langue_preferee']:
                if field in request.data:
                    setattr(user, field, request.data[field])
            if 'villes_favorites' in request.data:
                from locations.models import Ville
                villes = Ville.objects.filter(id__in=request.data['villes_favorites'])
                user.villes_favorites.set(villes)
            user.save()

        villes_fav = list(user.villes_favorites.values_list('nom', flat=True))
        return Response({
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "langue_preferee": user.langue_preferee,
            "villes_favorites": villes_fav,
        })

    @action(detail=False, methods=['post'], url_path='register-fcm-token')
    def register_fcm_token(self, request):
        """Enregistre ou met à jour le token FCM de l'utilisateur connecté."""
        serializer = FCMTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.fcm_token = serializer.validated_data['fcm_token']
        request.user.save(update_fields=['fcm_token'])
        return Response({"success": True, "message": "Token FCM enregistré."})
