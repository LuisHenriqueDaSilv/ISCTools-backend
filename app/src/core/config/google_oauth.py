from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleOAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    client_id: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
