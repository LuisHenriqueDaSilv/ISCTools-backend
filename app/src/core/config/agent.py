import json

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_MODELS = json.dumps([
    {"id": "gemini-3.1-pro-preview", "alias": "Gemini 3.1 Pro Preview"},
    {"id": "gemini-3.5-flash", "alias": "Gemini 3.5 Flash"},
    {"id": "gemini-3-flash-preview", "alias": "Gemini 3 Flash Preview"},
    {"id": "gemini-3.1-flash-lite", "alias": "Gemini 3.1 Flash Lite"},
    {"id": "gemini-2.5-flash", "alias": "Gemini 2.5 Flash"},
    {"id": "gemini-2.5-flash-lite", "alias": "Gemini 2.5 Flash Lite"},
    {"id": "gemini-2.5-pro", "alias": "Gemini 2.5 Pro"}
])


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_window_size: int = Field(default=10, validation_alias="AGENT_WINDOW_SIZE")
    gemini_models: str = Field(default=_DEFAULT_MODELS, validation_alias="GEMINI_MODELS")

    def get_models(self) -> list[dict]:
        return json.loads(self.gemini_models)
