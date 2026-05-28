from sqlalchemy.orm import Session

from src.auth.models import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_by_google_sub(db: Session, google_sub: str) -> User | None:
    return db.query(User).filter(User.google_sub == google_sub).first()


def create(db: Session, email: str, google_sub: str, name: str | None, picture: str | None) -> User:
    user = User(email=email, google_sub=google_sub, name=name, picture=picture)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
