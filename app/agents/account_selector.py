"""Selects active API accounts from DB, falls back to env vars."""
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ApiAccount


async def get_account(db: AsyncSession, service: str) -> dict:
    """Returns {'api_key': ..., 'extra': {...}} for the given service."""
    result = await db.execute(
        select(ApiAccount)
        .where(ApiAccount.service == service, ApiAccount.is_active == True)
        .order_by(ApiAccount.id)
        .limit(1)
    )
    account = result.scalar_one_or_none()
    if account:
        return {"api_key": account.api_key, "extra": account.extra or {}}

    # Fallback to environment variables
    env_map = {
        "groq": "GROQ_API_KEY",
        "elevenlabs": "ELEVENLABS_API_KEY",
        "huggingface": "HUGGINGFACE_API_KEY",
        "creatomate": "CREATOMATE_API_KEY",
        "supabase": "SUPABASE_API_KEY",
    }
    key = os.getenv(env_map.get(service, ""), "")
    extra = {}
    if service == "supabase":
        extra["url"] = os.getenv("SUPABASE_URL", "")
    return {"api_key": key, "extra": extra}
