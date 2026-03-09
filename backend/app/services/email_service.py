import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import settings
import structlog

logger = structlog.get_logger()

# Scopes minimaux nécessaires
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_gmail_service():
    """Retourne un service Gmail authentifié via OAuth2"""
    creds = None
    
    # Chemin absolu basé sur l'emplacement du fichier email_service.py
    base_dir = Path(__file__).parent.parent.parent  # remonte jusqu'à backend/
    token_file = base_dir / settings.GMAIL_TOKEN_FILE
    creds_file = base_dir / settings.GMAIL_CREDENTIALS_FILE

    logger.info("Cherche credentials", path=str(creds_file), exists=creds_file.exists())

    # Charge le token existant si disponible
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_file.exists():
                raise FileNotFoundError(
                    f"Fichier {creds_file} introuvable."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_file), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def build_email(
    to: str,
    subject: str,
    body: str,
    sender: str = None,
) -> dict:
    """Construit un email au format Gmail API"""
    if sender is None:
        sender = settings.GMAIL_SENDER_EMAIL

    message = MIMEMultipart("alternative")
    message["To"] = to
    message["From"] = sender
    message["Subject"] = subject

    # Corps en texte plain
    part = MIMEText(body, "plain", "utf-8")
    message.attach(part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_email(
    to: str,
    subject: str,
    body: str,
) -> dict:
    """Envoie un email via Gmail API"""
    try:
        service = get_gmail_service()
        message = build_email(to, subject, body)

        sent = service.users().messages().send(
            userId="me",
            body=message
        ).execute()

        logger.info(
            "Email envoyé",
            to=to,
            subject=subject,
            message_id=sent.get("id"),
        )
        return {
            "success": True,
            "message_id": sent.get("id"),
            "thread_id": sent.get("threadId"),
        }

    except HttpError as e:
        logger.error("Erreur envoi Gmail", error=str(e), to=to)
        return {"success": False, "error": str(e)}


def create_draft(
    to: str,
    subject: str,
    body: str,
) -> dict:
    """Crée un brouillon dans Gmail (sans envoyer)"""
    try:
        service = get_gmail_service()
        message = build_email(to, subject, body)

        draft = service.users().drafts().create(
            userId="me",
            body={"message": message}
        ).execute()

        logger.info(
            "Brouillon créé",
            to=to,
            subject=subject,
            draft_id=draft.get("id"),
        )
        return {
            "success": True,
            "draft_id": draft.get("id"),
            "message_id": draft.get("message", {}).get("id"),
        }

    except HttpError as e:
        logger.error("Erreur création brouillon", error=str(e))
        return {"success": False, "error": str(e)}


def get_recent_emails(max_results: int = 50) -> list[dict]:
    """Récupère les emails récents de la boîte"""
    try:
        service = get_gmail_service()

        results = service.users().messages().list(
            userId="me",
            maxResults=max_results,
            labelIds=["INBOX"],
        ).execute()

        messages = results.get("messages", [])
        emails = []

        for msg in messages:
            detail = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()

            headers = {
                h["name"]: h["value"]
                for h in detail.get("payload", {}).get("headers", [])
            }

            emails.append({
                "id": msg["id"],
                "thread_id": detail.get("threadId"),
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": detail.get("snippet", ""),
            })

        return emails

    except HttpError as e:
        logger.error("Erreur lecture Gmail", error=str(e))
        return []


def get_email_body(message_id: str) -> str:
    """Récupère le corps complet d'un email"""
    try:
        service = get_gmail_service()
        message = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()

        payload = message.get("payload", {})

        # Email simple
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8")

        # Email multipart
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")

        return ""

    except HttpError as e:
        logger.error("Erreur lecture corps email", error=str(e))
        return ""