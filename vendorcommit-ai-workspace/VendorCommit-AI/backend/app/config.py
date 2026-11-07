from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', case_sensitive=False)
    app_env: str = 'development'
    api_prefix: str = '/api/v1'
    database_url: str = 'sqlite:///./vendorcommit.db'
    jwt_secret: str = 'development-only-secret-change-before-deploying'
    jwt_algorithm: str = 'HS256'
    access_token_minutes: int = 60
    auth_required: bool = True
    cors_origins: str = 'http://localhost:5173'
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    seed_demo: bool = False
    memory_mode: str = 'LOCAL_MOCK'
    hindsight_api_url: str = ''
    hindsight_api_key: str = ''
    hindsight_bank_id: str = ''
    memory_max_retries: int = Field(default=3, ge=0, le=10)
    memory_retry_backoff_seconds: float = Field(default=0.5, ge=0, le=30)

    @field_validator('memory_mode')
    @classmethod
    def validate_memory_mode(cls, value):
        value = value.upper()
        if value not in {'LOCAL_MOCK', 'CLOUD'}:
            raise ValueError('MEMORY_MODE must be LOCAL_MOCK or CLOUD')
        return value

    @property
    def cors_origin_list(self):
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]

    def validate_security(self):
        if self.app_env.lower() == 'production':
            if not self.auth_required:
                raise RuntimeError('AUTH_REQUIRED cannot be false in production')
            if len(self.jwt_secret) < 32 or self.jwt_secret.startswith('development-only'):
                raise RuntimeError('A secure JWT_SECRET of at least 32 characters is required in production')
            if self.memory_mode == 'CLOUD':
                local_hindsight = any(host in self.hindsight_api_url for host in ('127.0.0.1', 'localhost'))
                if not self.hindsight_api_url or not self.hindsight_bank_id or (not local_hindsight and not self.hindsight_api_key):
                    raise RuntimeError('Hindsight requires API URL and bank ID; hosted cloud also requires an API key')


@lru_cache
def get_settings():
    return Settings()
