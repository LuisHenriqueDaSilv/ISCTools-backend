from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LangSmithSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    tracing: bool = Field(default=False, validation_alias="LANGSMITH_TRACING")
    api_key: str | None = Field(default=None, validation_alias="LANGSMITH_API_KEY")
    project: str = Field(default="isctools", validation_alias="LANGSMITH_PROJECT")
    endpoint: str = Field(
        default="https://api.smith.langchain.com",
        validation_alias="LANGSMITH_ENDPOINT",
    )
