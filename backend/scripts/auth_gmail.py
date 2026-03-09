"""
Lance ce script UNE SEULE FOIS pour autoriser l'accès Gmail.
Il va ouvrir ton navigateur pour que tu te connectes à Google.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.email_service import get_gmail_service

if __name__ == "__main__":
    print("Connexion à Gmail...")
    service = get_gmail_service()
    profile = service.users().getProfile(userId="me").execute()
    print(f"Connecté en tant que : {profile.get('emailAddress')}")
    print(f"Total messages : {profile.get('messagesTotal')}")
    print("Token sauvegardé — l'agent peut maintenant accéder à Gmail.")