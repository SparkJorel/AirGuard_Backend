from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Utilisateur
from locations.models import Ville


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Inscription d'un nouvel utilisateur.

    Body: {
        "email": "user@example.com",
        "password": "motdepasse",
        "first_name": "Jean",
        "last_name": "Dupont",
        "langue_preferee": "fr",
        "villes_favorites": [1, 5, 12]  // IDs des villes (optionnel)
    }
    """
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    langue = request.data.get('langue_preferee', 'fr')
    villes_ids = request.data.get('villes_favorites', [])

    if not email or not password:
        return Response({"error": "Email et mot de passe requis."}, status=400)

    if len(password) < 6:
        return Response({"error": "Le mot de passe doit contenir au moins 6 caractères."}, status=400)

    if Utilisateur.objects.filter(email=email).exists():
        return Response({"error": "Un compte avec cet email existe déjà."}, status=409)

    # Generate unique username from email
    base_username = email.split('@')[0]
    username = base_username
    counter = 1
    while Utilisateur.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    user = Utilisateur.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        langue_preferee=langue,
    )

    # Add favorite cities
    if villes_ids:
        villes = Ville.objects.filter(id__in=villes_ids)
        user.villes_favorites.set(villes)

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "langue_preferee": user.langue_preferee,
        }
    }, status=201)
