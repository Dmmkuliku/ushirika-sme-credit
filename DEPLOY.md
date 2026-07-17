# Deploy Ushirika to Render (API) + Vercel (Frontend)

## Local development (important)

A stuck old API on port **8000** causes **"Not Found"** on every edit. Prefer:

```powershell
# Terminal 1 — backend (defaults to 8001 if 8000 is busy)
cd "C:\Users\USER\OneDrive\Desktop\SME vs LENDER system"
.\scripts\start_backend.ps1

# Terminal 2 — frontend (Vite proxies /api → http://127.0.0.1:8001)
.\scripts\start_frontend.ps1
```

Open **http://localhost:5173**. Edits/deletes require API version **1.1.0+**
(check `http://127.0.0.1:8001/api/health` → `"version":"1.1.0"`).

If something still says Not Found, you are still talking to the old process on :8000.
Restart both terminals using the scripts above.

## 1. Deploy backend on Render

1. Push this repo to GitHub.
2. Go to https://dashboard.render.com → New → Blueprint.
3. Connect the repo and apply `render.yaml` from the project root.
4. Set `CORS_ORIGINS` to your Vercel URL when you have it.
5. Note the public API URL, e.g. `https://ushirika-api.onrender.com`.
6. In the Render shell, seed accounts:

```bash
python scripts/restore_admin.py
python scripts/seed_data.py
```

Admin: ID `20031001121160000228` / PIN `1234`.

## 2. Deploy frontend on Vercel

1. Import the repo on https://vercel.com
2. Root Directory: `Frontend`
3. Env var: `VITE_API_URL` = `https://ushirika-api.onrender.com`
4. Deploy — opening the Vercel link uses Render automatically.

## 3. How API switching works

1. `VITE_API_URL` (Vercel) → Render backend
2. Vite local (empty `VITE_API_URL`) → `/api` proxy to local backend
3. Else → localhost:8000/api