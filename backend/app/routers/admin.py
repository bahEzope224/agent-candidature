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

    # Inscriptions des 7 derniers jours
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = await db.execute(
        select(func.count()).where(User.created_at >= week_ago)
    )

    # Candidatures par statut
    sent_apps = await db.execute(
        select(func.count()).where(Application.status == "sent")
    )
    interview_apps = await db.execute(
        select(func.count()).where(Application.status.in_(["interview", "interview_proposed"]))
    )

    total = total_users.scalar() or 0
    active = active_users.scalar() or 0
    premium = premium_users.scalar() or 0
    new_week = new_users_week.scalar() or 0
    total_a = total_apps.scalar() or 0
    sent = sent_apps.scalar() or 0
    interviews = interview_apps.scalar() or 0
    total_j = total_jobs.scalar() or 0

    return {
        "users": {
            "total": total,
            "active": active,
            "premium": premium,
            "freemium": total - premium,
            "new_this_week": new_week,
        },
        "applications": {
            "total": total_a,
            "sent": sent,
            "interviews": interviews,
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
        "ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE users ADD COLUMN scraping_count_today INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN scraping_date DATE;",
        "ALTER TABLE users ADD COLUMN applications_count_month INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN applications_month INTEGER;",
        "ALTER TABLE users ADD COLUMN applications_year INTEGER;",
        "ALTER TABLE users ADD COLUMN scoring_count_today INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN scoring_date DATE;"
    ]

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

    return {"message": "Migration attempts finished", "results": results}