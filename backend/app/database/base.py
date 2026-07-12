from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models after Base is defined so SQLAlchemy registers every table.
from app import models  # noqa: E402,F401

