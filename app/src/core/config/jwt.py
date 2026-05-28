from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class JWTSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = Field(default="", validation_alias="SECRET_KEY")
    expire_minutes: int = Field(default=30, validation_alias="JWT_EXPIRE_MINUTES")
