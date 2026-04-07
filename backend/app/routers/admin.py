"""
Routes admin — protégées par whitelist email.
Accessible uniquement depuis bahibrahimatalibe@gmail.com
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, delete as sql_delete
from datetime import datetime, date, timedelta
from app.database import get_db
from app.models.user import User
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.models.profile import Profile
from app.models.system_log import SystemLog
from app.services.auth_service import get_current_user
import uuid

router = APIRouter()

# ── Whitelist admins ──────────────────────────────────────────
ADMIN_EMAILS = {
    "contact@ibrahima-bah.com",
}


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dépendance — vérifie que l'utilisateur est admin."""
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return current_user


# ── Liste des utilisateurs ────────────────────────────────────
@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    user_list = []
    for u in users:
        # Compte ses candidatures et offres
        apps_count = await db.execute(
            select(func.count()).where(Application.user_id == u.id)
        )
        jobs_count = await db.execute(
            select(func.count()).where(JobOffer.user_id == u.id)
        )
        user_list.append({
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name or "—",
            "is_active": u.is_active,
            "is_premium": u.is_premium,
            "applications_count": apps_count.scalar() or 0,
            "jobs_count": jobs_count.scalar() or 0,
            "applications_this_month": u.applications_count_month or 0,
            "scrapings_today": u.scraping_count_today or 0,
            "scoring_today": u.scoring_count_today or 0,
            "last_login_at": str(u.last_login_at) if u.last_login_at else None,
            "created_at": str(u.created_at),
        })

    return user_list


# ── Stats globales ────────────────────────────────────────────
@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    total_users = await db.execute(select(func.count()).select_from(User))
    active_users = await db.execute(select(func.count()).where(User.is_active == True))
    premium_users = await db.execute(select(func.count()).where(User.is_premium == True))
    total_apps = await db.execute(select(func.count()).select_from(Application))
    total_jobs = await db.execute(select(func.count()).select_from(JobOffer))

    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = await db.execute(
        select(func.count()).where(User.created_at >= week_ago)
    )

    # Candidatures par statut
    sent_apps = await db.execute(select(func.count()).where(Application.status.in_(["sent", "follow_up_needed", "follow_up_sent", "no_response"])))
    interview_apps = await db.execute(select(func.count()).where(Application.status.in_(["interview", "interview_proposed"])))
    signed_apps = await db.execute(select(func.count()).where(Application.status == "offer"))
    refused_apps = await db.execute(select(func.count()).where(Application.status.in_(["refused", "archived"])))
    pending_apps = await db.execute(select(func.count()).where(Application.status.in_(["to_apply", "pending_review", "ready_to_send"])))

    # Historique 30 jours — inscriptions utilisateurs
    users_history = []
    apps_history = []
    for i in range(29, -1, -1):
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        label = day_start.strftime("%d/%m")
        u_count = await db.execute(select(func.count()).where(User.created_at >= day_start, User.created_at < day_end))
        a_count = await db.execute(select(func.count()).where(Application.created_at >= day_start, Application.created_at < day_end))
        users_history.append({"date": label, "count": u_count.scalar() or 0})
        apps_history.append({"date": label, "count": a_count.scalar() or 0})

    total = total_users.scalar() or 0
    active = active_users.scalar() or 0
    premium = premium_users.scalar() or 0
    new_week = new_users_week.scalar() or 0
    total_a = total_apps.scalar() or 0
    sent = sent_apps.scalar() or 0
    interviews = interview_apps.scalar() or 0
    signed = signed_apps.scalar() or 0
    refused = refused_apps.scalar() or 0
    pending = pending_apps.scalar() or 0
    total_j = total_jobs.scalar() or 0

    conversion_rate = round((interviews / sent * 100), 1) if sent > 0 else 0
    signing_rate = round((signed / total_a * 100), 1) if total_a > 0 else 0

    return {
        "users": {
            "total": total,
            "active": active,
            "premium": premium,
            "freemium": total - premium,
            "new_this_week": new_week,
            "history_30d": users_history,
        },
        "applications": {
            "total": total_a,
            "pending": pending,
            "sent": sent,
            "interviews": interviews,
            "signed": signed,
            "refused": refused,
            "conversion_rate": conversion_rate,
            "signing_rate": signing_rate,
            "history_30d": apps_history,
        },
        "jobs": {
            "total": total_j,
        },
    }



# ── Activer / bloquer un compte ───────────────────────────────
@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    user.is_active = not user.is_active
    await db.commit()
    return {
        "id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
        "message": f"Compte {'activé' if user.is_active else 'bloqué'}",
    }


