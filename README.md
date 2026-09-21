# Wardrobe AI

A lightweight, mobile-first web app that organizes your wardrobe and recommends
outfits **using only the clothing you actually own**. The AI never invents
garments — every suggestion is validated against your own uploaded items.

Answers one question: **"What should I wear today?"** based on weather,
occasion, your profile, your wardrobe, and laundry status.

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic
- **Database:** SQLite by default (zero-config); MySQL-compatible models
- **AI:** Groq LLM (with a built-in rule-based fallback if no key is set)
- **Weather:** Open-Meteo (free, no API key required)
- **Images:** Cloudinary if configured, otherwise local file storage
- **Frontend:** HTML5 + Bootstrap 5 + Alpine.js (mobile-first, bottom tab bar)

> Note: The PRD listed both Pico CSS and Bootstrap 5. To avoid the two
> frameworks fighting over the same base elements, the UI uses Bootstrap 5 plus
> a custom mobile-first stylesheet (`app/static/css/app.css`).

## Project structure

```
app/
  api/         # FastAPI routers (users, wardrobe, weather, outfits, meta)
  models/      # SQLAlchemy models (User, WardrobeItem, OutfitHistory)
  schemas/     # Pydantic schemas
  services/    # image storage, weather (Open-Meteo), Groq, outfit engine
  database/    # engine/session/init
  static/      # css, js, uploads (local image fallback)
  templates/   # Jinja2 mobile pages
scripts/       # optional demo seeder
uploads/       # (reserved)
docs/
```

## Setup (Anaconda Prompt or Command Prompt on Windows)

1. Open **Anaconda Prompt** (or Command Prompt) and go to the project:

   ```bat
   cd C:\Users\Sahil\Projects\wardrobe-ai
   ```

2. (Recommended) create and activate an environment:

   ```bat
   conda create -n wardrobe python=3.11 -y
   conda activate wardrobe
   ```

   *(Or with plain Python: `python -m venv .venv` then `.venv\Scripts\activate`)*

3. Install dependencies:

   ```bat
   pip install -r requirements.txt
   ```

4. Create your `.env` file from the example and add your Groq key:

   ```bat
   copy .env.example .env
   ```

   Then open `.env` and set `GROQ_API_KEY=...`. Everything else has working
   defaults (SQLite database, Open-Meteo weather, local image storage).

5. (Optional) seed a demo profile with clean items so you can test right away:

   ```bat
   python -m scripts.seed_demo
   ```

6. Run the app:

   ```bat
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. Open **http://localhost:8000** in your browser (use device toolbar / a phone
   on the same network at `http://<your-pc-ip>:8000` for the mobile experience).

- Interactive API docs: **http://localhost:8000/docs**
- Health / config check: **http://localhost:8000/health**

## How the AI stays honest

- Only items with **Laundry Status = Clean** are eligible.
- Items are pre-filtered by current weather + occasion.
- The clean candidate list (with numeric IDs) is sent to Groq, which may only
  reference those IDs.
- Every returned item ID is **re-validated** server-side against the candidate
  pool. Anything not in your wardrobe is discarded.
- If Groq is unavailable or returns nothing usable, a deterministic rule-based
  stylist builds the outfits instead.

## Using MySQL instead of SQLite

Set `DATABASE_URL` in `.env`, e.g.:

```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/wardrobe_ai
```

and install a driver: `pip install pymysql`. Tables are created automatically
on startup.

## Configuration reference (`.env`)

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | DB connection string | `sqlite:///./wardrobe.db` |
| `GROQ_API_KEY` | Groq API key (enables AI) | *(empty → rule-based)* |
| `GROQ_MODEL` | Groq model name | `openai/gpt-oss-120b` |
| `CLOUDINARY_*` | Cloudinary creds (optional) | *(empty → local uploads)* |
| `OUTFIT_COUNT` | Outfits per generation | `2` |

## Deploying (Render + Neon Postgres, free) — use it on your phone

Because free hosts have an **ephemeral filesystem**, this app is built to keep
all durable state off-disk: images in **Cloudinary** and data in a **managed
Postgres** database. Local SQLite/`static/uploads` are for development only.

### 1. Create the database (Neon)
1. Sign up at [neon.com](https://neon.com) (no credit card) and create a project.
2. Copy the **connection string** (looks like
   `postgresql://user:password@ep-xxx-pooler.<region>.aws.neon.tech/dbname?sslmode=require`).
   Prefer the **pooled** connection string.
   *(The app auto-rewrites `postgresql://` → `postgresql+psycopg://`, so paste it as-is.)*

### 2. Push this project to GitHub
```bat
cd /d C:\Users\Sahil\Projects\wardrobe-ai
git init
git add .
git commit -m "Wardrobe AI"
git branch -M main
git remote add origin https://github.com/<you>/wardrobe-ai.git
git push -u origin main
```
> `.env`, `*.db`, and local uploads are gitignored, so no secrets are pushed.

### 3. Deploy on Render
1. At [render.com](https://render.com) → **New + → Blueprint**, connect the repo.
   Render reads `render.yaml` and creates the web service automatically.
2. When prompted, fill the secret env vars: `DATABASE_URL` (the Neon string),
   `GROQ_API_KEY`, and the three `CLOUDINARY_*` values. (`GROQ_MODEL`,
   `OUTFIT_COUNT`, `PYTHON_VERSION` are preset.)
3. Deploy. Tables are created automatically on first boot.
4. Open `https://wardrobe-ai.onrender.com` (your URL) on your phone.
   `‎/health` should show `groq_enabled` and `cloudinary_enabled` = `true`.

### Notes
- **HTTPS is automatic** on Render — needed for the "auto weather via location"
  button on mobile. (City/Manual weather work without it.)
- **Cold start:** the free tier sleeps after ~15 min idle; the first request
  then takes ~30–50s to wake. Normal for free hosting.
- **Old local images:** any items added before Cloudinary was configured have
  `/static/uploads/...` URLs that won't exist on Render — re-upload those photos
  (easy from your phone).
- **No login yet:** the URL is public. Ask to add a site password when ready.
```
