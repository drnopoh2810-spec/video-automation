from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models import Channel

router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelRequest(BaseModel):
    channel_id: str
    name: str
    niche: str = "finance"
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    character_style: str = "family_guy"
    target_duration: int = 120


@router.get("")
async def list_channels(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).order_by(Channel.id))
    return [{"id": c.id, "channel_id": c.channel_id, "name": c.name, "niche": c.niche,
             "voice_id": c.voice_id, "character_style": c.character_style,
             "target_duration": c.target_duration} for c in result.scalars().all()]


@router.post("")
async def create_channel(req: ChannelRequest, db: AsyncSession = Depends(get_db)):
    channel = Channel(**req.model_dump())
    db.add(channel)
    await db.commit()
    return {"id": channel.id, "channel_id": channel.channel_id}


@router.put("/{channel_id}")
async def update_channel(channel_id: str, req: ChannelRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.channel_id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(404, "Channel not found")
    for k, v in req.model_dump().items():
        setattr(channel, k, v)
    await db.commit()
    return {"status": "updated"}


@router.delete("/{channel_id}")
async def delete_channel(channel_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.channel_id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(404, "Channel not found")
    await db.delete(channel)
    await db.commit()
    return {"status": "deleted"}
