from sqlalchemy.orm import Session

from src.auth import repository
from src.auth.models import User


def get_or_raise(db: Session, email: str) -> User:
    user = repository.get_by_email(db, email)
    if not user:
        raise ValueError("User not found")
    return user


def register(db: Session, email: str, password: str) -> User:
    if repository.get_by_email(db, email):
        raise ValueError("Email already registered")
    # TODO: hash password before storing
    return repository.create(db, email=email, hashed_password=password)
