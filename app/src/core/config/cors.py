from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CORSSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    allowed_origins: list[str] = Field(
        default_factory=list,
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_csv(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value
