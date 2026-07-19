# Technical Performance Report

## SME Credit Risk ML Pipeline (Ushirika) — Group 15

**Aligned to proposal chapters 1–5 (methodology & results)**  
**Environment:** FastAPI + SQLite (Postgres-ready), Random Forest primary, Logistic Regression + statsmodels Logit baselines  
**Frontend:** Vite (HTML/JS/CSS) portal for SME, lender, and admin  
**Random seed:** 42

---

## 1. Objectives coverage (Ch. 1)

| Specific objective | System fulfilment |
|--------------------|-------------------|
| SO1 — Preprocessing & feature engineering | `preprocessing.py` (median impute, IQR clip) + `feature_engineering.py` (17 predictive variables from supply-chain transactions) |
| SO2 — Ensemble vs classical regression | Random Forest vs sklearn Logistic Regression (+ statsmodels Logit benchmark) |
| SO3 — Industry metrics | Accuracy, Precision, Recall, F1, ROC-AUC, confusion matrix, classification report |

General objective: automated ecosystem banking prototype using supply-chain transaction data for inclusive SME credit assessment in Tanzania — delivered as the Ushirika portal.

---

## 2. Methodology implementation (Ch. 3)

| Proposal item (§) | Implemented |
|-------------------|-------------|
| Backend: Python, Pandas, Scikit-Learn, Statsmodels (§3.2) | Yes |
| Frontend: Vite dashboard (§3.2) | Yes — SME, lender (per-SME ML metrics on detail), admin |
| SQL storage + PII policy (§3.5 / §3.11) | SQLite/SQLAlchemy; ML matrix excludes PII; HMAC `counterparty_hash` + opaque `display_token` |
| Missing values & outliers (§3.7) | Median imputation; IQR clip on delays/volume; transaction amount outliers for financing |
| EDA with Seaborn & Plotly (§3.7) | `scripts/run_eda.py` → `reports/eda/` |
| Feature scaling (§3.7) | StandardScaler inside LR pipeline |
| LR + Random Forest (§3.8) | Yes |
| 80/20 train–test + k-fold CV (§3.9) | Stratified split + StratifiedKFold GridSearchCV (ROC-AUC) |
| Metrics Acc/Prec/Rec/F1/ROC-AUC (§3.9) | Saved in `models/model_meta.json` and DB `model_metrics` |
| Deliverables: ML backend, Vite UI, this report (§3.10) | Yes |

---

## 3. Feature set (value-chain signals)

| Internal key | User-facing label |
|--------------|-------------------|
| payment_consistency | Payment reliability |
| payment_delay_avg / max | Average / longest payment delay |
| turnover_tzs | Total business volume (TZS) |
| transaction_frequency | Transactions per month |
| completion_rate_avg | Average order completion |
| default_rate / compliance_rate | Default / compliance rates |
| account_age_months | Account age |
| counterparty_diversity | Business partner diversity |
| volume_trend | Sales volume trend |
| on_time_rate | On-time payment rate |
| avg_transaction_interval_days | Days between transactions |
| buyer_share / supplier_share / distributor_share | Value-chain role shares |
| order_type_diversity | Order-type diversity |

Extra (scoring UI, not always in RF vector): unusual large transactions, typical volume excluding outliers.

---

## 4. Measured performance

After `python scripts/train_model.py`, exact floats are in:

- `Backend/models/model_meta.json`
- `Backend/reports/latest_evaluation.json`
- Admin portal → **ML Metrics** (`#/admin/ml`)

Typical seed=42 hold-out results (version `20260719090647`):

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|-------|----------|-----------|--------|-----|---------|
| **Random Forest (primary)** | **0.8857** | **0.9296** | **0.8571** | **0.8919** | **0.9583** |
| Logistic Regression (baseline) | 0.7786 | 0.7584 | 0.8766 | 0.8133 | 0.8749 |
| statsmodels Logit | 0.7786 | — | — | — | 0.8750 |

RF confusion matrix (rows = actual, cols = predicted): `[[116, 10], [22, 132]]` (TN/FP/FN/TP).

Re-run `python scripts/train_model.py` for the latest floats; also see Admin → **ML Metrics**.

---

## 5. Outliers and realistic financing

- **Outlier detection:** IQR on transaction amounts (`is_outlier`).
- **Financing caps:** Eligible amount uses typical (non-outlier) volume — avoids one-off giant invoices inflating offers.

---

## 6. Credit score mapping

```
probability p → raw = 300 + p × 500
score = 350 + (raw − 350) × 0.66   → clipped ~300–680
```

Risk bands: Low ≥ 580 · Medium 480–579 · High < 480  
Minimum **5 transactions** before scoring.

---

## 7. Results vs proposal Ch. 4–5

- Preprocessing and feature engineering pipelines are operational (Ch. 4.2 / SO1).
- Ensemble RF outperforms classical LR on hold-out ROC-AUC (Ch. 4.3 / SO2).
- Standard metrics + confusion matrices document reliability (Ch. 4.3 / SO3).
- Prototype scope (not full market deployment) matches Ch. 5 limitations.
- Future work (XGBoost, neural nets, SHAP) remains future work — not claimed as delivered.

---

## 8. Reproduction

```bash
cd Backend
pip install -r requirements.txt
python scripts/train_model.py
python scripts/run_eda.py
pytest
```

Admin UI: sign in as admin → **ML Metrics** → Retrain / Run EDA.
