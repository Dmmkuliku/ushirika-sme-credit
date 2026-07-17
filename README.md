# Ushirika — SME vs Lender Credit Risk System

Automated ecosystem banking prototype for Tanzania SMEs:
FastAPI + ML credit scoring backend, Vite frontend.

## Local run

See `DEPLOY.md` and:

```powershell
.\scripts\start_backend.ps1
.\scripts\start_frontend.ps1
```

Open http://localhost:5173

## Demo logins

| Role | ID | PIN |
|------|----|-----|
| Admin | `20031001121160000228` | `1234` |
| Lender | `EMP001` | `1234` |
| SME | `19900101123456789012` | `1234` |

## Deploy

- Backend: Render (`render.yaml`)
- Frontend: Vercel (`Frontend/vercel.json`) — set `VITE_API_URL` to the Render URL
