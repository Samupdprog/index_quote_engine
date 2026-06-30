"""Base declarativa para todos los modelos SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base común de todos los modelos ORM."""
    pass
