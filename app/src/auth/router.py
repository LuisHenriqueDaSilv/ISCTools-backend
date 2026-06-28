from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.auth import service
from src.auth.schemas import GoogleLoginPayload, Token
from src.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/google",
    response_model=Token,
    summary="Login com Google",
    response_description="JWT da aplicação a ser usado como Bearer token.",
    responses={
        200: {"description": "Login bem-sucedido; retorna o access token."},
        401: {"description": "`id_token` do Google inválido ou expirado."},
    },
)
def google_login(payload: GoogleLoginPayload, db: Session = Depends(get_db)):
    """Troca um `id_token` do Google por um JWT próprio da aplicação.

    O `id_token` é validado contra o `GOOGLE_CLIENT_ID` configurado. No primeiro
    login, o usuário é criado a partir das claims do Google (`email`, `name`,
    `picture`); nos seguintes, é recuperado por `google_sub`.
    """
    try:
        return service.google_login(db, payload.id_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
