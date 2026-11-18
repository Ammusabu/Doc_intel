"""Declarative base + shared metadata. Import every ORM model so create_all sees them."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Re-export models for create_all (added as phases progress)
from app.models import user, document, chunk, conversation, search  # noqa: E402,F401
