from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Alerte
from .serializers import AlerteSerializer
from .services import envoyer_notification_push
from users.models import Utilisateur


class AlerteViewSet(viewsets.ModelViewSet):
    queryset = Alerte.objects.all()
    serializer_class = AlerteSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Alerte.objects.all()
        # Non-admin users only see published alerts
        if not self.request.user.is_authenticated or getattr(self.request.user, 'role', '') != 'admin':
            qs = qs.filter(statut='publiee')
        return qs

    @action(detail=False, methods=['get'], url_path='active')
    def get_active_alerts(self, request):
        alertes = Alerte.objects.filter(est_active=True, statut='publiee')
        serializer = self.get_serializer(alertes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='brouillons')
    def get_draft_alerts(self, request):
        """Alertes ML en attente de validation (admin only)."""
        if not request.user.is_authenticated or getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Accès réservé aux administrateurs."}, status=403)
        alertes = Alerte.objects.filter(statut='brouillon')
        serializer = self.get_serializer(alertes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='publier')
    def publier(self, request, pk=None):
        """Admin publie une alerte brouillon → visible par tous + notifications."""
        if not request.user.is_authenticated or getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Accès réservé aux administrateurs."}, status=403)

        alerte = self.get_object()
        if alerte.statut == 'publiee':
            return Response({"error": "Cette alerte est déjà publiée."}, status=400)

        # Allow admin to modify before publishing
        for field in ['message_fr', 'message_en', 'niveau_severite',
                      'recommandations_residents_fr', 'recommandations_residents_en',
                      'recommandations_visiteurs_fr', 'recommandations_visiteurs_en',
                      'duree_estimee']:
            if field in request.data:
                setattr(alerte, field, request.data[field])

        alerte.statut = 'publiee'
        alerte.date_publication = timezone.now()
        alerte.est_active = True
        alerte.save()

        # Send push notifications
        self._notify_users(alerte)

        return Response(AlerteSerializer(alerte).data)

    @action(detail=True, methods=['post'], url_path='ignorer')
    def ignorer(self, request, pk=None):
        """Admin ignore/rejette une alerte brouillon."""
        if not request.user.is_authenticated or getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Accès réservé aux administrateurs."}, status=403)

        alerte = self.get_object()
        alerte.statut = 'ignoree'
        alerte.est_active = False
        alerte.save()
        return Response({"success": True, "message": "Alerte ignorée."})

    def perform_create(self, serializer):
        alerte = serializer.save()
        if alerte.statut == 'publiee' and alerte.est_active:
            self._notify_users(alerte)

    def _notify_users(self, alerte):
        ville = alerte.ville
        utilisateurs = Utilisateur.objects.filter(
            villes_favorites=ville
        ).exclude(fcm_token__isnull=True).exclude(fcm_token__exact='')

        titre = f"Alerte AirGuard : {ville.nom}"

        for user in utilisateurs:
            # Residents get resident recommendations, others get visitor ones
            is_resident = user.villes_favorites.filter(id=ville.id).exists()
            if user.langue_preferee == 'en':
                message = alerte.recommandations_residents_en if is_resident else alerte.recommandations_visiteurs_en
            else:
                message = alerte.recommandations_residents_fr if is_resident else alerte.recommandations_visiteurs_fr

            if not message:
                message = alerte.message_fr if user.langue_preferee == 'fr' else alerte.message_en

            envoyer_notification_push(
                fcm_token=user.fcm_token,
                titre=titre,
                message=message,
                data_supplementaire={
                    "ville_id": str(ville.id),
                    "severite": alerte.niveau_severite,
                    "type": "resident" if is_resident else "visiteur",
                }
            )
