"""Drop all tables and recreate with new schema."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.models  # noqa: F401 — register models with Base
from app.database import Base, engine

Base.metadata.drop_all(bind=engine)
print("All tables dropped.")
Base.metadata.create_all(bind=engine)
print("Tables recreated with new schema.")
