from fastapi import FastAPI

from src.auth.router import router as auth_router
from src.chat.router import router as chat_router

app = FastAPI(title="ISCTools API", version="0.1.0")

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
