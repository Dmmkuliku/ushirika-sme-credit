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


def migrate_schema() -> None:
    """Add new columns when upgrading an existing database."""
    dialect = engine.dialect.name
    with engine.begin() as conn:
        sme_cols = _existing_columns("sme_profiles")
        if sme_cols and "tin" not in sme_cols:
            logger.info("Adding sme_profiles.tin")
            conn.execute(text("ALTER TABLE sme_profiles ADD COLUMN tin VARCHAR(20)"))
        if sme_cols and "district" not in sme_cols:
            logger.info("Adding sme_profiles.district")
            conn.execute(text("ALTER TABLE sme_profiles ADD COLUMN district VARCHAR(100)"))

        tx_cols = _existing_columns("transactions")
        if tx_cols:
            additions = [
                ("counterparty_tin", "VARCHAR(20)"),
                ("counterparty_name", "VARCHAR(200)"),
                ("is_outlier", "BOOLEAN DEFAULT 0" if dialect == "sqlite" else "BOOLEAN DEFAULT FALSE"),
            ]
            for name, coltype in additions:
                if name not in tx_cols:
                    logger.info("Adding transactions.%s", name)
                    conn.execute(text(f"ALTER TABLE transactions ADD COLUMN {name} {coltype}"))
