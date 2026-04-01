import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import os

logger = logging.getLogger(__name__)


def initialiser_firebase():
    if not firebase_admin._apps:
        path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', '')
        if path and os.path.exists(path):
            cred = credentials.Certificate(path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialisé avec succès")
        else:
            logger.warning("Firebase non configuré : fichier credentials introuvable à '%s'", path)


def envoyer_notification_push(fcm_token, titre, message, data_supplementaire=None):
    initialiser_firebase()

    if not firebase_admin._apps:
        logger.warning("Notification ignorée (Firebase non configuré) → %s", titre)
        return False, "Firebase non configuré"

    try:
        message_push = messaging.Message(
            notification=messaging.Notification(
                title=titre,
                body=message,
            ),
            data=data_supplementaire if data_supplementaire else {},
            token=fcm_token,
        )

        response = messaging.send(message_push)
        logger.info("Notification envoyée → token=%s...%s titre='%s'", fcm_token[:8], fcm_token[-4:], titre)
        return True, response

    except messaging.UnregisteredError:
        logger.warning("Token FCM invalide/expiré : %s...%s", fcm_token[:8], fcm_token[-4:])
        return False, "Token expiré"

    except Exception as e:
        logger.error("Erreur notification push → %s: %s", type(e).__name__, str(e))
        return False, str(e)
