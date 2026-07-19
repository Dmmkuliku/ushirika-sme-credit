"""Run exploratory data analysis (Seaborn + Plotly) for proposal §3.7."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.services.eda import run_eda  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        summary = run_eda(db_session=db)
    finally:
        db.close()
    print("EDA complete.")
    print(f"  Rows: {summary['rows']}")
    print(f"  Summary: {summary.get('summary_path')}")
    for name, path in summary.get("figures", {}).items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
