"""FastAPI application entrypoint and top-level router wiring."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.runs import router as runs_router
from app.db.session import get_db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend Client
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Lightweight health check that validates DB dependency wiring."""
    return {"status": "ok"}


app.include_router(runs_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
