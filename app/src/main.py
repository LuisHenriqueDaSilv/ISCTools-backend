from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.chat.router import router as chat_router
from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_api_settings()
    yield


app = FastAPI(title="ISCTools API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
