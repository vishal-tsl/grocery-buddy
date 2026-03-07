# Step-by-step: Deploy to Vercel (and backend elsewhere)

**Important:** The **frontend** works great on Vercel. The **backend** (FastAPI) often does **not** run correctly on Vercel: the build only installs dependencies and never creates a serverless function, so you get 404 and the browser shows "CORS error". **Use Railway or Render for the backend** (see below), then point the frontend at that URL.

---

## Part 1: Deploy the backend (API) — use Railway (recommended)

1. **Push your code to GitHub**  
   Repo: e.g. `vishal-tsl/grocery-buddy`.

2. **Go to [Railway](https://railway.app)**  
   Sign in with GitHub.

3. **New project**  
   **New Project** → **Deploy from GitHub repo** → select `grocery-buddy`.

4. **Configure the service**
   - **Root Directory:** leave **empty** (repo root).
   - **Build Command:** (leave default or) `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
     (Railway sets `PORT`; the repo also has a `Procfile` so this may be auto-detected.)
   - **Environment variables:** Add the same as in your local `.env`:
     - `GEMINI_API_KEY`, `AUTOCOMPLETE_AUTH_TOKEN`
     - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`
     - `ADMIN_ALLOWED_EMAIL`, `ADMIN_PANEL_PASSWORD`, `TRACKING_ENABLED` (optional)

5. **Deploy**  
   Railway builds and runs the app. Open **Settings** → **Networking** → **Generate Domain**. You’ll get a URL like `https://grocery-buddy-production-xxxx.up.railway.app`.

6. **Test the backend**  
   Open `https://your-app.up.railway.app/health` in the browser. You should see `{"status":"healthy",...}`. Use this URL as the backend URL for the frontend.

**Alternative: Render (Blueprint)**  
The repo includes a **`render.yaml`** so you can deploy the backend in one go:

1. Go to [render.com](https://render.com) and sign in with GitHub.
2. **New** → **Blueprint** → connect the `grocery-buddy` repo.
3. Render will read `render.yaml` and create a Web Service. Set the **env vars** in the dashboard (they’re listed in the blueprint; values are not in the repo):
   - `GEMINI_API_KEY`, `AUTOCOMPLETE_AUTH_TOKEN`
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`
   - `ADMIN_ALLOWED_EMAIL`, `ADMIN_PANEL_PASSWORD`
4. Deploy. Copy the service URL (e.g. `https://grocery-buddy-api.onrender.com`) and use it as `NEXT_PUBLIC_API_URL` for the frontend.

**Manual Render Web Service**  
**New** → **Web Service** → connect repo → **Root Directory** empty, **Build Command** `pip install -r requirements.txt`, **Start Command** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add env vars, then deploy.

---

## Part 1 (Vercel backend — often broken): Deploy the backend on Vercel

*Only try this if you specifically need the backend on Vercel. In many cases the build never creates a runnable function and you get 404/CORS.*

1. **Push your code to GitHub**  
   Make sure this repo is on GitHub (e.g. `your-username/slai`).

2. **Go to Vercel**  
   Open [vercel.com](https://vercel.com) and sign in (GitHub is easiest).

3. **New project**  
   Click **Add New…** → **Project**.

4. **Import the repo**  
   Select your `slai` (or whatever the repo is called) and click **Import**.

5. **Configure the backend project**
   - **Project Name:** e.g. `slai-api` (you’ll get `https://slai-api.vercel.app`).
   - **Root Directory:** click **Edit**, leave it **empty** (repo root). Confirm.
   - **Framework Preset:** set to **FastAPI** (required so Vercel runs `server.py` at the root).
   - Do **not** set Root Directory to `frontend`.

6. **Environment variables**  
   Expand **Environment Variables** and add (use the same values as in your local `.env`):

   | Name | Value | Notes |
   |------|--------|------|
   | `GEMINI_API_KEY` | your key | Required |
   | `AUTOCOMPLETE_AUTH_TOKEN` | your token | Required |
   | `SUPABASE_URL` | `https://cxeigafwlswgdfghehku.supabase.co` | If you use tracking |
   | `SUPABASE_SERVICE_ROLE_KEY` | your key | If you use tracking |
   | `SUPABASE_ANON_KEY` | your key | If you use tracking |
   | `ADMIN_ALLOWED_EMAIL` | `mekala.chowdary.in@avenuecode.com` | For /krsna admin |
   | `ADMIN_PANEL_PASSWORD` | your admin password | For /krsna admin |
   | `TRACKING_ENABLED` | `true` | Optional |

   Add them for **Production** (and optionally Preview if you want).

7. **Deploy**  
   Click **Deploy**. Wait until the build finishes.

8. **Copy the backend URL**  
   After deploy, open the project and copy the URL, e.g.  
   `https://slai-api.vercel.app`  
   You need this for the frontend. Test: open `https://slai-api.vercel.app/health` in the browser; you should see `{"status":"healthy",...}`.

---

## Part 2: Deploy the frontend (app)

1. **New project again**  
   In Vercel, click **Add New…** → **Project**.

2. **Import the same repo**  
   Select the same `slai` repo and click **Import**.

3. **Configure the frontend project**
   - **Project Name:** e.g. `slai-app` (you’ll get `https://slai-app.vercel.app`).
   - **Root Directory:** click **Edit** → set to **`frontend`** (only the Next.js app). Confirm.
   - **Framework Preset:** Vercel should detect Next.js.

4. **Environment variable**
   - Name: `NEXT_PUBLIC_API_URL`
   - Value: your **backend** URL from Part 1, e.g. `https://slai-api.vercel.app`  
   - No trailing slash.

5. **Deploy**  
   Click **Deploy**. Wait until the build finishes.

6. **Open the app**  
   Visit the frontend URL (e.g. `https://slai-app.vercel.app`). The app will call the backend you deployed in Part 1.

---

## Part 3: Admin panel (/krsna)

- **URL:** `https://slai-app.vercel.app/krsna` (or `/krsna/login` to sign in).
- **Login:** Use the email and password you set in `ADMIN_ALLOWED_EMAIL` and `ADMIN_PANEL_PASSWORD` on the **backend** project.

---

## Summary

| What | Where | Root / Start | Main env vars |
|------|--------|----------------|----------------|
| **Backend** | Railway (or Render) | repo root, `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | `GEMINI_API_KEY`, `AUTOCOMPLETE_AUTH_TOKEN`, Supabase & admin vars |
| **Frontend** | Vercel | `frontend` | `NEXT_PUBLIC_API_URL` = your Railway (or Render) backend URL |

If you change the backend URL later, update `NEXT_PUBLIC_API_URL` in the frontend project and redeploy the frontend.
