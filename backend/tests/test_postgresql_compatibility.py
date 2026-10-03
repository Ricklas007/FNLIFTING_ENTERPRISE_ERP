from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

from app.database.base import Base
from app.models import MediaAttachment  # noqa: F401


def test_metadata_tables_compile_with_postgresql_dialect():
    dialect = postgresql.dialect()
    tables = ["users", "companies", "media_attachments", "documents", "certificates", "map_packages"]
    compiled = {name: str(CreateTable(Base.metadata.tables[name]).compile(dialect=dialect)) for name in tables}
    assert "CREATE TABLE media_attachments" in compiled["media_attachments"]
    assert "VARCHAR(64)" in compiled["media_attachments"]
    assert "CREATE TABLE certificates" in compiled["certificates"]
