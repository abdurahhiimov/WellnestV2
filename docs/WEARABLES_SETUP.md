# Wearables & UI v2 setup

## 1. Start local server (Oura button + sync)

Double-click:
```
ZamiraHealth/scripts/start_zamira.command
```

Or:
```bash
cd ~/ZamiraHealth && source .venv/bin/activate && pip install -r requirements.txt
python scripts/start_server.py
```

Open: **http://127.0.0.1:8787/dashboard**

Bookmark this — Oura OAuth and sync buttons need the server running.

Static file also works: `~/Desktop/HEALTH/dashboard.html` (Cmd+R to refresh)

---

## 2. Health Auto Export (iPhone → Mac)

1. Install [Health Auto Export](https://apps.apple.com/us/app/health-auto-export-json-csv/id1115567069) on iPhone
2. Enable auto-export to **iCloud Drive** or Mac folder
3. Point exports to sync into:
   ```
   ~/Desktop/HEALTH/health_auto_export/
   ```
4. In dashboard: **↻ Apple Health** or tab **Подключения → Синхронизировать**

Metrics imported: steps, resting HR, HRV, sleep, SpO2, weight, BP

---

## 3. Oura Ring (when she gets it — free API)

**One-time (you):**
1. Create app: https://cloud.ouraring.com/oauth/developer
2. Redirect URI: `http://127.0.0.1:8787/oura/callback`
3. Copy credentials to:
   ```
   ~/Desktop/HEALTH/data/integrations.json
   ```
   (copy from `profiles/zamira/integrations.example.json`)

**For Zamira:**
1. Start `start_zamira.command`
2. Dashboard → **Подключения** → **Подключить Oura Ring**
3. Sign in to Oura → done

No monthly API fee. Oura allows 10 users per dev app (family is fine).

---

## 4. UI

- Dark theme inspired by Oura / Apple Health
- System status cards (thyroid, pituitary, menopause, blood, nutrition)
- Lab sparkline charts (prolactin, TSH, estradiol, vitamin D, hemoglobin)
- Wearable charts when data exists
