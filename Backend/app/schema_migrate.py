"""Lightweight SQLite/Postgres column migrations for additive schema changes."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from app.database import engine

logger = logging.getLogger(__name__)


def _existing_columns(table: str) -> set[str]:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _add_column_if_missing(conn, table: str, column: str, coltype: str) -> None:
    cols = _existing_columns(table)
    if not cols or column in cols:
        return
    logger.info("Adding %s.%s", table, column)
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


def migrate_schema() -> None:
    """Add new columns when upgrading an existing database."""
    dialect = engine.dialect.name
    bool_default = "BOOLEAN DEFAULT 0" if dialect == "sqlite" else "BOOLEAN DEFAULT FALSE"

    # Use separate transactions so each ALTER is applied even if a later one fails.
    with engine.begin() as conn:
        _add_column_if_missing(conn, "sme_profiles", "tin", "VARCHAR(20)")
    with engine.begin() as conn:
        _add_column_if_missing(conn, "sme_profiles", "district", "VARCHAR(100)")

    tx_cols = _existing_columns("transactions")
    if tx_cols:
        for name, coltype in (
            ("counterparty_tin", "VARCHAR(20)"),
            ("counterparty_name", "VARCHAR(200)"),
            ("is_outlier", bool_default),
        ):
            with engine.begin() as conn:
                _add_column_if_missing(conn, "transactions", name, coltype)
