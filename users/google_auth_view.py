import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Utilisateur

logger = logging.getLogger(__name__)

# Web client ID — must match the one used in the mobile app
WEB_CLIENT_ID = "81645766104-9tp9o0q30t2s948jv89kpitdc0r1jobs.apps.googleusercontent.com"


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """
    Authenticate with Google Sign-In.
    Receives a Google ID token from Credential Manager, verifies it,
    creates/finds the user, returns JWT tokens.
    """
    token = request.data.get('id_token')
    if not token:
        return Response({"error": "Le champ 'id_token' est requis."}, status=400)

    try:
        # Verify the Google OAuth2 ID token
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            WEB_CLIENT_ID,
        )

        email = idinfo.get('email')
        if not email:
            return Response({"error": "Le token ne contient pas d'email."}, status=400)

        if not idinfo.get('email_verified', False):
            return Response({"error": "L'email n'est pas vérifié."}, status=400)

        # Get or create user
        created = False
        try:
            user = Utilisateur.objects.get(email=email)
        except Utilisateur.DoesNotExist:
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while Utilisateur.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = Utilisateur.objects.create_user(
                username=username,
                email=email,
                first_name=idinfo.get('given_name', ''),
                last_name=idinfo.get('family_name', ''),
            )
            user.set_unusable_password()
            user.save()
            created = True
            logger.info("Nouvel utilisateur créé via Google : %s", email)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        has_city = user.villes_favorites.exists()

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "created": created,
            "has_city": has_city,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        })

    except ValueError as e:
        logger.warning("Token Google invalide : %s", str(e))
        return Response({"error": f"Token Google invalide: {str(e)}"}, status=401)
    except Exception as e:
        logger.error("Erreur auth Google : %s: %s", type(e).__name__, str(e))
        return Response({"error": f"Erreur d'authentification: {str(e)}"}, status=500)
