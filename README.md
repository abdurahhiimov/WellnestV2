# Zamira Health

Local-first health companion for macOS. Uses **Claude Desktop Pro** (no API key) via MCP.

## Workflow

1. **Develop & test** on your MacBook (`ACTIVE_PROFILE=zamira` or `aziz`).
2. **Deliver** a `.dmg` / install folder to Zamira with her profile only.
3. **Later**: add your profile (`profiles/aziz/`) — same app, different data.

## Deliver to MacBook (DMG)

Build an installable `.app` + `.dmg` with your logo:

```bash
bash scripts/build_dmg.sh
# → build/ZamiraHealth.dmg
```

Install: open DMG → drag **Zamira Health** to **Applications** → first launch: right-click → Open.

The app starts the local server and opens the dashboard in Safari (no Terminal).

**Note:** Claude Desktop + MCP setup (`python scripts/install_mcp.py`) is still one-time manual step — see `packaging/INSTALL_RU.txt`.

## Quick start (development)

```bash
# Install Python deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Init database + seed Zamira profile
python scripts/init_db.py --profile zamira

# Register MCP server with Claude Desktop (backs up existing config)
python scripts/install_mcp.py

# Restart Claude Desktop, then try:
# "Use zamira_health to show patient profile and pending tasks"
```

## Data locations

| Profile | Health folder (uploads) | Database |
|---------|-------------------------|----------|
| `zamira` | `~/Desktop/HEALTH/` | `~/Desktop/HEALTH/data/health.db` |
| `aziz` (later) | `~/Desktop/HEALTH-AZIZ/` | `~/Desktop/HEALTH-AZIZ/data/health.db` |

Override with env: `ZAMIRA_HEALTH_ROOT`, `ACTIVE_PROFILE`.

## Project layout

```
profiles/          # Per-person medical context (JSON)
backend/           # SQLite + MCP server
dashboard/         # Static dashboard (Phase 1)
scripts/           # init_db, install_mcp, import_xlsx
```

## MCP tools (Claude Desktop)

- `get_patient_profile` — diagnoses, meds, demographics
- `get_lab_results` — with freshness warnings
- `get_tasks` — pending follow-ups
- `get_medications` — current stack
- `get_problem_list` — P001–P006 style tracking
- `list_health_files` — files in HEALTH folder
- `import_chat_datapoints` — save labs/symptoms/tasks from chat attachments
- `list_inbox_files` / `process_inbox_files` — process dropped files in inbox/
- `get_upload_workflow_instructions` — schema for Claude when user attaches files
- `get_recent_datapoints` — audit log of imports
- `get_clinical_context` / `lookup_lab_reference` / `lookup_medication_reference` — local reference DB (RxNorm, guidelines)
- `get_reference_db_status` — verify reference.db is built

Run once (with network for RxNorm drug interactions):
```bash
python scripts/download_reference_db.py
```

## Disclaimer

Wellness and health-literacy tool only. Not a medical device. Always consult a physician.
