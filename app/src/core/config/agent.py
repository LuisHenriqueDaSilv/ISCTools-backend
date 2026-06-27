from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Referência para o script de seed do catálogo (app/scripts/seed_models.py).
# A fonte da verdade do catálogo passa a ser a tabela `models` (D8).
DEFAULT_MODELS = [
    {"slug": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro Preview"},
    {"slug": "gemini-3.5-flash", "name": "Gemini 3.5 Flash"},
    {"slug": "gemini-3-flash-preview", "name": "Gemini 3 Flash Preview"},
    {"slug": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite"},
    {"slug": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
    {"slug": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite"},
    {"slug": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
]


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_window_size: int = Field(default=10, validation_alias="AGENT_WINDOW_SIZE")
