from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.auth import service
from src.auth.schemas import UserCreate, UserOut
from src.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return service.register(db, payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
