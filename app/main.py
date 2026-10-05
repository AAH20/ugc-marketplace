"""Main FastAPI application."""
from fastapi import FastAPI
from app import models  # noqa: F401 - ensures all models registered with Base
from app.database import init_db, get_db
from app.routes import brokers_router, commissions_router, payouts_router, posts_router
from app.routes.dashboard import router as dashboard_router
from app.routes.monitoring import router as monitoring_router
from app.routes.websockets import ws_router
from app.routes.video import router as video_router

app = FastAPI(
    title="UGC Marketplace Broker API",
    description="Broker channel dashboard backend for MENA market",
    version="1.0.0",
)

# Include routers
app.include_router(brokers_router)
app.include_router(commissions_router)
app.include_router(payouts_router)
app.include_router(posts_router)
app.include_router(dashboard_router)
app.include_router(monitoring_router)
app.include_router(ws_router)
app.include_router(video_router)


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
