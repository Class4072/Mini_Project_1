from app.database import get_db

# Re-export get_db for convenient API dependency injection
__all__ = ["get_db"]
