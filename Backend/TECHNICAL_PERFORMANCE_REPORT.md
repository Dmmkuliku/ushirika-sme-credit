# Ushirika technical performance report

**What this document is:** a plain-language record of how the credit system works, what we measured, and how that matches the Group 15 project goals.  
**Audience:** supervisors, examiners, and teammates — not only data scientists.  
**Platform version:** 1.3.1 · Random Forest primary scorer · Logistic Regression baseline

---

## In one paragraph

Ushirika turns an SME’s supply-chain transactions into a credit score. The business uploads or records deals (who they traded with, amounts, payment status). The system cleans that data, builds behavioural features, and runs the same Random Forest model that lenders see when they open an SME profile. After enough activity (at least five transactions), the SME and the lender both see a score, a risk band, and an indicative financing amount — without relying only on collateral.

---

## How this meets the project objectives

| Goal from the proposal | What the live system does |
|------------------------|---------------------------|
| Build preprocessing and feature engineering | Raw transactions become payment reliability, delays, volume, partner mix, buyer/supplier shares, and related signals |
| Compare ensemble vs classical models | Random Forest (main) vs Logistic Regression (baseline), with the same train/test split |
| Prove reliability with standard metrics | Accuracy, precision, recall, F1, ROC-AUC, plus confusion matrix |
| Deliver a usable prototype | Vite portal + FastAPI backend + this report |

---

## What happens when an SME uploads data

1. **Upload or record** — CSV template or manual form (TIN of the other party is required).  
2. **Clean and save** — Invalid rows are skipped with clear messages; valid rows are stored.  
3. **Score immediately** — The current Random Forest model scores that SME’s data (this is the same model path lenders use).  
4. **Show the result** — Score, risk, creditworthy chance, and key signals appear; the overview updates.  
5. **Refresh in the background** — A fuller retrain may run after scoring so future assessments keep learning from live SME mixes, without freezing the upload button.

This design avoids the old failure mode where a long training job made “Upload” look broken on slow hosting.

---

## Data and privacy (in everyday terms)

- Login uses NIDA or membership ID plus a PIN.  
- The machine-learning table never includes names, phone numbers, emails, or TIN as features.  
- Counterparties are linked with a one-way hash; lenders mainly see an opaque display token plus the score story.  
- Unusual large invoices are flagged so one outlier deal does not inflate the financing offer.

---

## Features the model uses (plain labels)

Payment reliability · average and longest delay · total volume · deals per month · order completion · default and compliance rates · account age · partner diversity · sales trend · on-time rate · days between deals · share of buyers / suppliers / distributors · mix of order types.

---

## Measured performance (example training run)

Exact latest numbers live in `models/model_meta.json` after training. A representative hold-out result:

| Model | Role | Accuracy | F1 | ROC-AUC |
|-------|------|----------|-----|---------|
| Random Forest | Primary (what lenders use) | ~0.89 | ~0.89 | ~0.96 |
| Logistic Regression | Fair baseline | ~0.78 | ~0.81 | ~0.87 |

**Reading tip:** ROC-AUC closer to 1.0 means the model ranks creditworthy vs higher-risk cases more reliably. On this data, Random Forest stays ahead of the classical baseline — which is what the proposal expected.

Training protocol: 80% train / 20% test, stratified; 5-fold cross-validation while tuning; median fill for missing values; IQR clip on noisy continuous fields.

---

## How a score becomes a financing hint

```
Model probability → score roughly in the 300–680 band (conservative mapping)
Low risk ≥ 580 · Medium 480–579 · High below 480
Eligible amount is capped by typical (non-outlier) trading volume
```

---

## Where to look in the product

| Who | Where | What they see |
|-----|-------|----------------|
| SME | Upload CSV → progress → ML result | Same family of metrics the lender will review |
| SME | Overview | Score ring, financing hint, explainable factors |
| Lender | Portfolio → select SME | Full **ML metrics for this SME** from that firm’s feed |
| Admin | Accounts | Create and manage users (not the lending decision screen) |

---

## How to reproduce the numbers

```bash
cd Backend
pip install -r requirements.txt
python scripts/train_model.py
python scripts/run_eda.py
pytest
```

EDA charts are written under `Backend/reports/eda/`. Evaluation snapshots under `Backend/reports/latest_evaluation.json`.

---

## Honest limits (prototype scope)

- Labels for training still combine engineered rules with live SME features; a production bank would eventually use observed repayment outcomes.  
- Hosting is a free-tier prototype (cold starts can slow the first click).  
- Future upgrades could include gradient boosting, clearer SHAP-style explanations, and live ERP feeds — those remain future work, not claims of this release.
