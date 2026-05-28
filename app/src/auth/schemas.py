from pydantic import BaseModel, EmailStr


class GoogleLoginPayload(BaseModel):
    id_token: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str | None
    picture: str | None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
