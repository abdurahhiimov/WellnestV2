"""Local web server: dashboard, Oura OAuth, sync APIs."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from backend.dashboard_export import export_dashboard_html
from backend.integrations import integrations_path, oura_configured
from backend.oura import exchange_code, get_oauth_url, is_connected, new_oauth_state, sync_oura
from backend.paths import REPO_ROOT, health_root
from backend.wearables import import_health_auto_export_folder

app = FastAPI(title="Wellnest Local Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_oauth_states: set[str] = set()


def _health_dashboard() -> Path:
    return health_root() / "dashboard.html"


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "wellnest",
        "version": 3,
        "features": ["snapshot", "explain", "icons", "visit_pack", "weekly_brief", "checkins", "consilium", "symptom_survey", "claude_consilium"],
    }


def _frontend_dist() -> Path:
    return REPO_ROOT / "frontend" / "dist"


@app.get("/")
def root():
    if (_frontend_dist() / "index.html").exists():
        return RedirectResponse("/app/")
    return RedirectResponse("/dashboard")


def _serve_spa(path: str = ""):
    """New React dashboard (frontend/dist). SPA fallback to index.html."""
    dist = _frontend_dist()
    index = dist / "index.html"
    if not index.exists():
        return RedirectResponse("/dashboard?legacy=1")
    if path:
        candidate = (dist / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)
    return FileResponse(index, headers={"Cache-Control": "no-store"})


@app.get("/app")
@app.get("/app/")
@app.get("/app/{path:path}")
def app_spa(path: str = ""):
    return _serve_spa(path)


@app.get("/dashboard")
def dashboard(legacy: bool = False):
    if not legacy and (_frontend_dist() / "index.html").exists():
        return RedirectResponse("/app/")
    export_dashboard_html()
    path = _health_dashboard()
    if not path.exists():
        return HTMLResponse("<h1>Run: python scripts/init_db.py</h1>", status_code=404)
    return FileResponse(path, headers={"Cache-Control": "no-store"})


@app.get("/vendor/{path:path}")
def vendor(path: str):
    src = REPO_ROOT / "dashboard" / "vendor" / path
    if src.exists():
        return FileResponse(src)
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/icons/{path:path}")
def icons(path: str):
    for base in (health_root() / "icons", REPO_ROOT / "dashboard" / "icons"):
        src = base / path
        if src.exists():
            return FileResponse(src)
    return JSONResponse({"error": "not found"}, status_code=404)


@app.post("/api/consilium/request-claude")
def api_consilium_request_claude():
    from backend.consilium_ai import request_claude_consilium

    return request_claude_consilium()


@app.get("/api/engine/status")
def api_engine_status():
    from backend.llm_engine import engine_status

    return JSONResponse(engine_status(), headers={"Cache-Control": "no-store"})


@app.post("/api/engine/configure")
async def api_engine_configure(request: Request):
    from backend.llm_engine import save_engine_config

    body = await request.json()
    return save_engine_config(
        api_key=body.get("api_key"),
        model=body.get("model"),
    )


@app.post("/api/consilium/generate")
async def api_consilium_generate(request: Request):
    """Autonomous: start consilium generation in the background, return at once."""
    from backend.llm_engine import engine_config, start_consilium_job

    if not engine_config()["enabled"]:
        return JSONResponse(
            {"ok": False, "error": "engine_not_configured"},
            status_code=400,
            headers={"Cache-Control": "no-store"},
        )
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    specialist_ids = body.get("specialist_ids") or None
    job = start_consilium_job(specialist_ids=specialist_ids)
    return JSONResponse({"ok": True, "job": job}, headers={"Cache-Control": "no-store"})


@app.get("/api/consilium/progress")
def api_consilium_progress():
    """Live progress of the background consilium job (poll every ~2s)."""
    from backend.llm_engine import consilium_job_status

    return JSONResponse(consilium_job_status(), headers={"Cache-Control": "no-store"})


@app.post("/api/consilium/cancel")
def api_consilium_cancel():
    """Stop a running consilium job (partial results are discarded)."""
    from backend.llm_engine import cancel_consilium_job

    return JSONResponse({"ok": True, "job": cancel_consilium_job()}, headers={"Cache-Control": "no-store"})


@app.get("/api/consilium/status")
def api_consilium_status():
    from backend.consilium_ai import consilium_status

    data = consilium_status()
    # Don't send full report in status if huge - dashboard uses snapshot; include summary
    if data.get("claude_report"):
        data = {**data, "claude_report": data["claude_report"]}
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


@app.get("/reports/consilium-ai")
def consilium_ai_page():
    from backend.consilium_ai import load_claude_consilium
    from backend.consilium import build_consilium_html_from_data

    ai = load_claude_consilium()
    if not ai:
        return RedirectResponse("/reports/consilium")
    return HTMLResponse(
        build_consilium_html_from_data(ai, footer_note="Claude · локально через MCP"),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/consilium")
def consilium_short():
    return RedirectResponse("/reports/consilium")


@app.get("/reports/consilium")
def consilium_page():
    from backend.consilium import build_consilium_html, export_consilium

    export_consilium()
    return HTMLResponse(build_consilium_html(), headers={"Cache-Control": "no-store"})


@app.post("/api/consilium")
def api_consilium():
    from backend.consilium import export_consilium

    path = export_consilium()
    return {"ok": True, "path": str(path), "url": "/reports/consilium"}


@app.get("/api/symptom-survey/config")
def symptom_survey_config():
    from backend.symptom_survey import survey_config

    return survey_config()


@app.post("/api/symptom-question")
async def api_symptom_question(request: Request):
    from backend.symptom_qa import request_symptom_question

    body = await request.json()
    question = str(body.get("question") or "")
    attachments = body.get("attachments") or []
    base_q = question.strip()
    # Allow asking with just an attachment (no typed text).
    if not base_q and attachments:
        base_q = "Please review the attached file(s) and explain in plain language."
    pending = request_symptom_question(base_q)

    from backend.llm_engine import engine_config, start_symptom_job

    if engine_config()["enabled"] and base_q:
        job = start_symptom_job(base_q, attachments=attachments, mode="quick")
        return JSONResponse(
            {"ok": True, "mode": "background", "job": job},
            headers={"Cache-Control": "no-store"},
        )
    return JSONResponse({"ok": True, "mode": "pending", **pending}, headers={"Cache-Control": "no-store"})


@app.get("/api/symptom-question/progress")
def api_symptom_question_progress():
    from backend.llm_engine import symptom_job_status

    return JSONResponse(symptom_job_status(), headers={"Cache-Control": "no-store"})


@app.get("/api/symptom-question/status")
def api_symptom_question_status():
    from backend.symptom_qa import symptom_qa_status

    return JSONResponse(symptom_qa_status(), headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------- profile / onboarding

@app.get("/api/profile")
def api_get_profile():
    from backend.profile_store import load_profile

    return JSONResponse(load_profile(), headers={"Cache-Control": "no-store"})


@app.get("/api/onboarding/status")
def api_onboarding_status():
    from backend.profile_store import is_onboarded

    return JSONResponse({"onboarding_complete": is_onboarded()}, headers={"Cache-Control": "no-store"})


@app.get("/api/specialist-catalog")
def api_specialist_catalog(lang: str = "en"):
    from backend.specialist_selector import localized_specialists

    return JSONResponse({"specialists": localized_specialists(lang)}, headers={"Cache-Control": "no-store"})


@app.post("/api/specialist-panel/suggest")
async def api_suggest_panel(request: Request):
    """Given a draft profile, return the recommended specialist panel (hybrid)."""
    from backend.specialist_selector import recommend_panel

    draft = await request.json()
    use_llm = bool(draft.pop("use_llm", True))
    return JSONResponse(recommend_panel(draft, use_llm=use_llm), headers={"Cache-Control": "no-store"})


@app.post("/api/profile")
async def api_save_profile(request: Request):
    """Onboarding submit / full profile save. Computes panel if none provided."""
    from backend.specialist_selector import recommend_panel
    from backend.profile_store import save_profile

    body = await request.json()
    if not body.get("specialist_panel"):
        body["specialist_panel"] = recommend_panel(body, use_llm=False)["panel"]
    body["onboarding_complete"] = bool(body.get("onboarding_complete", True))
    saved = save_profile(body)
    try:
        export_dashboard_html()
    except Exception:
        pass  # fresh install may not have a DB yet; dashboard renders on next refresh
    return JSONResponse(saved, headers={"Cache-Control": "no-store"})


@app.patch("/api/profile")
async def api_patch_profile(request: Request):
    from backend.profile_store import update_profile

    patch = await request.json()
    saved = update_profile(patch)
    export_dashboard_html()
    return JSONResponse(saved, headers={"Cache-Control": "no-store"})


@app.post("/api/tasks/{task_id}/status")
async def api_task_status(task_id: int, request: Request):
    from backend import health_db

    body = await request.json()
    status = str(body.get("status") or "")
    result = health_db.update_task_status(task_id, status)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400, headers={"Cache-Control": "no-store"})
    export_dashboard_html()
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


@app.delete("/api/tasks/{task_id}")
def api_task_delete(task_id: int):
    from backend import health_db

    result = health_db.delete_task(task_id)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400, headers={"Cache-Control": "no-store"})
    export_dashboard_html()
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


@app.post("/api/uploads")
async def api_uploads(files: list[UploadFile] = File(...)):
    """Save attachments to HEALTH/uploads/ for symptom/consilium context."""
    root = health_root()
    dest_dir = root / "uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: list[dict[str, str]] = []
    for f in files:
        name = Path(f.filename or "file").name.replace("..", "_")
        if name.startswith("."):
            continue
        target = dest_dir / name
        # Avoid overwrite: add suffix if exists
        if target.exists():
            stem, suffix = target.stem, target.suffix
            n = 2
            while target.exists():
                target = dest_dir / f"{stem}_{n}{suffix}"
                n += 1
        with target.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append({"name": target.name, "path": f"uploads/{target.name}"})
    return JSONResponse({"ok": True, "files": saved}, headers={"Cache-Control": "no-store"})


@app.post("/api/symptom-answer/save-memory")
async def api_symptom_save_memory(request: Request):
    from backend.clinical_history import append_symptom_memory
    from backend.symptom_qa import symptom_qa_status

    body = await request.json()
    st = symptom_qa_status()
    answer = st.get("answer") or body.get("answer") or {}
    question = body.get("question") or answer.get("question") or st.get("pending_question") or ""
    attachments = body.get("attachments") or answer.get("attachments") or []
    return JSONResponse(
        append_symptom_memory(question, answer, attachments),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/symptom-answer/report")
async def api_symptom_report(request: Request):
    from backend.symptom_qa import symptom_qa_status
    from backend.symptom_reports import export_symptom_report

    body = await request.json()
    st = symptom_qa_status()
    answer = st.get("answer") or body.get("answer") or {}
    question = body.get("question") or answer.get("question") or ""
    attachments = body.get("attachments") or []
    lang = str(body.get("lang") or "ru")
    return JSONResponse(
        export_symptom_report(question, answer, attachments, lang=lang),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/symptom-consilium")
async def api_symptom_consilium(request: Request):
    """Symptom + optional files → mini consilium-style answer via LLM engine (background)."""
    from backend.llm_engine import engine_config, start_symptom_job

    body = await request.json()
    question = str(body.get("question") or "").strip()
    attachments = body.get("attachments") or []
    if not question:
        return JSONResponse({"ok": False, "error": "question_required"}, status_code=400)

    if not engine_config()["enabled"]:
        return JSONResponse({"ok": False, "error": "engine_not_configured"}, status_code=400)

    job = start_symptom_job(
        question,
        attachments=attachments,
        mode="symptom_consilium",
        also_full_consilium=bool(body.get("also_full_consilium")),
    )
    return JSONResponse(
        {"ok": True, "mode": "background", "job": job},
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/labs/extract-from-file")
async def api_labs_extract(request: Request):
    """OCR/parse an uploaded file and extract structured lab rows via LLM."""
    from backend.attachments import extract_one
    from backend.llm_engine import engine_config, extract_labs_from_text

    if not engine_config()["enabled"]:
        return JSONResponse({"ok": False, "error": "engine_not_configured"}, status_code=400)

    body = await request.json()
    path = str(body.get("path") or "").strip()
    if not path:
        return JSONResponse({"ok": False, "error": "path_required"}, status_code=400)

    text = extract_one(path)
    if not text:
        return JSONResponse({"ok": False, "error": "could_not_read_file"}, status_code=422)

    try:
        from backend.paths import active_profile_id
        result = extract_labs_from_text(text, profile_id=active_profile_id())
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

    return JSONResponse(result, headers={"Cache-Control": "no-store"})


@app.post("/api/labs/explain")
async def api_labs_explain(request: Request):
    """Generate AI explanation for a single lab result."""
    from backend.llm_engine import explain_lab_result
    from backend.paths import active_profile_id

    body = await request.json()
    try:
        result = explain_lab_result(
            test_name=str(body.get("test_name") or body.get("test_code") or ""),
            value=body.get("value"),
            value_text=body.get("value_text"),
            unit=str(body.get("unit") or ""),
            flag=body.get("flag"),
            ref_low=body.get("ref_low"),
            ref_high=body.get("ref_high"),
            profile_id=active_profile_id(),
        )
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


@app.post("/api/labs/add")
async def api_labs_add(request: Request):
    """Manually add a single lab result to the database."""
    from backend import health_db

    body = await request.json()
    test_name = str(body.get("test_name") or "").strip()
    if not test_name:
        return JSONResponse({"ok": False, "error": "test_name_required"}, status_code=400)
    sample_date = str(body.get("sample_date") or "").strip()
    if not sample_date:
        return JSONResponse({"ok": False, "error": "date_required"}, status_code=400)

    def _float(key: str) -> float | None:
        v = body.get(key)
        try:
            return float(v) if v not in (None, "", "—") else None
        except (TypeError, ValueError):
            return None

    result = health_db.add_lab_result(
        test_name=test_name,
        value=_float("value"),
        unit=str(body.get("unit") or ""),
        sample_date=sample_date,
        ref_low=_float("ref_low"),
        ref_high=_float("ref_high"),
        value_text=str(body.get("value_text") or "") or None,
        source_file="manual",
    )
    if result.get("ok"):
        export_dashboard_html()
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


@app.post("/api/symptom-survey")
async def api_symptom_survey(request: Request):
    from backend.dashboard_export import export_dashboard_html
    from backend.symptom_survey import save_symptom_survey

    body = await request.json()
    result = save_symptom_survey(
        mood=int(body.get("mood", 3)),
        sleep=str(body.get("sleep", "ok")),
        symptoms=body.get("symptoms") or [],
        notes=str(body.get("notes") or ""),
    )
    export_dashboard_html()
    return result


@app.get("/visit-pack")
def visit_pack_short():
    return RedirectResponse("/reports/visit-pack")


@app.get("/reports/visit-pack")
def visit_pack_page():
    from backend.visit_pack import build_visit_pack_html, export_visit_pack

    export_visit_pack()
    return HTMLResponse(build_visit_pack_html(), headers={"Cache-Control": "no-store"})


@app.get("/api/reports/download/{filename}")
def api_download_report(filename: str):
    """Download report file (HTML — open in browser → Print → Save as PDF)."""
    safe = Path(filename).name
    path = health_root() / "reports" / safe
    if not path.exists():
        return JSONResponse({"error": "not_found"}, status_code=404)
    media = "application/pdf" if safe.endswith(".pdf") else "text/html; charset=utf-8"
    return FileResponse(
        path,
        media_type=media,
        filename=safe,
        headers={"Content-Disposition": f'attachment; filename="{safe}"'},
    )


@app.get("/reports/{filename}")
def reports_file(filename: str):
    path = health_root() / "reports" / filename
    if path.exists():
        return FileResponse(path, headers={"Cache-Control": "no-store"})
    return JSONResponse({"error": "not found"}, status_code=404)


@app.post("/api/visit-pack")
async def api_visit_pack(request: Request):
    from backend.visit_pack import export_visit_pack

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    lang = str((body or {}).get("lang") or "ru")
    sections = (body or {}).get("sections") or None
    path = export_visit_pack(lang=lang, sections=sections)
    suffix = "" if lang == "ru" else f"_{lang}"
    return {"ok": True, "path": str(path), "url": f"/reports/visit-pack", "filename": f"visit_pack_latest{suffix}.html"}


@app.get("/api/snapshot")
def api_snapshot():
    from backend.health_db import dashboard_snapshot
    from datetime import datetime

    data = dashboard_snapshot()
    data["generated_at"] = datetime.now().isoformat(timespec="seconds")
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


@app.post("/api/refresh")
def api_refresh():
    import_health_auto_export_folder()
    if is_connected():
        sync_oura()
    from backend.visit_pack import export_visit_pack

    path = export_dashboard_html()
    export_visit_pack()
    return {"ok": True, "dashboard": str(path)}


@app.post("/api/sync/apple-health")
def sync_apple_health():
    result = import_health_auto_export_folder()
    export_dashboard_html()
    return result


@app.post("/api/sync/oura")
def sync_oura_api():
    result = sync_oura()
    export_dashboard_html()
    return result


@app.get("/api/status")
def api_status():
    from backend.wearables import get_integration_status

    return get_integration_status()


@app.get("/oura/connect")
def oura_connect():
    if not oura_configured():
        return HTMLResponse(
            _oura_setup_html(missing_config=True),
            status_code=200,
        )
    state = new_oauth_state()
    _oauth_states.add(state)
    return RedirectResponse(get_oauth_url(state))


@app.get("/oura/callback")
def oura_callback(code: str = "", state: str = "", error: str = ""):
    if error:
        return HTMLResponse(f"<h2>Oura: {error}</h2><p><a href='/dashboard'>Back</a></p>")
    if state not in _oauth_states:
        return HTMLResponse("<h2>Invalid session. <a href='/oura/connect'>Try again</a></h2>")
    _oauth_states.discard(state)
    try:
        exchange_code(code)
        sync_oura()
        export_dashboard_html()
        return HTMLResponse(
            "<html><body style='font-family:system-ui;background:#0a0e14;color:#e2e8f0;"
            "display:flex;align-items:center;justify-content:center;height:100vh'>"
            "<div style='text-align:center'>"
            "<h1>✓ Oura Ring connected</h1>"
            "<p>Data synced. You can close this tab.</p>"
            "<a href='/dashboard' style='color:#2dd4bf'>Open dashboard →</a>"
            "</div></body></html>"
        )
    except Exception as exc:
        return HTMLResponse(f"<h2>Error: {exc}</h2><p><a href='/oura/connect'>Retry</a></p>")


@app.get("/oura/setup")
def oura_setup_page():
    return HTMLResponse(_oura_setup_html(missing_config=not oura_configured()))


def _oura_setup_html(missing_config: bool) -> str:
    cfg_hint = str(integrations_path())
    if missing_config:
        body = f"""
        <h1>One-time setup (2 min)</h1>
        <ol>
          <li>Create free app at <a href="https://cloud.ouraring.com/oauth/developer">Oura Developer</a></li>
          <li>Redirect URI: <code>http://127.0.0.1:8787/oura/callback</code></li>
          <li>Copy Client ID + Secret to <code>{cfg_hint}</code></li>
          <li>Reload this page and click Connect</li>
        </ol>
        """
        btn = ""
    else:
        body = "<p>Oura API is free. Click to sign in with your Oura account.</p>"
        btn = '<a href="/oura/connect" class="btn">Connect Oura Ring</a>'
    return f"""<!DOCTYPE html><html><head><meta charset=utf-8>
    <title>Oura — Wellnest</title>
    <style>body{{font-family:system-ui;background:#0a0e14;color:#e2e8f0;padding:2rem;max-width:560px;margin:auto}}
    a{{color:#2dd4bf}} .btn{{display:inline-block;margin-top:1rem;padding:12px 24px;background:linear-gradient(135deg,#6366f1,#2dd4bf);
    color:#0a0e14;text-decoration:none;border-radius:12px;font-weight:600}}</style></head>
    <body>{body}{btn}<p><a href="/dashboard">← Dashboard</a></p></body></html>"""


def _copy_tree_safe(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    try:
        shutil.copytree(src, dest, dirs_exist_ok=True)
    except OSError as e:
        print(f"  Warning: could not copy {src.name} → {dest} ({e})")


def copy_vendor_to_health():
    root = health_root()
    _copy_tree_safe(REPO_ROOT / "dashboard" / "vendor", root / "vendor")
    _copy_tree_safe(REPO_ROOT / "dashboard" / "icons", root / "icons")


def main():
    copy_vendor_to_health()
    import uvicorn

    host, port = "127.0.0.1", 8787
    print("\n  Wellnest server")
    print(f"  → http://{host}:{port}/app/\n")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
