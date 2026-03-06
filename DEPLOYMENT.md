# Step-by-step: Deploy to Vercel

You need **two Vercel projects**: one for the API (backend) and one for the app (frontend). Deploy the backend first so you have its URL for the frontend.

---

## Part 1: Deploy the backend (API)

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

| What | Vercel project | Root Directory | Main env vars |
|------|----------------|-----------------|----------------|
| **Backend** | e.g. `slai-api` | (empty) | `GEMINI_API_KEY`, `AUTOCOMPLETE_AUTH_TOKEN`, Supabase & admin vars |
| **Frontend** | e.g. `slai-app` | `frontend` | `NEXT_PUBLIC_API_URL` = backend URL |

If you change the backend URL later, update `NEXT_PUBLIC_API_URL` in the frontend project and redeploy the frontend.
