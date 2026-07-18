# Technical Performance Report

## SME Credit Risk ML Pipeline (Ushirika v1.2)

**Environment:** FastAPI + SQLite/Postgres-ready, Random Forest primary, Logistic Regression baseline  
**Random seed:** 42 (reproducible synthetic bootstrap)

---

## 1. How real machine learning works in this system

1. **Feature engineering** — Each SME’s supply-chain transactions are turned into numeric features (payment reliability, delays, typical volume, partner diversity, days between deals, etc.).
2. **Training** — Two classifiers are fit with GridSearchCV on an 80/20 stratified hold-out:
   - **Random Forest** (ensemble, primary)
   - **Logistic Regression** (linear baseline)
3. **Live data loop** — When an SME records or uploads transactions and has at least 5 deals, the backend:
   - rebuilds features for all eligible SMEs from the database,
   - **mixes those real rows into training** (upsampled) with synthetic bootstrap data,
   - re-saves `.joblib` models + `models/model_meta.json`,
   - reloads the in-memory predictor,
   - runs a fresh **prediction** (credit score + risk band + eligible financing).
4. **Explainability** — Score components are shown with **plain-language labels** (not programmer variable names).

This is real sklearn training and inference — not a hard-coded score table.

---

## 2. Objectives coverage

| Objective | How the system fulfills it |
|-----------|----------------------------|
| Data-driven SME credit for Tanzania | End-to-end portal: SME transactions → ML score → lender portfolio |
| Preprocessing & features | `compute_features()` + outlier flags |
| Ensemble vs classical ML | RF vs LR on same split; ROC-AUC decides honesty of “RF wins” |
| Realistic lending amounts | Financing capped by **typical (non-outlier) volume**, not one-off giant deals |

---

## 3. Outliers and realistic financing

- **Outlier detection:** IQR rule on transaction amounts (high-side). Marked on each transaction (`is_outlier`).
- **Financing caps:** Eligible amount = min(score-based amount, 75% of typical volume, ~8× median typical deal).
- **Concept:** An SME whose usual deals are under TZS 1M should not be offered tens of millions just because of one unusual invoice.

---

## 4. Feature set (internal keys → user labels)

| Internal key | Shown to users as |
|--------------|-------------------|
| payment_consistency | Payment reliability |
| payment_delay_avg | Average payment delay (days) |
| payment_delay_max | Longest payment delay (days) |
| turnover_tzs | Total business volume (TZS) |
| transaction_frequency | Transactions per month |
| completion_rate_avg | Average order completion |
| default_rate | Default rate |
| compliance_rate | Compliance rate |
| account_age_months | Account age (months) |
| counterparty_diversity | Business partner diversity |
| volume_trend | Sales volume trend |
| on_time_rate | On-time payment rate |
| avg_transaction_interval_days | Average days between transactions |

Extra display metrics: unusual large transactions count, typical volume excluding outliers.

---

## 5. Measured performance (example seed=42)

Exact latest floats live in `models/model_meta.json` after training. Meta also records `real_sme_profiles_used` and `training_source` (`synthetic_bootstrap` or `synthetic+real_sme_transactions`).

| Model | Role |
|-------|------|
| Random Forest | Primary scorer |
| Logistic Regression | Baseline comparator |

---

## 6. Credit score mapping (conservative)

```
probability p → raw = 300 + p × 500
score = 350 + (raw − 350) × 0.66   → clipped ~300–680
```

Risk bands: Low ≥ 580 · Medium 480–579 · High < 480  
Minimum **5 transactions** before scoring.

---

## 7. Where to show “the model is trained”

| Location | What you see |
|----------|----------------|
| `Backend/models/model_meta.json` | Version, metrics, real SME count, paths to `.joblib` |
| `Backend/models/random_forest_*.joblib` | Trained primary model artifact |
| Admin `POST /api/admin/train-model` | Manual full retrain |
| After SME CSV upload / record (≥5 txs) | Automatic retrain + rescore |
| SME Credit overview | Score, financing, human-readable components, model version |

---

## 8. Reproduction

```bash
cd Backend
pip install -r requirements.txt
python scripts/train_model.py
```

Inspect `models/model_meta.json` for the latest run.
