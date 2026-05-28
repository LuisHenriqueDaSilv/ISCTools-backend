from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.auth import service
from src.auth.schemas import GoogleLoginPayload, Token
from src.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=Token)
def google_login(payload: GoogleLoginPayload, db: Session = Depends(get_db)):
    try:
        return service.google_login(db, payload.id_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
