# Wellnest

Local-first personal health dashboard for macOS. Tracks lab results, medications, symptoms, and wearable data — all stored privately on your own machine.

## What it is

- **React + Vite** frontend (dark-mode UI, Russian/English)
- **FastAPI** backend running locally on port 8787
- **SQLite** per-profile health database
- **120-test clinical reference DB** with authoritative ranges (CBC, CMP, lipids, thyroid, vitamins, hormones, coagulation, QuantiFERON TB, and more)
- Optional **AI explanations** via Claude API (bring your own API key)

No cloud. No accounts. Your data never leaves your laptop.

## macOS App (recommended)

Download `Wellnest.dmg`, drag to Applications, double-click.

On first launch it automatically:
1. Creates a Python virtual environment
2. Installs all dependencies
3. Builds the reference database
4. Opens the dashboard in your browser

Requires **Python 3.10+** (install via `brew install python@3.12` if not present) and **macOS 13+**.

## Development setup

```bash
# Clone
git clone https://github.com/abdurahhiimov/WellnestV2.git
cd WellnestV2

# Python backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-app.txt

# Build reference DB (offline, from bundled source JSON)
python scripts/init_db.py

# Start backend (port 8787)
python scripts/start_server.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev        # → http://localhost:5173
```

The Vite dev server proxies API calls to the FastAPI backend automatically.

## Build the DMG

```bash
bash scripts/build_dmg.sh
# → build/Wellnest.dmg
```

## Project layout

```
backend/          # FastAPI server, SQLite health DB, AI engine
frontend/         # React + Vite + shadcn/ui dashboard
data/
  reference/
    source/       # Curated JSON: labs, medications, guidelines
scripts/          # init_db, build_dmg, import_labs, etc.
profiles/
  default/        # Template profile (copy to get started)
packaging/        # macOS .app launcher and Info.plist
```

## AI features (optional)

Set `ANTHROPIC_API_KEY` in your environment to enable:
- Plain-language explanations for every lab result
- AI consilium (multi-specialist health review)
- Symptom Q&A

Without a key the app works fully — AI sections are hidden.

## Disclaimer

Wellness and health-literacy tool only. Not a medical device. Always consult a qualified physician.
