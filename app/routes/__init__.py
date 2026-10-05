"""Route exports."""

from app.routes.brokers import router as brokers_router
from app.routes.commissions import router as commissions_router
from app.routes.payouts import router as payouts_router
from app.routes.posts import router as posts_router
from app.routes.video import router as video_router

__all__ = ["brokers_router", "commissions_router", "payouts_router", "posts_router", "video_router"]
