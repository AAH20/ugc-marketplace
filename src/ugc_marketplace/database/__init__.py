"""Database package for UGC Marketplace."""
from ugc_marketplace.database.archival import ArchivalManager
from ugc_marketplace.database.manager import DatabaseManager, get_db_manager
from ugc_marketplace.database.partitions import PartitionManager
from ugc_marketplace.models import Base


def get_db():
    """Yield a database session."""
    from ugc_marketplace.database.manager import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["Base", "DatabaseManager", "get_db", "get_db_manager", "PartitionManager", "ArchivalManager"]
