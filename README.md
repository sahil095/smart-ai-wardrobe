# Wardrobe AI

A mobile-first personal stylist that organizes the clothes you own and answers
**“What should I wear today?”** Every suggestion is built only from your
uploaded items. The AI cannot invent garments — returned item IDs are checked
against your wardrobe before anything is shown.

Weather (Open-Meteo), occasion, your profile, laundry status, recently worn
pieces, and saved looks all feed the generator. You get **two** outfit options
per run.

## What you can do

- **Accounts:** each person signs in with a username and password. Usernames are unique. A closet is visible only to the account that owns it. The first time you open the app after this change, set a login on the existing wardrobe before you share the link. Friends use **Create account** and start with an empty closet.
- **Wardrobe:** add items with photos and tags; filter by category, season,
  laundry, favorites, and category-specific attributes (e.g. shoe sole/height).
  Only **Clean** items are eligible for generate.
- **Retail-style photos:** with Cloudinary, uploads are background-removed and
  padded onto a shared canvas. The original file is kept. If a remote image is
  later deleted, the UI shows a placeholder instead of a broken icon.
- **Generate:** weather (auto / city / manual), occasion, dress code, comfort
  vs style. Optional must-include item.
- **Complete the look:** from a wardrobe card or item edit, generate two
  outfits that **must** include that piece (it has to be Clean).
- **Save and wear:** star a look to reuse it; **I wore this** writes a wear
  log and `last_worn_at` (laundry does **not** change unless you confirm
  “send to laundry”).
- **History:** Generated | Saved | Worn. Delete one session, or **Delete all**
  on Generated or Worn. Clearing Worn also resets last-worn dates so old
  pieces stop steering generate.
- **Gaps:** `/gaps` names missing staples from your tags (category, color,
  season, occasion). Cached 24 hours unless the wardrobe changes. No shop links.
- **Stylist chat:** ask what to wear. The model can look up your closet, weather, wear log, saved looks, and gaps, then generate owned outfits. Say a lasting preference (“no skinny jeans”) and it is remembered.
- **Style ideas:** from a wardrobe item, see similar outfit photos (Pexels, if configured) plus a Pinterest search. Those pictures are not your garment and are not for sale.
- **Style memory:** stated preferences show on Profile (delete any time) and are included the next time outfits are generated.
- **PWA:** add to a phone home screen. Bottom tabs: Home, Wardrobe, Add, History, Profile. The stylist is opened from Home.

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic
- **Database:** SQLite locally; Postgres (Neon) in production; MySQL-compatible models
- **AI:** Groq LLM (rule-based fallback if no key is set)
- **Weather:** Open-Meteo (no API key)
- **Images:** Cloudinary if configured, otherwise `app/static/uploads`
- **Frontend:** HTML + Bootstrap 5 + Alpine.js (`app/static/css/app.css`)

## Project structure

```
app/
  api/         # users, wardrobe, weather, outfits, meta, attributes
  models/      # User, WardrobeItem, history, saved outfits, wear events, gaps
  schemas/     # Pydantic schemas
  services/    # images, weather, Groq, outfit engine, wear log, gaps
  database/    # engine / session / schema ensure
  static/      # css, js, icons, local uploads
  templates/   # mobile pages
scripts/       # demo seeder, display-URL backfill
```

## Clone and local setup

You need **Python 3.11+**. On Windows, Anaconda Prompt or Command Prompt is
fine.

```bash
git clone https://github.com/<you>/wardrobe-ai.git
cd wardrobe-ai
```

Create an environment (pick one):

```bat
conda create -n wardrobe python=3.11 -y
conda activate wardrobe
```

```bat
python -m venv .venv
.venv\Scripts\activate
```

On macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`.

```bat
pip install -r requirements.txt
copy .env.example .env
```

On macOS/Linux: `cp .env.example .env`.

Edit `.env` (AI key and, if you want, Neon — see below). The project `.env`
wins over a leftover Windows User/System `GROQ_API_KEY`. **Restart the server**
after any `.env` change.

Optional demo data:

```bat
python -m scripts.seed_demo
```

```bat
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000**. On a phone on the same network:
`http://<your-pc-ip>:8000`.

- API docs: **http://localhost:8000/docs**
- Health / flags: **http://localhost:8000/health** (`groq_enabled`, `cloudinary_enabled`)

## AI models (Groq)

Outfit generate, attribute schemas, and wardrobe gaps all call **Groq**.
There is no separate OpenAI client. The default model id
`openai/gpt-oss-120b` is an **OpenAI-named model hosted on Groq**, not the
ChatGPT API.

