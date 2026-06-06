from datetime import datetime

from pydantic import BaseModel, field_validator

from src.core.config import settings


class ToolCallOut(BaseModel):
    id: int
    name: str
    input: dict
    output: str

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    llm_model: str | None = None
    tool_calls: list[ToolCallOut] = []
    is_error: bool = False
    error_code: str | None = None

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class SendMessage(BaseModel):
    content: str
    model: str

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        valid_ids = {m["id"] for m in settings.agent.get_models()}
        if v not in valid_ids:
            raise ValueError(f"Modelo não suportado. Use um de: {', '.join(sorted(valid_ids))}")
        return v


class RetryMessage(BaseModel):
    model: str

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        valid_ids = {m["id"] for m in settings.agent.get_models()}
        if v not in valid_ids:
            raise ValueError(f"Modelo não suportado. Use um de: {', '.join(sorted(valid_ids))}")
        return v


class GeminiModelOption(BaseModel):
    id: str
    alias: str
