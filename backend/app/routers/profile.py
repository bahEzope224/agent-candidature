from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.dependencies import get_current_user

router = APIRouter()


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    education_level: Optional[str] = None
    school: Optional[str] = None
    graduation_year: Optional[str] = None
    skills_technical: Optional[List[str]] = None
    skills_soft: Optional[List[str]] = None
    languages: Optional[List[dict]] = None
    tools: Optional[List[str]] = None
    target_roles: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None
    target_contract: Optional[str] = None
    min_salary: Optional[str] = None
    availability_date: Optional[str] = None
    pitch: Optional[str] = None
    strengths: Optional[str] = None
    motivation: Optional[str] = None


@router.get("/")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé")

    return {
        "id": str(profile.id),
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "full_name": f"{profile.first_name or ''} {profile.last_name or ''}".strip(),
        "phone": profile.phone,
        "location": profile.location,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
        "education_level": profile.education_level,
        "school": profile.school,
        "graduation_year": profile.graduation_year,
        "skills_technical": profile.skills_technical or [],
        "skills_soft": profile.skills_soft or [],
        "languages": profile.languages or [],
        "tools": profile.tools or [],
        "target_roles": profile.target_roles or [],
        "target_locations": profile.target_locations or [],
        "target_contract": profile.target_contract,
        "min_salary": profile.min_salary,
        "availability_date": profile.availability_date,
        "pitch": profile.pitch,
        "strengths": profile.strengths,
        "motivation": profile.motivation,
        "updated_at": str(profile.updated_at),
    }


@router.patch("/")
async def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        # Crée le profil s'il n'existe pas
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    # Met à jour uniquement les champs fournis
    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    from datetime import datetime
    profile.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Profil mis à jour", "updated_fields": list(update_data.keys())}


@router.post("/skills/add")
async def add_skill(
    category: str,
    skill: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ajoute une compétence à une catégorie"""
    valid_categories = ["skills_technical", "skills_soft", "tools", "target_roles", "target_locations"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Catégorie invalide. Valeurs: {valid_categories}")

    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé")

    current_list = getattr(profile, category) or []
    if skill not in current_list:
        setattr(profile, category, current_list + [skill])
        await db.commit()
        return {"message": f"'{skill}' ajouté à {category}"}
    return {"message": f"'{skill}' déjà présent"}


@router.delete("/skills/remove")
async def remove_skill(
    category: str,
    skill: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Supprime une compétence"""
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé")

    current_list = getattr(profile, category) or []
    updated = [s for s in current_list if s != skill]
    setattr(profile, category, updated)
    await db.commit()
    return {"message": f"'{skill}' supprimé"}