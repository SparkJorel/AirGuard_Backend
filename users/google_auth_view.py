import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Utilisateur

logger = logging.getLogger(__name__)

# Web client ID from Firebase/Google Console — also accepts Android client IDs automatically
GOOGLE_CLIENT_IDS = [
    # Add your Google OAuth client IDs here
    # The verify_oauth2_token function will accept tokens from any of these
]


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """
    Authenticate with Google Sign-In.
    Receives a Google ID token, verifies it, creates/finds the user, returns JWT tokens.

    Request body: { "id_token": "eyJhbGciOi..." }
    Response: { "access": "...", "refresh": "...", "created": true/false }
    """
    token = request.data.get('id_token')
    if not token:
        return Response({"error": "Le champ 'id_token' est requis."}, status=400)

    try:
        # Verify the Google ID token
        # Using verify_firebase_token because Firebase Auth is already configured.
        # This verifies tokens issued by Firebase Auth (which includes Google Sign-In
        # through Firebase). If the mobile app uses Firebase Auth with Google provider,
        # this is the correct verification method.
        idinfo = id_token.verify_firebase_token(token, google_requests.Request())

        # If using regular Google Sign-In (not Firebase), use:
        # idinfo = id_token.verify_oauth2_token(token, google_requests.Request())

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
            # Generate unique username to avoid collisions
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
            # Set unusable password since they use Google auth
            user.set_unusable_password()
            user.save()
            created = True
            logger.info("Nouvel utilisateur créé via Google : %s", email)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "created": created,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
            }
        })

    except ValueError as e:
        logger.warning("Token Google invalide : %s", str(e))
        return Response({"error": "Token Google invalide."}, status=401)
    except Exception as e:
        logger.error("Erreur auth Google : %s", str(e))
        return Response({"error": "Erreur d'authentification."}, status=500)
