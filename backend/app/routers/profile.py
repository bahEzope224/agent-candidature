from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        "phone": profile.phone,
        "location": profile.location,
        "education_level": profile.education_level,
        "school": profile.school,
        "graduation_year": profile.graduation_year,
        "skills": profile.skills or [],
        "skills_technical": profile.skills_technical or [],
        "skills_soft": profile.skills_soft or [],
        "tools": profile.tools or [],
        "languages": profile.languages or [],
        "strengths": profile.strengths,
        "target_roles": profile.target_roles or [],
        "target_locations": profile.target_locations or [],
        "target_contract": profile.target_contract,
        "min_salary": profile.min_salary,
        "availability_date": str(profile.availability_date) if profile.availability_date else None,
        "pitch": profile.pitch,
        "motivation": profile.motivation,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
    }


@router.patch("/")
async def update_profile(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé")

    allowed = [
        "first_name", "last_name", "phone", "location",
        "education_level", "school", "graduation_year",
        "skills", "skills_technical", "skills_soft", "tools",
        "languages", "strengths", "target_roles", "target_locations",
        "target_contract", "min_salary", "availability_date",
        "pitch", "motivation", "linkedin_url", "portfolio_url",
    ]
    for key, value in body.items():
        if key in allowed:
            setattr(profile, key, value)

    await db.commit()
    return {"message": "Profil mis à jour"}
