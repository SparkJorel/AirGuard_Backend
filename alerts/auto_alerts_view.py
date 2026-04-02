from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .auto_alerts import generer_alertes_automatiques


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def scan_alerts(request):
    """Déclenche le scan ML pour générer des alertes automatiques (admin only)."""
    if getattr(request.user, 'role', '') != 'admin':
        return Response({"error": "Accès réservé aux administrateurs."}, status=403)

    try:
        count = generer_alertes_automatiques()
    except Exception as e:
        return Response({
            "success": False,
            "error": f"Erreur lors du scan ML : {str(e)}"
        }, status=500)

    return Response({
        "success": True,
        "alertes_generees": count,
        "message": f"{count} nouvelle(s) alerte(s) détectée(s) par le modèle ML."
    })
