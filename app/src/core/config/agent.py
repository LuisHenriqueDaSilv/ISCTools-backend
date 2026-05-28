import json

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_MODELS = json.dumps([
    {"id": "gemini-2.0-flash", "alias": "Gemini 2.0 Flash"},
    {"id": "gemini-2.5-flash-lite", "alias": "Gemini 2.5 Flash Lite"},
    {"id": "gemini-1.5-flash", "alias": "Gemini 1.5 Flash"},
    {"id": "gemini-1.5-pro", "alias": "Gemini 1.5 Pro"},
])


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_window_size: int = Field(default=10, validation_alias="AGENT_WINDOW_SIZE")
    gemini_models: str = Field(default=_DEFAULT_MODELS, validation_alias="GEMINI_MODELS")

    def get_models(self) -> list[dict]:
        return json.loads(self.gemini_models)
