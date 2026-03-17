# 🤖 Job Agent IA — Recherche & Suivi de candidatures

Agent automatisé pour la recherche et le suivi de candidatures à des emplois en général (CDD, CDI, stages ou alternances), adaptable à n'importe quel poste en fonction du profil utilisateur. La génération de candidatures personnalisées, le suivi CRM et les relances automatiques.

---

## 📋 Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Stack technique](#stack-technique)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Authentification Gmail](#authentification-gmail)
- [Lancement](#lancement)
- [Utilisation de l'API](#utilisation-de-lapi)
- [Structure du projet](#structure-du-projet)
- [Workflow complet](#workflow-complet)
- [Sécurité](#sécurité)
- [Roadmap](#roadmap)

---

## ✨ Fonctionnalités

### MVP (implémenté)
- ✅ **Scraping multi-plateformes** — Welcome to the Jungle, Indeed France
- ✅ **Déduplication automatique** des offres par hash SHA256
- ✅ **Scoring de pertinence 0-100** par GPT-4o-mini (matching profil/offre)
- ✅ **Génération LLM** d'emails et lettres de motivation personnalisés
- ✅ **CRM intégré** — suivi du cycle de vie complet des candidatures
- ✅ **Intégration Gmail OAuth2** — envoi d'emails et création de brouillons
- ✅ **Validation humaine** avant les actions sensibles

### En cours (Étapes 7-9)
- 🔄 **Relances automatiques** à J+7 via Celery Beat
- 🔄 **Classification LLM** des réponses reçues (refus / entretien / info)
- 🔄 **Dashboard React** de supervision

---

## 🏗️ Architecture

```
Sources d'offres (WTTJ, Indeed...)
         │
         ▼
   [Job Scraper]  ──►  [Déduplication]  ──►  [BDD: job_offers]
                                │
                                ▼
                      [Analyzer + Scorer LLM]
                      Score de pertinence 0-100
                                │
                          Score >= 60 ?
                           /         \
                         OUI          NON ──► Ignoré
                          │
                          ▼
                   [Generator LLM]
                   Email + Lettre personnalisés
                          │
                   Confiance >= 85 ?
                    /         \
                  OUI          NON ──► Brouillon + Notif
                   │
                   ▼
            [Gmail API OAuth2]
                   │
                   ▼
            [BDD: applications]
                   │
                   ▼
         [Celery Beat — J+7]
         Relance si pas de réponse
                   │
                   ▼
           [Email Monitor]
           Lecture des réponses
                   │
                   ▼
          [Response Classifier]
          refus / entretien / info
                   │
                   ▼
         [Validation Humaine]
         Dashboard de supervision
```

---

## 🛠️ Stack technique

| Composant | Technologie | Justification |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async natif, typage fort |
| LLM | GPT-4o-mini / GPT-4o | Qualité/coût optimal |
| Base de données | PostgreSQL 16 | Relationnel robuste, JSONB |
| ORM | SQLAlchemy 2.0 async | Migrations, typage Pydantic |
| Scheduler | Celery + Redis | Relances fiables avec retry |
| Email | Gmail API v1 OAuth2 | Sécurisé, scopes minimaux |
| Scraping | Playwright + BS4 | Stable sur les SPAs modernes |
| Frontend | React + TailwindCSS | Dashboard clean |
| Monitoring | structlog + Sentry | Logs structurés, alertes |
| Infra | Docker + Docker Compose | Reproducible, simple |

---

## ✅ Prérequis

### Logiciels
- Python 3.11+
- Docker Desktop
- Node.js 18+ (pour le frontend)
- Git

### Comptes nécessaires
- **OpenAI** — clé API avec crédit (min. ~5$) → [platform.openai.com](https://platform.openai.com)
- **Google Cloud** — projet avec Gmail API activée → [console.cloud.google.com](https://console.cloud.google.com)
- **Gmail** — compte qui servira à envoyer les candidatures

---

## 🚀 Installation

### 1. Clone le projet

```bash
git clone https://github.com/ton-compte/job-agent.git
cd job-agent
```

### 2. Environnement virtuel Python

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# ou : venv\Scripts\activate  # Windows
```

### 3. Dépendances Python

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### 4. Lance les services Docker

```bash
cd ..  # retour à la racine
docker compose up -d
```

Vérifie que PostgreSQL et Redis tournent :

```bash
docker compose ps
# db et redis doivent être en statut "Up"
```

---

## ⚙️ Configuration

### 1. Copie le fichier d'environnement

```bash
cp .env.example backend/.env
```

### 2. Remplis les variables dans `backend/.env`

```env
# Base de données
DATABASE_URL=postgresql+asyncpg://jobuser:jobpass@localhost:5433/jobagent

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI — récupère ta clé sur platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-...

# Sécurité — génère avec : openssl rand -hex 32
SECRET_KEY=ta_cle_secrete_ici

# Gmail OAuth2
GMAIL_CREDENTIALS_FILE=gmail_credentials.json
GMAIL_TOKEN_FILE=gmail_token.json
GMAIL_SENDER_EMAIL=ton.email@gmail.com

# Paramètres agent
ENVIRONMENT=development
MAX_APPLICATIONS_PER_DAY=5
AUTO_SEND_THRESHOLD=85
MIN_RELEVANCE_SCORE=60
FOLLOWUP_DAYS=7
```

### 3. Personnalise ton profil candidat

Ouvre `backend/app/services/generator.py` et mets à jour `DEFAULT_CANDIDATE` :

```python
DEFAULT_CANDIDATE = {
    "full_name": "Ton Prénom Nom",
    "education": "Master 2 Data Science, Université XXX (2024-2025)",
    "skills": ["Python", "SQL", "Power BI", "Pandas", "Scikit-learn", "Excel"],
    "availability": "Disponible à partir de juin 2025",
    "duration": 6,
    "linkedin": "linkedin.com/in/ton-profil",
    "github": "github.com/ton-compte",
    "cover_letter_template": """
Madame, Monsieur,

[Ton modèle de lettre de motivation ici]

Cordialement,
""",
}
```

---

## 📧 Authentification Gmail

### 1. Crée un projet Google Cloud

1. Va sur [console.cloud.google.com](https://console.cloud.google.com)
2. Crée un nouveau projet → nomme-le `job-agent`
3. Active l'**API Gmail** → APIs et services → Bibliothèque → Gmail API → Activer

### 2. Crée les identifiants OAuth2

1. APIs et services → Identifiants → Créer des identifiants → ID client OAuth
2. Type : **Application Web**
3. URI de redirection : `http://localhost:8080/`
4. Télécharge le JSON → renomme-le `gmail_credentials.json`
5. Place-le dans `backend/`

### 3. Configure l'écran de consentement

1. APIs et services → Écran de consentement OAuth
2. Type : **Externe** → remplis le nom et ton email
3. Utilisateurs test → ajoute ton adresse Gmail

### 4. Lance l'authentification

```bash
cd backend
python3 scripts/auth_gmail.py
```

Un navigateur s'ouvre → connecte-toi → autorise l'accès → retourne dans le terminal.

```
Connecté en tant que : ton.email@gmail.com
Total messages : XXXX
Token sauvegardé ✓
```

---

## ▶️ Lancement

### Démarrage complet

**Terminal 1 — API FastAPI :**
```bash
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 — Worker Celery (relances) :**
```bash
cd backend
source ../venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info
```

**Terminal 3 — Celery Beat (scheduler) :**
```bash
cd backend
source ../venv/bin/activate
celery -A app.tasks.celery_app beat --loglevel=info
```

### Vérification

```bash
# Santé de l'API
curl http://localhost:8000/health

# Statut Gmail
curl http://localhost:8000/api/auth/gmail/status

# Doc Swagger complète
open http://localhost:8000/docs
```

---

## 📡 Utilisation de l'API

### Scraping des offres

```bash
# Lance le scraping (arrière-plan)
curl -X POST "http://localhost:8000/api/jobs/scrape" \
  -H "Content-Type: application/json" \
  -d '["Paris", "Lyon"]'

# Liste les offres scrapées
curl "http://localhost:8000/api/jobs/"

# Offres shortlistées uniquement
curl "http://localhost:8000/api/jobs/?status=shortlisted"
```

### Scoring des offres

```bash
# Score les 10 prochaines offres (to_review)
curl -X POST "http://localhost:8000/api/jobs/score-all"

# Score une offre spécifique
curl -X POST "http://localhost:8000/api/jobs/{offer_id}/score"
```

### Génération des candidatures

```bash
# Génère 5 candidatures pour les meilleures offres
curl -X POST "http://localhost:8000/api/applications/generate-batch?limit=5"

# Génère pour une offre spécifique
curl -X POST "http://localhost:8000/api/applications/generate/{offer_id}"

# Liste toutes les candidatures
curl "http://localhost:8000/api/applications/"

# Détail complet d'une candidature (email + lettre)
curl "http://localhost:8000/api/applications/{application_id}"
```

### Envoi des candidatures

```bash
# Crée un brouillon Gmail (recommandé — tu vérifies avant d'envoyer)
curl -X POST "http://localhost:8000/api/applications/{application_id}/send?mode=draft&recipient_email=recruteur@entreprise.com"

# Envoie directement (attention — action irréversible)
curl -X POST "http://localhost:8000/api/applications/{application_id}/send?mode=send&recipient_email=recruteur@entreprise.com"
```

### Statuts des candidatures

| Statut | Description |
|---|---|
| `draft` | Candidature créée, non finalisée |
| `pending_review` | En attente de validation humaine |
| `ready_to_send` | Prête à envoyer (confiance >= 85%) |
| `sent` | Email envoyé |
| `follow_up_scheduled` | Relance planifiée à J+7 |
| `follow_up_sent` | Relance envoyée |
| `response_received` | Réponse reçue |
| `interview_proposed` | Entretien proposé |
| `interview_confirmed` | Entretien confirmé |
| `refused` | Refus reçu |
| `hired` | Résultat positif |
| `archived` | Archivée |

---

## 📁 Structure du projet

```
job-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                    # Point d'entrée FastAPI
│   │   ├── config.py                  # Settings (Pydantic)
│   │   ├── database.py                # Connexion PostgreSQL async
│   │   ├── models/
│   │   │   ├── user.py                # Modèle utilisateur
│   │   │   ├── profile.py             # Profil de recherche
│   │   │   ├── job_offer.py           # Offres + Entreprises
│   │   │   ├── application.py         # Candidatures
│   │   │   └── email_thread.py        # Emails + Relances
│   │   ├── routers/
│   │   │   ├── auth.py                # OAuth2 Gmail
│   │   │   ├── jobs.py                # Scraping + Scoring
│   │   │   └── applications.py        # Candidatures + Envoi
│   │   ├── services/
│   │   │   ├── scraper/
│   │   │   │   ├── base.py            # Structure commune
│   │   │   │   ├── wttj.py            # Welcome to the Jungle
│   │   │   │   └── indeed.py          # Indeed France
│   │   │   ├── scorer.py              # Scoring LLM
│   │   │   ├── generator.py           # Génération candidatures LLM
│   │   │   ├── email_service.py       # Gmail API
│   │   │   ├── classifier.py          # Classification emails entrants
│   │   │   └── job_service.py         # Logique métier BDD
│   │   ├── tasks/
│   │   │   ├── celery_app.py          # Configuration Celery
│   │   │   ├── scraping.py            # Tâche scraping périodique
│   │   │   ├── followups.py           # Tâche relances J+7
│   │   │   └── email_monitor.py       # Surveillance boîte mail
│   │   └── prompts/
│   │       ├── analyze_offer.txt      # Prompt analyse offre
│   │       ├── score_offer.txt        # Prompt scoring
│   │       ├── generate_application.txt # Prompt génération
│   │       ├── classify_email.txt     # Prompt classification
│   │       └── write_followup.txt     # Prompt relance
│   ├── scripts/
│   │   └── auth_gmail.py              # Script auth OAuth2
│   ├── tests/
│   ├── gmail_credentials.json         # ⚠️ NE PAS COMMITTER
│   ├── gmail_token.json               # ⚠️ NE PAS COMMITTER
│   ├── .env                           # ⚠️ NE PAS COMMITTER
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   ├── Applications.jsx
│       │   └── Settings.jsx
│       └── components/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔒 Sécurité

### Règles absolues

- **Secrets** — jamais en dur dans le code, toujours via `.env`
- **OAuth2** — l'agent n'accède jamais à ton mot de passe Gmail
- **Tokens** — le `gmail_token.json` est stocké localement, jamais en BDD
- **Rate limiting** — max 5 candidatures/jour (configurable)
- **Validation humaine** — obligatoire pour les entretiens et dates de début
- **No spam** — déduplication stricte, 1 seule relance par candidature
- **Audit** — toutes les actions loguées dans `action_logs`

### Fichiers à ne JAMAIS committer

```gitignore
.env
gmail_credentials.json
gmail_token.json
venv/
__pycache__/
*.pyc
.DS_Store
```

### Révoquer l'accès Gmail

Tu peux révoquer l'accès à tout moment depuis :
[myaccount.google.com/permissions](https://myaccount.google.com/permissions)

---

## 🗺️ Roadmap

### Phase 1 — MVP ✅
- [x] Scraper WTTJ + Indeed
- [x] Scoring GPT-4o-mini
- [x] Génération email + lettre de motivation
- [x] Intégration Gmail OAuth2
- [x] CRM candidatures en PostgreSQL

### Phase 2 — En cours 🔄
- [ ] Relances automatiques Celery Beat (J+7)
- [ ] Classification LLM des réponses reçues
- [ ] Génération de réponses adaptées (entretien, info...)
- [ ] Dashboard React basique
- [ ] Ajout scraper LinkedIn + Apec

### Phase 3 — Planifié 📋
- [ ] LangGraph — agent multi-étapes avec mémoire
- [ ] Intégration Google Calendar (créneaux automatiques)
- [ ] Support Outlook / Microsoft Graph API
- [ ] Notifications Telegram/email (récap quotidien)
- [ ] Analyse statistiques (taux de réponse par plateforme)
- [ ] Multi-profils (plusieurs types de postes en parallèle)

---

## 🐛 Résolution de problèmes fréquents

### PostgreSQL ne démarre pas
```bash
# Conflit de port — change 5432 en 5433 dans docker-compose.yml et .env
docker compose down -v
docker compose up -d
```

### Erreur "password authentication failed"
```bash
# Vérifie que le port dans .env correspond au docker-compose.yml
cat backend/.env | grep DATABASE_URL
# Doit contenir localhost:5433 si tu as changé le port
```

### OpenAI timeout
```bash
# Teste la connexion directement
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | python3 -m json.tool
# Si erreur quota → ajoute du crédit sur platform.openai.com/billing
```

### Le scraper WTTJ retourne 0 offres
```bash
# WTTJ a peut-être changé ses sélecteurs — inspecte la page
grep -o 'data-testid="[^"]*"' /tmp/wttj_debug.html | sort | uniq -c | sort -rn | head -10
```

### Gmail non connecté
```bash
# Relance l'authentification
cd backend
python3 scripts/auth_gmail.py
```

---

## 📊 Base de données

```
users ──────────────── profiles
  │                       
  └── applications ──── job_offers ──── companies
        │
        ├── email_threads
        └── followups
```

Toutes les actions sont tracées dans `action_logs`.

---

## 🤝 Contribution

Projet personnel — toute suggestion bienvenue via Issues.

---

## ⚠️ Avertissement

Cet agent est conçu pour un usage personnel et raisonné. Il respecte les bonnes pratiques :
- Pas d'envoi massif aveugle (max 5/jour)
- Respect du robots.txt des plateformes
- Pas de stockage non sécurisé des credentials
- Validation humaine sur les actions à fort impact

L'utilisateur reste responsable de l'usage de cet outil et du respect des CGU des plateformes d'emploi.
