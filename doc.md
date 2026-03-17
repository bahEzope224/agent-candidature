# Documentation Complète du Code pour le Projet "agent-candidature" (Mise à Jour Mars 2026)

Ce document fournit une documentation exhaustive du code source du projet GitHub [bahEzope224/agent-candidature](https://github.com/bahEzope224/agent-candidature). Le projet est un agent IA automatisé pour la recherche et le suivi de candidatures à des emplois en général (CDD, CDI, stages ou alternances), adaptable à n'importe quel poste en fonction du profil utilisateur. Il est structuré en deux parties principales : un backend Python basé sur FastAPI et un frontend React. Le backend gère le scraping d'offres, l'analyse par LLM (via OpenAI), la génération de candidatures, l'intégration Gmail, un CRM simple, et des relances automatiques via Celery. L'infrastructure est conteneurisée avec Docker Compose (PostgreSQL pour la BD, Redis pour les tâches) pour le développement local, mais le projet est déployé en production sur la plateforme Render, avec la base de données PostgreSQL également hébergée sur Render.

**Mises à Jour Récentes (basées sur l'historique des commits et les spécifications fournies) :**
- L'envoi automatique de mails a été désactivé. Tous les emails (candidatures et relances) sont désormais générés sous forme de textes à copier-coller, permettant une candidature manuelle par l'utilisateur via le lien direct de l'offre ou le contenu généré.
- Après scoring des offres par l'IA, un bouton/option a été ajouté (dans le frontend et via API) pour générer une lettre de motivation pour les meilleures offres (basé sur le score de pertinence).
- Logique de relance mise à jour : J+7 après statut "Envoyé" ("sent") sans réponse → basculer automatiquement en "À relancer" et générer un mail de relance (brouillon). J+7 après "Relancé" ("follow_up_sent") sans réponse → basculer en "Sans réponse".
- Ajout de boutons de confirmation manuelle pour chaque offre : [Envoyé], [Relancé], [Entretien obtenu], [Refus]. Ces boutons mettent à jour le statut de la candidature via des endpoints API et déclenchent des actions associées (ex. génération de relance).

La documentation est organisée par composant, avec pour chaque fichier : 
- **Objectif global** : Description générale.
- **Imports** : Liste des dépendances.
- **Classes et Fonctions** : Détails sur les éléments clés, paramètres, retours et explications.
- **Intégration** : Comment le fichier s'intègre au reste du projet, incluant les mises à jour récentes.

## Aperçu du Projet
- **Langages** : Python (backend), html/css, JavaScript/React (frontend).
- **Frameworks** : FastAPI (API), Celery (tâches asynchrones), SQLAlchemy (ORM), Playwright (scraping), OpenAI (LLM pour analyse/génération/classification).
- **Base de Données** : PostgreSQL (asynchrone via asyncpg), hébergée sur Render en production.
- **Dépendances Clés** : Voir la section `requirements.txt` ci-dessous.
- **Fonctionnalités Principales** (mises à jour incluses) :
  - Scraping d'offres sur Welcome to the Jungle et Indeed, adaptable à tout type de contrat (CDD, CDI, stage, alternance) et poste (basé sur le profil utilisateur : rôles cibles, compétences, localisation, durée, type de contrat).
  - Analyse et scoring des offres par rapport au profil utilisateur (rôles cibles comme "Data Analyst", "Développeur", etc., compétences, localisation, durée, type de contrat).
  - Génération automatique d'emails et lettres de motivation personnalisées, avec option/bouton pour les meilleures offres post-scoring.
  - Candidatures manuelles : Génération de brouillons Gmail ou textes à copier-coller ; envoi automatique désactivé.
  - Suivi des candidatures avec relances automatiques (J+7 après "Envoyé" → "À relancer" avec brouillon de relance ; J+7 après "Relancé" → "Sans réponse").
  - Surveillance de la boîte mail pour détecter les réponses et classifier (ex. refus, entretien).
  - Boutons de confirmation manuelle : [Envoyé], [Relancé], [Entretien obtenu], [Refus] pour mettre à jour les statuts.
  - Frontend pour dashboard, liste des candidatures et paramètres (profil adaptable à tout emploi), avec intégration des nouveaux boutons et options de génération.
- **Déploiement** : 
  - **Local** : Docker Compose pour PostgreSQL et Redis ; l'API et les workers Celery tournent séparément.
  - **Production** : Hébergé sur Render (scalabilité automatique, déploiements CI via GitHub). BD PostgreSQL sur Render (DATABASE_URL gérée via env vars). Services liés pour Redis (add-on). Variables d'environnement du `.env` uploadées sur Render.

## Structure du Backend
Le backend est organisé sous `backend/app/` avec des sous-dossiers pour les modèles, routers, services, tasks et prompts. Les scripts utilitaires sont dans `backend/scripts/`.

### backend/app/main.py
#### Objectif global
Ce fichier sert de point d'entrée pour l'application backend basée sur FastAPI. Il initialise l'app, configure son cycle de vie (incluant la création des tables DB), inclut les routers pour l'authentification, la gestion des jobs et des applications, et expose un endpoint de health check. En production sur Render, ce fichier est lancé via Uvicorn.

#### Imports
- `FastAPI` : Classe principale pour créer l'app web.
- `asynccontextmanager` : Utilitaire pour définir des événements asynchrones de cycle de vie.
- `settings` : De `app.config` pour accéder aux configurations (ex. environnement).
- `create_tables` : Fonction asynchrone de `app.database` pour initialiser le schéma DB.
- `jobs`, `applications`, `auth` : Routers de `app.routers` pour les endpoints spécifiques.
- `app.models` : Import pour charger les définitions de modèles ORM (SQLAlchemy).

#### Fonctions
1. **`lifespan(app: FastAPI)`**  
   - **Paramètres** : `app: FastAPI` – Instance de l'app.  
   - **Retour** : Gestionnaire de contexte asynchrone.  
   - **Explication** : Définit le cycle de vie de l'app. Avant le démarrage, appelle `await create_tables()` pour initialiser la DB. Permet un nettoyage après (non implémenté ici).

2. **`health()`**  
   - **Paramètres** : Aucun.  
   - **Retour** : `dict` – Réponse JSON avec statut et environnement.  
   - **Explication** : Endpoint de vérification de santé, retourne un dictionnaire indiquant que le service est opérationnel et l'environnement actuel (ex. développement, production) de `settings.ENVIRONMENT`.

#### Intégration
- **Base de Données** : Le `lifespan` déclenche `create_tables` de `app.database` au démarrage.
- **Configuration** : Utilise `settings` de `app.config` pour les configs spécifiques à l'environnement, incluant les seuils pour scoring et relances (mises à jour pour désactivation auto-send).
- **Routage** : Intègre trois routers : `auth.router` (/api/auth), `jobs.router` (/api/jobs), `applications.router` (/api/applications), avec support pour nouveaux endpoints de génération de lettres et updates de statuts.
- **Chargement des Modèles** : `import app.models` assure que tous les modèles SQLAlchemy sont importés pour les opérations DB, incluant les statuts mis à jour ("À relancer", "Sans réponse").

### backend/app/config.py
#### Objectif global
Ce fichier définit un système de gestion de configuration centralisé pour le backend en utilisant `BaseSettings` de Pydantic. Il charge les variables d'environnement depuis un fichier `.env`, fournit un accès typé aux paramètres, et met en cache l'instance. Supporte les configs pour seuils de scoring, relances, et Gmail (mises à jour pour désactiver auto-send via seuils non utilisés pour envoi direct).

#### Imports
- `pydantic_settings.BaseSettings` : Crée une classe de settings qui parse automatiquement les variables d'environnement.
- `functools.lru_cache` : Décorateur pour cacher le résultat de `get_settings()`.
- `pathlib.Path` : Gestion des chemins pour localiser le `.env`.

#### Classes
##### `Settings(BaseSettings)`
Modèle Pydantic pour définir les options de configuration.

**Champs :**
- `DATABASE_URL: str` : Chaîne de connexion à la DB.
- `REDIS_URL: str` : URL pour Redis.
- `OPENAI_API_KEY: str` : Clé API pour OpenAI.
- `SECRET_KEY: str` : Clé secrète pour cryptage.
- `ENVIRONMENT: str = "development"` : Environnement d'exécution.
- `LOG_LEVEL: str = "INFO"` : Niveau de logging.
- `MAX_APPLICATIONS_PER_DAY: int = 5` : Max candidatures par jour.
- `AUTO_SEND_THRESHOLD: int = 85` : Seuil de score pour envoi auto (désactivé ; utilisé uniquement pour suggestions de revue).
- `MIN_RELEVANCE_SCORE: int = 60` : Score min de pertinence pour génération de lettres.
- `FOLLOWUP_DAYS: int = 7` : Jours avant relance (utilisé pour logique J+7).
- `GMAIL_CREDENTIALS_FILE: str = "gmail_credentials.json"` : Chemin vers credentials OAuth2 Gmail.
- `GMAIL_TOKEN_FILE: str = "gmail_token.json"` : Chemin vers token d'accès Gmail.
- `GMAIL_SENDER_EMAIL: str = ""` : Email expéditeur pour Gmail.

**Classe imbriquée : `Config`**  
- `env_file = str(ENV_FILE)` : Chemin vers le `.env`.  
- `env_file_encoding = "utf-8"` : Encodage.

##### `get_settings() -> Settings`
- Décorée avec `@lru_cache()` pour singleton.
- **Retour** : `Settings` – Instance configurée.

#### Variables
- `ENV_FILE: Path` : Détermine le chemin du `.env`.
- `settings = get_settings()` : Instance globale.

#### Intégration
- **Mises à Jour** : `AUTO_SEND_THRESHOLD` n'est plus utilisé pour envoi direct (désactivé) ; sert à flagger les candidatures pour revue manuelle. `FOLLOWUP_DAYS` pilote la logique de relance J+7. Configs Gmail supportent drafts uniquement pour candidatures manuelles.
- **Services Externes** : Fournit credentials/URLs pour DB, Redis, OpenAI, Gmail.
- **Logique Applicative** : Valeurs pour limiter taux, filtrer offres, timing relances.

### backend/app/database.py
#### Objectif global
Configure la connexion DB avec SQLAlchemy async. Définit moteur, sessions, base pour modèles, dépendance `get_db`, et `create_tables`.

#### Imports
- `create_async_engine`, `AsyncSession`, `async_sessionmaker`, `DeclarativeBase` : SQLAlchemy async.
- `settings` : De `app.config`.

#### Classes
##### `Base(DeclarativeBase)`
- Base pour modèles.

#### Fonctions
##### `get_db() -> AsyncSession`
- Générateur de session async pour FastAPI.

##### `create_tables()`
- Crée tables async.

#### Variables
- `engine` : AsyncEngine avec `DATABASE_URL`.
- `AsyncSessionLocal` : Fabrique de sessions.

#### Intégration
- **Mises à Jour** : Supporte statuts mis à jour dans modèles (`application.py` : "sent", "follow_up_sent", "À relancer", "Sans réponse").
- **FastAPI** : `get_db` injectée dans routes.

### Modèles (backend/app/models/)
Modèles ORM pour entités, avec statuts mis à jour pour candidatures.

#### user.py
Modèle `User` pour utilisateurs.

#### profile.py
Modèle `Profile` pour profils (target_roles adaptable à tout poste, type contrat).

#### job_offer.py
Modèles `Company` et `JobOffer` (contract_type adaptable : "CDD", "CDI", "stage", "alternance").

#### application.py
Modèle `Application` pour candidatures.

**Attributs clés (mises à jour)** : `status` (default "draft" ; cycle : "draft", "sent" (Envoyé), "À relancer", "follow_up_sent" (Relancé), "interview_scheduled" (Entretien obtenu), "rejected" (Refus), "sans réponse" (Sans réponse), etc.). `sent_at`, `followup_sent_at` pour timing J+7.

#### email_thread.py
Modèles `EmailThread` et `Followup` pour threads et relances.

### Routers (backend/app/routers/)
Endpoints API.

#### auth.py
Auth Gmail, statut connexion.

#### jobs.py
Scraping, liste offres, scoring. Mise à jour : Après scoring, support pour génération lettres via lien vers /applications/generate.

#### applications.py
#### Objectif global
Routeur pour gestion candidatures : liste, génération batch/individuelle, détails, classification réponses. Mises à jour : Endpoints pour génération lettres post-scoring, updates statuts via boutons ([Envoyé], etc.), trigger relances ; auto-send désactivé (génère drafts ou texts).

#### Imports
- `APIRouter`, `Depends`, `HTTPException` : FastAPI.
- `AsyncSession`, `select`, `selectinload` : SQLAlchemy.
- `get_db` : De `database`.
- `generate_application` : De `generator`.
- `create_application_draft` : De `job_service`.
- `send_email`, `create_draft` : De `email_service` (send désactivé ; drafts only).
- `classify_email`, `generate_interview_response`, `generate_info_response` : De `classifier`.
- `get_email_body`, `create_draft` : De `email_service`.
- `EmailThread`, `Application`, `JobOffer` : Modèles.

#### Fonctions (mises à jour incluses)
1. **`list_applications(status, db)`** : Liste candidatures avec filtre statut (inclut nouveaux statuts).
2. **`pending_followups(db)`** : Liste attendant relance (J+7 après "sent").
3. **`generate_batch(limit, db)`** : Génère pour shortlistées (post-scoring ; inclut lettres ; drafts).
4. **`trigger_followups()`** : Déclenche vérification relances (J+7 logic).
5. **`generate_for_offer(offer_id, db)`** : Génère pour offre spécifique (bouton pour meilleures ; lettre, email text ; action "pending_review" since auto-send off).
6. **`get_application(application_id, db)`** : Détails (inclut cover_letter).
7. **`classify_all_responses(db)`** : Classifie réponses, génère brouillons (pour entretiens, etc.).

**Mises à jour non explicites dans code (inférées)** : Nouveaux endpoints implicites pour update statut (ex. POST /applications/{id}/update-status avec body {status: "sent"} pour boutons).

#### Intégration
- **Génération** : `generate_application` produit lettre/email ; drafts via `create_draft`.
- **Manuelle** : Texts à copy-paste ou drafts ; lien offre in JobOffer.
- **Statuts** : Updates pour boutons, relance logic.

### Services (backend/app/services/)
#### scraper/ (base.py, wttj.py, indeed.py)
Scraping adaptable à tout poste/contrat.

#### scorer.py
Analyse/scoring offres vs profil (adaptable).

#### generator.py
#### Objectif global
Génère emails/lettres via GPT. Mise à jour : Support pour génération lettres pour meilleures offres post-scoring.

#### Imports
- `json`, `Path` : Prompts.
- `AsyncOpenAI` : Client.
- `JobOffer` : Modèle.
- `settings` : Clé API.

#### Variables
- `DEFAULT_CANDIDATE` : Profil défaut (adaptable).
- `client` : OpenAI.

#### Fonctions
1. **`load_prompt(name)`** : Charge prompt.
2. **`generate_application(offer, candidate)`** : Génère candidature (email, lettre, confidence) ; utilise analysis/score pour personnalisation.

#### Intégration
- **Mises à Jour** : Appelée post-scoring pour meilleures offres (score >= MIN_RELEVANCE_SCORE) ; produit lettre pour manuel.
- **LLM** : `gpt-4o-mini`.

#### email_service.py
#### Objectif global
Service Gmail : drafts, envoi (désactivé auto), lecture.

#### Imports
- `os`, `base64`, `json`, `MIMEText`, `MIMEMultipart` : Emails.
- `Path`, `Request`, `Credentials`, `InstalledAppFlow`, `build`, `HttpError` : Google API.
- `settings` : Config.

#### Variables
- `SCOPES` : Scopes OAuth.

#### Fonctions
1. **`get_gmail_service()`** : Service authentifié.
2. **`build_email(to, subject, body, sender)`** : Construit message.
3. **`send_email(to, subject, body)`** : Envoi (désactivé auto ; manuel only).
4. **`create_draft(to, subject, body)`** : Brouillon (utilisé pour tout).
5. **`get_recent_emails(max_results)`** : Emails récents.
6. **`get_email_body(message_id)`** : Corps.

#### Intégration
- **Mises à Jour** : Auto-send désactivé ; tout via drafts pour manuel. Utilisé pour relances J+7.

#### classifier.py
Classification réponses, génération réponses.

#### job_service.py
Sauvegarde offres/candidatures (drafts).

### Tâches (backend/app/tasks/)
#### celery_app.py
Configure Celery, beat schedule pour scraping, relances, monitor (J+7 logic).

#### scraping.py
Scraping quotidien.

#### followups.py
#### Objectif global
Tâche pour relances J+7. Mises à jour : J+7 après "sent" → "À relancer" + générer relance (draft) ; J+7 après "follow_up_sent" → "Sans réponse" (inféré ; code base sur "sent" to "follow_up_sent").

#### Imports
- `shared_task` : Celery.
- `datetime`, `timedelta` : Dates.
- `select`, `selectinload` : SQLAlchemy.
- `json` : Parse.
- `structlog` : Logging.
- `Application`, `JobOffer`, `Company`, `Followup` : Modèles.
- `create_draft` : De `email_service`.
- `asyncio` : Async.

#### Fonctions
1. **`check_and_send_followups(self)`** : Vérifie candidatures "sent" J+7, génère relance, update to "follow_up_sent".
2. **`send_single_followup(application, db)`** : Génère/envoie relance (draft), update statut.
3. **`generate_followup_text(application, offer, company_name)`** : Texte via GPT.
4. **`get_default_followup(job_title, company)`** : Template défaut.

#### Intégration
- **Mises à Jour** : Logique J+7 pour "À relancer" / "Sans réponse" ; drafts only. Vérifie weekends.
- **DB** : Session synchrone.
- **Gmail** : Brouillons.
- **LLM** : `gpt-4o-mini`.

#### email_monitor.py
Surveillance inbox, détection réponses pour statuts.

### Prompts (backend/app/prompts/)
Prompts pour LLM (analyse, score, génération, classification, followup).

### Scripts (backend/scripts/)
#### auth_gmail.py
Auth OAuth Gmail.

## Frontend (frontend/src/pages/)
Composants React pour UI.

#### Dashboard.jsx
Tableau de bord : Stats offres/candidatures.

#### Applications.jsx
#### Objectif global
Page pour liste candidatures. Mises à jour : Boutons pour générer lettres post-scoring, confirmations ([Envoyé], etc.), copy-paste mails, liens offres.

#### Intégration
- **UI** : Boutons déclenchent API (/generate, /update-status). Liste avec statuts, options manuelles.
- **React** : Composants pour carousel offres, modals pour lettres/drafts.

#### Settings.jsx
Paramètres profil (adaptable postes/contrats).

## Fichiers de Configuration
### docker-compose.yml
Services : db (PostgreSQL), redis.

### requirements.txt
Dépendances : FastAPI, SQLAlchemy, Celery, OpenAI, Google APIs, etc.

### .env.example
Variables : DATABASE_URL, etc. (inclut FOLLOWUP_DAYS=7).