1. Create an account at [console.groq.com](https://console.groq.com).
2. Create an API key.
3. In `.env`:

   ```
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=openai/gpt-oss-120b
   ```

4. To use another current Groq model, set `GROQ_MODEL` to the id from
   [Groq’s model list](https://console.groq.com/docs/models). Examples that
   have been used with this app:

   | `GROQ_MODEL` | Notes |
   | --- | --- |
   | `openai/gpt-oss-120b` | Default; stronger |
   | `openai/gpt-oss-20b` | Faster / cheaper on Groq |
   | Other Groq chat models | Must support JSON-object responses |

5. Leave `GROQ_API_KEY` empty to run the built-in rule-based stylist (no AI).

If generate says the key is missing, confirm `.env` is in the **project root**,
then restart uvicorn. A stale system `GROQ_API_KEY` no longer overrides `.env`.

## Database: SQLite, Neon, or MySQL

**Local default:** `DATABASE_URL=sqlite:///./wardrobe.db`. Tables are created
on first start. Fine for trying the app on one machine.

**Neon (Postgres)** — use this when you want the same data on phone + laptop,
or when you deploy (Render’s disk is wiped on every deploy).

1. Sign up at [neon.tech](https://neon.tech) (free tier is enough).
2. Create a project. Open **Dashboard → Connection details**.
3. Copy the **pooled** connection string (`-pooler` in the host). It looks like:

   ```
   postgresql://USER:PASSWORD@ep-xxx-pooler.REGION.aws.neon.tech/neondb?sslmode=require
   ```

4. Paste it into `.env` as `DATABASE_URL=...` (the `postgresql://` form is
   fine). The app rewrites it to `postgresql+psycopg://` automatically.
5. Restart uvicorn. Tables are created on boot. Your local SQLite file is
   **not** migrated — this is a new empty database unless you add items again.

Keep the Neon password private. If you rotate it, update `.env` and (for
production) the `DATABASE_URL` secret on Render.

**MySQL instead of SQLite / Neon:**

```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/wardrobe_ai
```

`PyMySQL` is already in `requirements.txt`. Tables are created on startup.

## How the AI stays honest

- Only **Clean** items are eligible.
- Recently worn items (last 7 days) are down-ranked; saved outfits may be
  reused if they still fit weather and occasion.
- Candidates are pre-filtered by weather and occasion when tags exist.
- Groq may only reference numeric IDs from that candidate list.
- Every ID is re-checked server-side. Unknown IDs are dropped.
- If Groq fails or returns nothing usable, the rule-based stylist builds the
  two looks instead.

## Configuration (`.env`)

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLite, Neon Postgres, or MySQL | `sqlite:///./wardrobe.db` |
| `GROQ_API_KEY` | Groq API key (enables AI) | *(empty → rule-based)* |
| `GROQ_MODEL` | Groq model id | `openai/gpt-oss-120b` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud (optional) | *(empty → local uploads)* |
| `CLOUDINARY_API_KEY` | Cloudinary key | |
| `CLOUDINARY_API_SECRET` | Cloudinary secret | |
| `OUTFIT_COUNT` | Outfits per generate | `2` |
| `STANDARDIZE_IMAGES` | Background-remove + pad (needs Cloudinary AI Background Removal) | `true` |
| `IMAGE_BG_COLOR` | Standardized background (hex, no `#`) | `F5F6F8` |
| `IMAGE_ASPECT` | Standardized aspect ratio | `1:1` |
| `GAP_CACHE_HOURS` | Reuse a gaps analysis this long | `24` |
| `PEXELS_API_KEY` | In-app style-inspiration photos (optional) | *(empty → Pinterest link only)* |
| `SECRET_KEY` | Signs the login cookie | `wardrobe-ai-dev-secret` locally; set a long random value when you share the app |

**Cloudinary (optional, recommended for phones / hosting):** enable
**AI Background Removal** on the account. Set `STANDARDIZE_IMAGES=false` to
keep originals only. Older items can be backfilled with
`python -m scripts.backfill_display`.

## Deploy (Render + Neon + Cloudinary)

Free hosts have an **ephemeral filesystem**. Keep data in **Neon** and images
in **Cloudinary**. Local SQLite and `static/uploads` are for development.

1. Create a Neon database (see above) and copy the **pooled** URL.
2. Push the repo to GitHub (`.env`, `*.db`, and local uploads are gitignored).
3. At [render.com](https://render.com) → **New + → Blueprint**, connect the
   repo. `render.yaml` defines the web service.
4. Set secrets: `DATABASE_URL` (Neon), `GROQ_API_KEY`, and the three
   `CLOUDINARY_*` values. `GROQ_MODEL`, `OUTFIT_COUNT`, and `PYTHON_VERSION`
   are already set in the blueprint.
5. Deploy. Tables are created on first boot.
6. Open your Render URL. `/health` should show `groq_enabled` and
   `cloudinary_enabled` as `true` if those keys were set.

### Hosting notes

- **HTTPS** on Render is required for auto weather via the device location.
  City / Manual weather work without it.
- **Cold start:** the free web tier sleeps after ~15 minutes idle; the first
  request can take 30–50s.
- Items uploaded only as `/static/uploads/...` will not exist on Render —
  re-upload those photos after Cloudinary is configured.
- There is **no login** yet. Anyone with the URL can use the app.
