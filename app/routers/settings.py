from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import ApiAccount

router = APIRouter(prefix="/api/settings", tags=["settings"])

SERVICES = ["groq", "elevenlabs", "huggingface", "creatomate", "supabase"]


class AccountRequest(BaseModel):
    service: str
    label: str
    api_key: str
    extra: Optional[dict] = {}
    is_active: bool = True


@router.get("/accounts")
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiAccount).order_by(ApiAccount.service, ApiAccount.id))
    accounts = result.scalars().all()
    return [{"id": a.id, "service": a.service, "label": a.label,
             "api_key": a.api_key[:8] + "****" if a.api_key else "",
             "extra": a.extra, "is_active": a.is_active,
             "created_at": a.created_at.isoformat()} for a in accounts]


@router.post("/accounts")
async def add_account(req: AccountRequest, db: AsyncSession = Depends(get_db)):
    if req.service not in SERVICES:
        raise HTTPException(400, f"Unknown service. Valid: {SERVICES}")
    account = ApiAccount(**req.model_dump())
    db.add(account)
    await db.commit()
    return {"id": account.id, "service": account.service, "label": account.label}


@router.put("/accounts/{account_id}")
async def update_account(account_id: int, req: AccountRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiAccount).where(ApiAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")
    for k, v in req.model_dump().items():
        setattr(account, k, v)
    await db.commit()
    return {"status": "updated"}


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiAccount).where(ApiAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")
    await db.delete(account)
    await db.commit()
    return {"status": "deleted"}
