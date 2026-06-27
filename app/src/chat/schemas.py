from datetime import datetime

from pydantic import BaseModel


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


class ModelOption(BaseModel):
    slug: str
    name: str
    priority: int
    enabled: bool

    model_config = {"from_attributes": True}


class ModelToggle(BaseModel):
    enabled: bool
