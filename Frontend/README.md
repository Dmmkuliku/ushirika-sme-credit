# Ushirika — Tanzania SME Banking Portal (Frontend)

Vanilla Vite SPA for the Tanzania SME ecosystem banking portal. Supports **SME** and **Lender** roles with JWT token authentication against a FastAPI backend.

## Stack

- Vite 6
- Vanilla HTML, JavaScript (ES modules), CSS
- No React — lightweight native SVG/canvas charts only

## Setup

```bash
cd Frontend
cp .env.example .env
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Environment

| Variable        | Description                                      | Default                 |
|-----------------|--------------------------------------------------|-------------------------|
| `VITE_API_URL`  | FastAPI base URL (no trailing slash)             | `http://localhost:8000` |

## Scripts

| Command           | Purpose                    |
|-------------------|----------------------------|
| `npm run dev`     | Development server         |
| `npm run build`   | Production build → `dist/` |
| `npm run preview` | Preview production build   |

## Features

- Login / register with explicit **SME | Lender** role selector
- Bearer token auth stored in `sessionStorage`
- Logout control + **auto-logout after exactly 30s** of no mouse/keyboard/touch/scroll activity (warning overlay + countdown from 20s idle)
- Role-gated hash routes and navigation
- SME: credit overview (score locked until ≥5 transactions), risk, estimated TZS financing, explainability components, monthly chart, transaction filters, CSV upload (template/help/errors), CSV e-statement export
- Lender: portfolio search/filter, SME detail, monthly history, metrics, statement download
- Loading / empty / error / toast UI states
- Accessible semantic HTML and responsive layout

## FastAPI routes

`src/api.js` automatically appends `/api` to `VITE_API_URL` and targets:

### Auth
- `POST /auth/register` — `{ email, password, role, full_name?, business_name? }`
- `POST /auth/login` — `{ email, password }` → `{ access_token, token_type, user }`
- `GET /auth/me` — current user (Bearer)

### SME
- `GET /dashboard/sme`
- `POST /credit/score`
- `GET /credit/history/monthly`
- `GET /transactions`
- `POST /transactions/import` — multipart `file`
- `GET /transactions/template`
- `GET /transactions/export/estatement`

### Lender
- `GET /lender/portfolio?q&risk&min_score&max_score`
- `GET /lender/sme/{id}`
- `GET /lender/sme/{id}/transactions`
- `GET /lender/sme/{id}/statement`

Responses are normalized flexibly (`items`, `data`, `transactions`, etc.) so minor backend field naming differences still render.

## Project structure

```
Frontend/
├── index.html
├── package.json
├── vite.config.js
├── .env.example
├── README.md
└── src/
    ├── main.js          # Boot, hash router, logout wiring
    ├── api.js           # FastAPI client
    ├── session.js       # Token/user state
    ├── inactivity.js    # 30s idle auto-logout
    ├── ui.js            # Shell, toasts, chart helpers
    ├── utils.js         # Formatting & safe DOM helpers
    ├── styles.css
    └── pages/
        ├── auth.js
        ├── sme.js
        └── lender.js
```

## Security notes

- User-facing strings are inserted via `textContent` / `escapeHtml` — avoid raw `innerHTML` for API data where values are interpolated into templates (templates escape with `escapeHtml`).
- Tokens live in `sessionStorage` (cleared on tab close and logout).
- No hardcoded “successful” score/financing values — all metrics come from the API.

## Deployment

```bash
npm run build
```

Serve the `dist/` folder behind any static host. Configure `VITE_API_URL` at **build time** to the public API origin, and ensure the FastAPI CORS policy allows the frontend origin.
