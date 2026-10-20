from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    database_url: str = 'sqlite:///./kaze.db'
    allowed_origins: list[str] = ['http://127.0.0.1:5173', 'http://localhost:5173']
    cache_ttl: int = 1800
    wajik_base_url: str = 'https://wajik-anime-api.vercel.app'
    model_config = SettingsConfigDict(env_prefix='KAZE_', env_file='.env', extra='ignore')

config = Config()
