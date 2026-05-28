from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    role: str
    content: str

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}


class SendMessage(BaseModel):
    content: str