# ── Passer en premium / freemium ──────────────────────────────
@router.patch("/users/{user_id}/toggle-premium")
async def toggle_user_premium(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    user.is_premium = not user.is_premium
    await db.commit()
    return {
        "id": str(user.id),
        "email": user.email,
        "is_premium": user.is_premium,
        "message": f"Plan mis à jour : {'Premium ⭐' if user.is_premium else 'Freemium'}",
    }


# ── Supprimer un compte ───────────────────────────────────────
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    # Supprime d'abord les données liées
    await db.execute(sql_delete(Application).where(Application.user_id == user_id))
    await db.execute(sql_delete(JobOffer).where(JobOffer.user_id == user_id))
    await db.execute(sql_delete(Profile).where(Profile.user_id == user_id))
    await db.delete(user)
    await db.commit()

    return {"message": f"Compte {user.email} supprimé"}


# ── Réinitialiser les compteurs d'un user ─────────────────────
@router.patch("/users/{user_id}/reset-quotas")
async def reset_user_quotas(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    user.scraping_count_today = 0
    user.applications_count_month = 0
    user.scoring_count_today = 0
    await db.commit()

    return {"message": "Quotas réinitialisés", "email": user.email}

# ── Migration Temporaire DB ────────────────────────────────────
@router.get("/migrate-db-temp")
async def migrate_database(db: AsyncSession = Depends(get_db)):
    """
    Exécute des requêtes ALTER TABLE pour ajouter les colonnes manquantes 
    sans effacer les données existantes.
    """
    queries = [
        "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE users ADD COLUMN scraping_count_today INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN scraping_date DATE;",
        "ALTER TABLE users ADD COLUMN applications_count_month INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN applications_month INTEGER;",
        "ALTER TABLE users ADD COLUMN applications_year INTEGER;",
        "ALTER TABLE users ADD COLUMN scoring_count_today INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN scoring_date DATE;",
        "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN locked_until TIMESTAMP;",
        "ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP;"
    ]

    # Colonnes Profile manquantes (en cas de DB ancienne)
    profile_cols = [
        ("first_name", "VARCHAR"), ("last_name", "VARCHAR"), ("phone", "VARCHAR"), ("location", "VARCHAR"),
        ("education_level", "VARCHAR"), ("school", "VARCHAR"), ("graduation_year", "VARCHAR"),
        ("strengths", "TEXT"), ("pitch", "TEXT"), ("motivation", "TEXT"),
        ("linkedin_url", "VARCHAR"), ("portfolio_url", "VARCHAR")
    ]
    for col, ctype in profile_cols:
        queries.append(f"ALTER TABLE profiles ADD COLUMN {col} {ctype};")

    profile_arrays = ["skills", "skills_technical", "skills_soft", "tools", "languages", "target_roles", "target_locations"]
    for col in profile_arrays:
        queries.append(f"ALTER TABLE profiles ALTER COLUMN {col} DROP DEFAULT;")
        queries.append(f"ALTER TABLE profiles ALTER COLUMN {col} TYPE JSON USING array_to_json({col});")
        queries.append(f"ALTER TABLE profiles ALTER COLUMN {col} SET DEFAULT '[]'::json;")
    
    job_arrays = ["required_skills", "nice_to_have_skills"]
    for col in job_arrays:
        queries.append(f"ALTER TABLE job_offers ALTER COLUMN {col} DROP DEFAULT;")
        queries.append(f"ALTER TABLE job_offers ALTER COLUMN {col} TYPE JSON USING array_to_json({col});")
        queries.append(f"ALTER TABLE job_offers ALTER COLUMN {col} SET DEFAULT '[]'::json;")
    
    results = []
    for q in queries:
        try:
            await db.execute(text(q))
            await db.commit()
            results.append({"query": q, "status": "success"})
        except Exception as e:
            await db.rollback()
            results.append({"query": q, "status": "failed_or_already_exists", "error": str(e)})

    # Création table logs (si manquante)
    create_logs_table = """
    CREATE TABLE IF NOT EXISTS system_logs (
        id UUID PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        level VARCHAR(50) NOT NULL,
        action VARCHAR(100) NOT NULL,
        details JSON,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
    );
    """
    try:
        await db.execute(text(create_logs_table))
        await db.commit()
        results.append({"query": "CREATE TABLE system_logs", "status": "success"})
    except Exception as e:
        await db.rollback()
        results.append({"query": "CREATE TABLE system_logs", "status": "failed", "error": str(e)})

    return {"message": "Migration attempts finished", "results": results}


# ── LOGS SYSTÈME ─────────────────────────────────────────────
@router.get("/logs")
async def get_system_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Récupère les derniers logs système"""
    result = await db.execute(
        select(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return logs


@router.delete("/logs/purge")
async def purge_logs(
    older_than_days: int = 30,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Supprime les logs anciens"""
    limit_date = datetime.utcnow() - timedelta(days=older_than_days)
    await db.execute(
        sql_delete(SystemLog).where(SystemLog.created_at < limit_date)
    )
    await db.commit()
    return {"message": f"Logs plus vieux que {older_than_days} jours supprimés"}