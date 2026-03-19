"""
Router Billing — Stripe Checkout + Webhooks
--------------------------------------------
GET  /api/billing/status          → statut abonnement de l'utilisateur
POST /api/billing/checkout        → crée une session Stripe Checkout
POST /api/billing/webhook         → reçoit les events Stripe
POST /api/billing/cancel          → annule l'abonnement
"""
from __future__ import annotations
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_user
from app.config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

# ── Limites par plan ────────────────────────────────────────────
PLAN_LIMITS = {
    "free":  {"applications": 3,   "scraping": 2,  "label": "Gratuit"},
    "pro":   {"applications": 999, "scraping": 999, "label": "Pro"},
}

PRICE_NORMAL = settings.STRIPE_PRICE_NORMAL   # price_xxx 2.99€/semaine
PRICE_PROMO  = settings.STRIPE_PRICE_PROMO    # price_xxx 1.99€/semaine (promo lancement)


# ── Helpers ─────────────────────────────────────────────────────

def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


async def check_application_limit(user: User, db: AsyncSession) -> None:
    """Lève une 403 si l'utilisateur free a atteint sa limite de 3 candidatures."""
    if user.plan == "pro":
        return  # pas de limite

    from app.models.application import Application
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(Application.id)).where(Application.user_id == user.id)
    )
    count = result.scalar() or 0
    limit = PLAN_LIMITS["free"]["applications"]
    if count >= limit:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "LIMIT_REACHED",
                "message": f"Tu as utilisé tes {limit} candidatures gratuites.",
                "upgrade_url": "/api/billing/checkout",
                "current": count,
                "limit": limit,
            }
        )


# ── Routes ──────────────────────────────────────────────────────

@router.get("/status")
async def billing_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne le statut d'abonnement et les limites de l'utilisateur."""
    from app.models.application import Application
    from sqlalchemy import func

    result = await db.execute(
        select(func.count(Application.id)).where(Application.user_id == current_user.id)
    )
    apps_count = result.scalar() or 0
    limits = get_plan_limits(current_user.plan or "free")

    return {
        "plan": current_user.plan or "free",
        "plan_label": limits["label"],
        "applications_used": apps_count,
        "applications_limit": limits["applications"],
        "applications_remaining": max(0, limits["applications"] - apps_count) if current_user.plan != "pro" else 999,
        "is_pro": current_user.plan == "pro",
        "stripe_customer_id": current_user.stripe_customer_id,
        "subscription_status": current_user.subscription_status,
    }


@router.post("/checkout")
async def create_checkout(
    current_user: User = Depends(get_current_user),
    promo: bool = False,
):
    """Crée une session Stripe Checkout et retourne l'URL de paiement."""
    if current_user.plan == "pro":
        raise HTTPException(status_code=400, detail="Tu es déjà abonné Pro !")

    price_id = PRICE_PROMO if promo else PRICE_NORMAL

    try:
        # Crée ou récupère le customer Stripe
        if current_user.stripe_customer_id:
            customer_id = current_user.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name or current_user.email,
                metadata={"user_id": str(current_user.id)},
            )
            customer_id = customer.id

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}?upgrade=success",
            cancel_url=f"{settings.FRONTEND_URL}?upgrade=cancelled",
            metadata={"user_id": str(current_user.id)},
            subscription_data={
                "trial_period_days": 7,  # 7 jours d'essai gratuit
                "metadata": {"user_id": str(current_user.id)},
            },
            allow_promotion_codes=True,
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }

    except stripe.StripeError as e:
        logger.error("Erreur Stripe checkout", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur Stripe : {str(e)}")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Reçoit et traite les événements Stripe.
    Configure l'URL dans Stripe Dashboard → Webhooks.
    """
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Signature Stripe invalide")

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe webhook reçu", event=event_type)

    # ── Abonnement activé ──
    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        sub_status = data.get("status")
        customer_id = data.get("customer")
        sub_id = data.get("id")

        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Cherche via metadata
            user_id = data.get("metadata", {}).get("user_id")
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

        if user:
            is_active = sub_status in ("active", "trialing")
            user.plan = "pro" if is_active else "free"
            user.stripe_customer_id = customer_id
            user.stripe_subscription_id = sub_id
            user.subscription_status = sub_status
            await db.commit()
            logger.info("Plan mis à jour", email=user.email, plan=user.plan, status=sub_status)

    # ── Checkout complété ──
    elif event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        user_id = data.get("metadata", {}).get("user_id")

        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and not user.stripe_customer_id:
                user.stripe_customer_id = customer_id
                await db.commit()

    # ── Paiement échoué ──
    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.subscription_status = "past_due"
            await db.commit()
            logger.warning("Paiement échoué", email=user.email)

    # ── Abonnement annulé ──
    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.plan = "free"
            user.subscription_status = "cancelled"
            await db.commit()
            logger.info("Abonnement annulé", email=user.email)

    return {"received": True}


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Annule l'abonnement à la fin de la période en cours."""
    if not current_user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="Aucun abonnement actif")

    try:
        stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=True,
        )
        current_user.subscription_status = "cancelling"
        await db.commit()
        return {"message": "Abonnement annulé à la fin de la période en cours"}
    except stripe.StripeError as e:
        raise HTTPException(status_code=500, detail=str(e))
