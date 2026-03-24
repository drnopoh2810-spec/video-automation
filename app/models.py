from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.database import Base


class Channel(Base):
    __tablename__ = "channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    niche: Mapped[str] = mapped_column(String(100), default="finance")
    voice_id: Mapped[str] = mapped_column(String(100), default="EXAVITQu4vr4xnSDxMaL")
    character_style: Mapped[str] = mapped_column(String(100), default="family_guy")
    target_duration: Mapped[int] = mapped_column(Integer, default=120)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Video(Base):
    __tablename__ = "videos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    video_title: Mapped[str] = mapped_column(String(500))
    channel_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    script_json: Mapped[str] = mapped_column(Text, nullable=True)
    scene_count: Mapped[int] = mapped_column(Integer, nullable=True)
    total_duration: Mapped[float] = mapped_column(Float, nullable=True)
    final_video_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ApiAccount(Base):
    __tablename__ = "api_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service: Mapped[str] = mapped_column(String(50))   # groq, elevenlabs, huggingface, creatomate, supabase
    label: Mapped[str] = mapped_column(String(200))
    api_key: Mapped[str] = mapped_column(String(500))
    extra: Mapped[dict] = mapped_column(JSON, default=dict)  # e.g. supabase_url
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ErrorLog(Base):
    __tablename__ = "error_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow: Mapped[str] = mapped_column(String(50))
    node_name: Mapped[str] = mapped_column(String(200))
    error_message: Mapped[str] = mapped_column(Text)
    video_id: Mapped[str] = mapped_column(String(100), nullable=True)
    scene_id: Mapped[str] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentLog(Base):
    __tablename__ = "agent_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[str] = mapped_column(String(100), index=True)
    agent: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20), default="info")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
