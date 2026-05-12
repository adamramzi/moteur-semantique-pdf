"""
email_service.py — Service d'envoi d'e-mails de vérification
Moteur Sémantique PDF

Utilise l'API transactionnelle Brevo (ex-Sendinblue).
Credentials lus depuis les variables d'environnement :
    BREVO_API_KEY  → Clé API Brevo (Settings > API Keys)
    EMAIL_SENDER   → Adresse e-mail expéditrice vérifiée dans Brevo
"""

import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def envoyer_code_verification(email_destinataire: str, code: str):
    """
    Envoie un e-mail HTML de vérification avec le code à 6 chiffres via l'API Brevo.

    Args:
        email_destinataire: L'adresse e-mail du destinataire.
        code:               Le code de vérification à 6 chiffres.

    Returns:
        Tuple (bool, str) :
            - (True,  "Email envoyé")       en cas de succès (status 201)
            - (False, "message d'erreur")   en cas d'échec
    """
    api_key      = os.getenv("BREVO_API_KEY")
    email_sender = os.getenv("EMAIL_SENDER")

    if not api_key or not email_sender:
        return False, (
            "Variables BREVO_API_KEY et/ou EMAIL_SENDER manquantes. "
            "Configurez-les dans le fichier .env."
        )

    html_content = (
        "<div style='font-family:Arial;text-align:center;padding:30px;"
        "background:#1a1a2e;color:white;border-radius:15px'>"
        "<h2 style='color:#a78bfa'>Moteur Sémantique PDF</h2>"
        "<p>Votre code de vérification est :</p>"
        f"<h1 style='color:#34d399;font-size:50px;letter-spacing:10px'>{code}</h1>"
        "<p style='color:#94a3b8'>Ce code expire dans 10 minutes.</p>"
        "</div>"
    )

    payload = {
        "sender": {"name": "Moteur PDF", "email": email_sender},
        "to": [{"email": email_destinataire}],
        "subject": "Code de vérification - Moteur PDF",
        "htmlContent": html_content,
    }

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=15,
        )

        if response.status_code == 201:
            return True, "Email envoyé"
        else:
            return False, str(response.text)

    except Exception as e:
        return False, str(e)
