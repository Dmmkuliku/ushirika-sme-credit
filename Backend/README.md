# SME Credit Risk Backend

Production-minded prototype API for supply-chain credit risk assessment, supporting **SME** and **Lender** roles with JWT authentication, pseudonymized PII storage, ML-based credit scoring, and portfolio analytics.

## Stack

- **FastAPI** – REST API with OpenAPI docs
- **SQLAlchemy + SQLite** – no external database required
- **Pydantic** – request/response validation
- **JWT + bcrypt** – authentication and password hashing
- **pandas / scikit-learn / joblib** – feature engineering and credit models

## Quick Start

```powershell
cd Backend

# Use Python 3.13 (recommended). Python 3.14 can break native packages like pydantic-core.
py -3.13 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env

# Train model (optional – also runs on startup)
python scripts\train_model.py

# Seed demo data
python scripts\seed_data.py

# Run API (prefer python -m so the venv interpreter is always used)
python -m uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/api/docs
- Health: http://localhost:8000/api/health

## Demo Accounts

| Role   | Email              | Password        |
|--------|--------------------|-----------------|
| Admin  | admin@demo.local   | AdminPass123!   |
| Lender | lender@demo.local  | LenderPass123!  |
| SME    | sme1@demo.local    | SmePass123!     |

## API Overview

| Endpoint | Role | Description |
|----------|------|-------------|
| `POST /api/auth/register` | Public | Register SME or Lender |
| `POST /api/auth/login` | Public | JWT login |
| `GET /api/sme/profile` | SME | Pseudonymized profile |
| `POST /api/transactions` | SME | Add transaction |
| `POST /api/transactions/import` | SME | CSV bulk import |
| `GET /api/transactions/export/estatement` | SME | CSV e-statement |
| `POST /api/credit/score` | SME | Credit score (≥5 txns) |
| `GET /api/credit/history/monthly` | SME | Monthly aggregates |
| `GET /api/dashboard/sme` | SME | SME dashboard |
| `GET /api/lender/portfolio` | Lender | SME portfolio list |
| `GET /api/lender/sme/{id}` | Lender | SME detail |
| `GET /api/dashboard/lender` | Lender | Lender dashboard |
| `POST /api/admin/train-model` | Admin | Retrain ML models |
| `GET /api/health` | Public | Health check |

## Security

- **PII pseudonymization**: business name, email, phone, tax ID, and counterparty names are stored as stable HMAC-SHA256 hashes only.
- **JWT expiry**: configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 min). Invalid/expired tokens return `401`.
- **Role guards**: endpoints enforce SME / Lender / Admin permissions.

## ML Pipeline

- **Primary**: Random Forest with GridSearchCV
- **Baseline**: Logistic Regression with StandardScaler
- **Evaluation**: 80/20 stratified split, 5-fold CV tuning, metrics: accuracy, precision, recall, F1, ROC-AUC
- Synthetic bootstrap data uses non-linear risk interactions so RF generally outperforms the linear baseline honestly on hold-out evaluation.

## Tests

```bash
pytest -v
```

## Project Structure

```
Backend/
├── app/
│   ├── main.py              # FastAPI app + CORS + lifespan
│   ├── config.py            # Settings from .env
│   ├── database.py          # SQLAlchemy engine
│   ├── dependencies.py      # Auth & role guards
│   ├── models/              # ORM models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API routes
│   ├── services/            # Business logic
│   └── utils/               # Security & pseudonymization
├── scripts/
│   ├── seed_data.py         # Demo data
│   └── train_model.py       # Reproducible training
├── tests/
├── models/                  # Saved joblib artifacts
└── data/                    # SQLite database
```

## CORS

Configured for Vite dev server (`http://localhost:5173`). Update `CORS_ORIGINS` in `.env` for other origins.
