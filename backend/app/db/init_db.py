from sqlalchemy.engine import Engine
from sqlalchemy import inspect, text

from app.db import schema as _schema  # noqa: F401
from app.db.session import Base, engine


def init_database(bind: Engine | None = None) -> None:
    active_engine = bind or engine
    Base.metadata.create_all(bind=active_engine)
    _migrate_sqlite_dataset_metadata(active_engine)


def _migrate_sqlite_dataset_metadata(active_engine: Engine) -> None:
    if active_engine.dialect.name != "sqlite":
        return

    inspector = inspect(active_engine)
    if "datasets" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("datasets")
    }
    required_columns = {
        "file_size_bytes": "INTEGER NOT NULL DEFAULT 0",
        "stored_file_path": "TEXT",
        "artifact_path": "TEXT",
        "column_metadata": "JSON NOT NULL DEFAULT '[]'",
        "warnings": "JSON NOT NULL DEFAULT '[]'",
    }

    with active_engine.begin() as connection:
        for column_name, column_sql in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE datasets ADD COLUMN {column_name} {column_sql}")
                )

    _add_missing_sqlite_columns(
        active_engine,
        table_name="reports",
        required_columns={
            "dataset_overview": "TEXT NOT NULL DEFAULT ''",
            "data_quality_notes": "JSON NOT NULL DEFAULT '[]'",
            "evidence_appendix": "JSON NOT NULL DEFAULT '[]'",
        },
    )


def _add_missing_sqlite_columns(
    active_engine: Engine,
    *,
    table_name: str,
    required_columns: dict[str, str],
) -> None:
    inspector = inspect(active_engine)
    if table_name not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns(table_name)
    }
    with active_engine.begin() as connection:
        for column_name, column_sql in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
                )
