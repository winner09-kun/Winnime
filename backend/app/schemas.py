import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

Status = Literal['PLANNING', 'WATCHING', 'COMPLETED', 'PAUSED', 'DROPPED']

class Anime(BaseModel):
    id: int
    mal_id: int | None = None
    title: str
    titles: list[str] = []
    cover: str | None = None
    banner: str | None = None
    description: str = ''
    score: float | None = None
    year: int | None = None
    season: str | None = None
    genres: list[str] = []
    format: str | None = None
    status: str | None = None
    episodes: int | None = None
    duration: int | None = None
    studios: list[str] = []
    links: list[dict] = []
    next_episode: dict | None = None
    characters: list[dict] = []
    relations: list[dict] = []
    recommendations: list[dict] = []

class WatchInput(BaseModel):
    anime_id: int
    anime: Anime
    status: Status = 'PLANNING'
    @model_validator(mode='after')
    def matching_id(self):
        if self.anime_id != self.anime.id:
            raise ValueError('Anime ID does not match metadata')
        return self

class WatchPatch(BaseModel):
    status: Status

class HistoryInput(BaseModel):
    anime_id: int
    episode: int = Field(ge=1)
    position: float = Field(ge=0, allow_inf_nan=False)
    duration: float = Field(ge=0, allow_inf_nan=False)
    completed: bool = False
    anime: Anime
    @model_validator(mode='after')
    def matching_id(self):
        if self.anime_id != self.anime.id:
            raise ValueError('Anime ID does not match metadata')
        return self

class Subtitle(BaseModel):
    url: str
    language: str = 'id'
    label: str = 'Indonesia'
    @field_validator('url')
    @classmethod
    def safe_url(cls, v):
        if not v.startswith(('https://', 'http://localhost', 'http://127.0.0.1')):
            raise ValueError('Use HTTPS or a local media server')
        return v

class SourceInput(BaseModel):
    anime_id: int = Field(gt=0)
    episode: int = Field(ge=1)
    provider: Literal['youtube', 'mp4', 'hls', 'cloudflare']
    url: str
    language: str = 'Japanese'
    subtitles: list[Subtitle] = []
    available: bool = True
    authorized: Literal[True]
    @model_validator(mode='after')
    def validate_url(self):
        if self.provider == 'youtube':
            if not re.fullmatch(r'[\w-]{11}', self.url):
                raise ValueError('Use an 11-character YouTube video ID')
        elif self.provider == 'cloudflare':
            if not re.fullmatch(r'[a-fA-F0-9]{32}', self.url):
                raise ValueError('Use a Cloudflare Stream video UID')
        elif not self.url.startswith(('https://', 'http://localhost:', 'http://127.0.0.1:')):
            raise ValueError('Use an HTTPS media URL or local media server')
        return self

class SettingsInput(BaseModel):
    autoplay: bool = False
    auto_next: bool = False
    show_completed: bool = True
