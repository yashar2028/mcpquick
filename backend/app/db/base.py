from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Alembic metadata autogeneration sees all tables.
from app.models import run as run_models  # noqa: F401, E402
from app.models import user as user_models  # noqa: F401, E402
