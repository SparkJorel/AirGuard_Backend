from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .auto_alerts import generer_alertes_automatiques


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def scan_alerts(request):
    if getattr(request.user, 'role', '') != 'admin':
        return Response({"error": "Acces reserve aux administrateurs."}, status=403)

    try:
        count, villes = generer_alertes_automatiques()
    except Exception as e:
        return Response({
            "success": False,
            "error": f"Erreur lors de l'analyse : {str(e)}"
        }, status=500)

    if count == 0:
        return Response({
            "success": True,
            "alertes_generees": 0,
            "villes": [],
            "message": "Aucune ville en danger actuellement. La qualite de l'air est acceptable partout."
        })

    return Response({
        "success": True,
        "alertes_generees": count,
        "villes": villes,
        "message": f"{count} alerte(s) creee(s) pour : {', '.join(villes)}."
    })
