from datetime import datetime, timedelta, timezone

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.auth import repository
from src.auth.models import User
from src.core.config import settings


def google_login(db: Session, token: str) -> dict:
    try:
        id_info = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.google.client_id
        )
    except ValueError:
        raise ValueError("Invalid Google token")

    google_sub = id_info["sub"]
    user = repository.get_by_google_sub(db, google_sub)
    if not user:
        user = repository.create(
            db,
            email=id_info["email"],
            google_sub=google_sub,
            name=id_info.get("name"),
            picture=id_info.get("picture"),
        )

    return _build_token(user)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt.secret_key, algorithms=["HS256"])
    except JWTError:
        raise ValueError("Invalid or expired token")


def _build_token(user: User) -> dict:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt.expire_minutes)
    payload = {"sub": str(user.id), "email": user.email, "exp": exp}
    access_token = jwt.encode(payload, settings.jwt.secret_key, algorithm="HS256")
    return {"access_token": access_token, "token_type": "bearer"}
