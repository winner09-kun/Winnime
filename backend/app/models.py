from sqlalchemy import String, JSON, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .core.database import Base

class Watchlist(Base):
    __tablename__ = 'watchlist'
    anime_id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String, default='PLANNING')
    anime: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[float] = mapped_column(Float)

class History(Base):
    __tablename__ = 'history'
    episode_id: Mapped[str] = mapped_column(String, primary_key=True)
    anime_id: Mapped[int] = mapped_column(index=True)
    episode: Mapped[int]
    position: Mapped[float] = mapped_column(Float)
    duration: Mapped[float] = mapped_column(Float)
    completed: Mapped[bool] = mapped_column(Boolean)
    anime: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[float] = mapped_column(Float)

class Source(Base):
    __tablename__ = 'sources'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anime_id: Mapped[int] = mapped_column(index=True)
    episode: Mapped[int]
    provider: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    language: Mapped[str] = mapped_column(String)
    subtitles: Mapped[list] = mapped_column(JSON, default=list)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

class Setting(Base):
    __tablename__ = 'settings'
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    data: Mapped[dict] = mapped_column(JSON)

class Cache(Base):
    __tablename__ = 'cache'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[float] = mapped_column(Float)
