"""Import health datapoints from Claude chat attachments and inbox files."""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from backend import health_db
from backend.dashboard_export import export_dashboard_html
from backend.paths import health_root

ALLOWED_TYPES = {"lab", "symptom", "medication", "task", "note", "vital", "document", "checkin"}
INBOX_SUBFOLDER = "inbox"
UPLOADS_SUBFOLDER = "uploads"

DATAPOINTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS datapoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    event_date TEXT,
    title_ru TEXT,
    payload_json TEXT NOT NULL,
    source TEXT NOT NULL,
    source_file TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inbox_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relative_path TEXT NOT NULL UNIQUE,
    original_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    ocr_text TEXT,
    error_message TEXT,
    processed_at TEXT,
    created_at TEXT NOT NULL
);
"""


def ensure_datapoint_tables(profile_id: str | None = None) -> None:
    conn = health_db.connect(profile_id)
    conn.executescript(DATAPOINTS_SCHEMA)
    conn.commit()
    conn.close()


def _slugify(name: str) -> str:
    cleaned = unicodedata.normalize("NFKD", name)
    cleaned = re.sub(r"[^\w.\-]+", "_", cleaned, flags=re.UNICODE)
    return cleaned.strip("_") or "file"


def _archive_file(src: Path, profile_id: str | None = None) -> Path:
    root = health_root(profile_id)
    day = datetime.now().strftime("%Y-%m-%d")
    dest_dir = root / UPLOADS_SUBFOLDER / day
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / _slugify(src.name)
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        dest = dest_dir / f"{stem}_{datetime.now().strftime('%H%M%S')}{suffix}"
    shutil.copy2(src, dest)
    return dest


def _insert_lab_row(row: dict[str, Any], source: str, source_file: str | None, profile_id: str | None) -> bool:
    test_code = row.get("test_code") or _slugify(row.get("test_name_ru", "lab"))
    sample_date = row.get("sample_date") or row.get("date") or datetime.now().strftime("%Y-%m-%d")
    value = row.get("value")
    ref_low = row.get("ref_low")
    ref_high = row.get("ref_high")
    flag = health_db._compute_flag(value, ref_low, ref_high)

    conn = health_db.connect(profile_id)
    dup = conn.execute(
        "SELECT 1 FROM lab_results WHERE test_code = ? AND sample_date = ? AND value IS ?",
        (test_code, sample_date, value),
    ).fetchone()
    if dup:
        conn.close()
        return False

    conn.execute(
        """
        INSERT INTO lab_results(
            test_code, test_name_ru, value, value_text, unit,
            ref_low, ref_high, flag, sample_date, source_file, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            test_code,
            row.get("test_name_ru") or test_code,
            value,
            row.get("value_text"),
            row.get("unit"),
            ref_low,
            ref_high,
            flag,
            sample_date,
            source_file,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return True


def _record_datapoint(
    dtype: str,
    payload: dict[str, Any],
    source: str,
    event_date: str | None,
    title_ru: str | None,
    source_file: str | None,
    profile_id: str | None,
) -> int:
    ensure_datapoint_tables(profile_id)
    conn = health_db.connect(profile_id)
    cur = conn.execute(
        """
        INSERT INTO datapoints(type, event_date, title_ru, payload_json, source, source_file, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dtype,
            event_date,
            title_ru,
            json.dumps(payload, ensure_ascii=False),
            source,
            source_file,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return int(row_id)


def _apply_datapoint(item: dict[str, Any], source: str, source_file: str | None, profile_id: str | None) -> dict[str, Any]:
    dtype = item.get("type", "note")
    if dtype not in ALLOWED_TYPES:
        return {"ok": False, "error": f"Unknown type: {dtype}"}

    data = item.get("data") or item
    event_date = item.get("date") or data.get("sample_date") or data.get("date")
    title = item.get("title_ru") or data.get("title_ru") or data.get("test_name_ru")

    result: dict[str, Any] = {"type": dtype, "ok": True}

    if dtype == "lab":
        inserted = _insert_lab_row(data, source, source_file, profile_id)
        result["lab_inserted"] = inserted
    elif dtype == "task":
        conn = health_db.connect(profile_id)
        conn.execute(
            """
            INSERT INTO tasks(title_ru, priority, status, category, notes, created_at)
            VALUES (?, ?, 'open', ?, ?, ?)
            """,
            (
                data.get("title_ru") or title or "Новая задача",
                data.get("priority", "planned"),
                data.get("category"),
                data.get("notes"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        result["task_created"] = True
    elif dtype == "symptom":
        conn = health_db.connect(profile_id)
        conn.execute(
            """
            INSERT INTO checkins(checkin_date, summary_ru, raw_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                event_date or datetime.now().strftime("%Y-%m-%d"),
                data.get("summary_ru") or data.get("text") or title,
                json.dumps(data, ensure_ascii=False),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        result["symptom_logged"] = True
    elif dtype == "checkin":
        from backend.checkins import save_evening_checkin

        r = save_evening_checkin(
            mood=int(data.get("mood", 3)),
            sleep_quality=int(data.get("sleep_quality", data.get("sleep", 3))),
            symptoms=data.get("symptoms") or [],
            notes=data.get("notes") or data.get("summary_ru") or "",
            checkin_date=event_date,
            profile_id=profile_id,
        )
        result["checkin_saved"] = r
    elif dtype == "medication":
        conn = health_db.connect(profile_id)
        conn.execute(
            """
            INSERT INTO medications(name, generic, dose, purpose, status, notes, started_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                data.get("name") or title,
                data.get("generic"),
                data.get("dose"),
                data.get("purpose"),
                data.get("notes"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        result["medication_added"] = True

    dp_id = _record_datapoint(dtype, data if isinstance(data, dict) else {"raw": data}, source, event_date, title, source_file, profile_id)
    result["datapoint_id"] = dp_id
    return result


def import_chat_datapoints(
    datapoints: list[dict[str, Any]],
    source_label: str = "claude_chat",
    attachment_description: str = "",
    refresh_dashboard: bool = True,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """
    Import structured datapoints extracted by Claude from chat attachments or user text.
    Each item: {type, date?, title_ru?, data: {...}}
    Lab data fields: test_code, test_name_ru, value, unit, ref_low, ref_high, sample_date
    """
    ensure_datapoint_tables(profile_id)
    results = []
    labs_added = 0

    for item in datapoints:
        out = _apply_datapoint(item, source_label, attachment_description or None, profile_id)
        results.append(out)
        if out.get("lab_inserted"):
            labs_added += 1

    dashboard_path = None
    if refresh_dashboard:
        dashboard_path = str(export_dashboard_html(profile_id))

    return {
        "imported_count": len(results),
        "labs_added": labs_added,
        "results": results,
        "dashboard_path": dashboard_path,
        "message_ru": f"Импортировано {len(results)} datapoint(s), новых анализов: {labs_added}.",
    }


def get_upload_workflow_instructions() -> str:
    return """
WORKFLOW: Загрузка файлов и datapoints в Wellnest

A) ФАЙЛ В ЧАТЕ CLAUDE (фото/PDF/скрин):
   1. Пользователь прикрепляет файл к сообщению.
   2. Ты ВИДИШЬ файл — извлеки все медицинские значения (OCR/vision).
   3. Вызови import_chat_datapoints с structured JSON.
   4. Вызови refresh_dashboard_file.
   5. Кратко объясни пользователю что сохранено (↑↓ флаги).

B) ФАЙЛ В ПАПКЕ INBOX (без чата):
   1. Пользователь кладёт файл в ~/Desktop/HEALTH/inbox/
   2. Вызови list_inbox_files → process_inbox_files
   3. Если OCR текста достаточно — import_chat_datapoints из извлечённого текста
   4. Иначе попроси прикрепить файл в чат для vision

ТИПЫ datapoint.type:
   lab — анализ (value, unit, ref_low, ref_high, test_name_ru, sample_date)
   symptom — симптом/самочувствие
   task — новая задача (title_ru, priority: urgent|important|planned)
   medication — препарат
   note — клиническая заметка
   vital — давление, пульс, вес
   document — метаданные документа без чисел

Правила:
   - Дата анализа с бланка → sample_date (YYYY-MM-DD)
   - Не дублировать: если значение уже есть — сообщи
   - После импорта всегда refresh_dashboard_file
""".strip()


def list_inbox_files(profile_id: str | None = None) -> list[dict[str, Any]]:
    root = health_root(profile_id)
    inbox = root / INBOX_SUBFOLDER
    inbox.mkdir(parents=True, exist_ok=True)
    ensure_datapoint_tables(profile_id)

    conn = health_db.connect(profile_id)
    files = []
    for path in sorted(inbox.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        rel = f"{INBOX_SUBFOLDER}/{path.name}"
        row = conn.execute(
            "SELECT status, ocr_text, error_message FROM inbox_files WHERE relative_path = ?",
            (rel,),
        ).fetchone()
        files.append(
            {
                "relative_path": rel,
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "status": row["status"] if row else "new",
                "has_ocr": bool(row and row["ocr_text"]),
            }
        )
    conn.close()
    return files


def _ocr_image(path: Path) -> str:
    try:
        from ocrmac import ocrmac

        annotations = ocrmac.OCR(str(path)).recognize()
        lines = [text for text, _conf, _bbox in annotations if text.strip()]
        return "\n".join(lines)
    except ImportError:
        return ""
    except Exception as exc:
        return f"[OCR error: {exc}]"


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages[:20]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
    except ImportError:
        return ""
    except Exception as exc:
        return f"[PDF error: {exc}]"


def process_inbox_files(
    process_all: bool = True,
    relative_paths: list[str] | None = None,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Move inbox files to uploads/, OCR/extract text, register for Claude to parse."""
    root = health_root(profile_id)
    inbox = root / INBOX_SUBFOLDER
    inbox.mkdir(parents=True, exist_ok=True)
    ensure_datapoint_tables(profile_id)

    targets: list[Path] = []
    if relative_paths:
        for rel in relative_paths:
            targets.append(root / rel)
    elif process_all:
        targets = [p for p in inbox.iterdir() if p.is_file() and not p.name.startswith(".")]

    processed = []
    conn = health_db.connect(profile_id)
    now = datetime.utcnow().isoformat()

    for src in targets:
        if not src.exists():
            processed.append({"file": str(src), "ok": False, "error": "not found"})
            continue

        archived = _archive_file(src, profile_id)
        rel_archive = str(archived.relative_to(root))
        suffix = src.suffix.lower()
        ocr_text = ""
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".heic", ".tiff", ".tif"}:
            ocr_text = _ocr_image(archived)
        elif suffix == ".pdf":
            ocr_text = _extract_pdf_text(archived)
        else:
            ocr_text = archived.read_text(encoding="utf-8", errors="ignore")[:50000]

        status = "ocr_ready" if ocr_text and not ocr_text.startswith("[") else "stored"
        conn.execute(
            """
            INSERT INTO inbox_files(relative_path, original_name, status, ocr_text, processed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(relative_path) DO UPDATE SET
                status=excluded.status, ocr_text=excluded.ocr_text, processed_at=excluded.processed_at
            """,
            (rel_archive, src.name, status, ocr_text, now, now),
        )

        if src.parent == inbox and src.exists():
            src.unlink()

        processed.append(
            {
                "ok": True,
                "archived_to": rel_archive,
                "status": status,
                "ocr_preview": (ocr_text[:1500] + "…") if len(ocr_text) > 1500 else ocr_text,
                "next_step": (
                    "Parse ocr_preview and call import_chat_datapoints with lab rows."
                    if ocr_text
                    else "Ask user to attach this file in chat for vision extraction."
                ),
            }
        )

    conn.commit()
    conn.close()

    return {
        "processed_count": len(processed),
        "files": processed,
        "inbox_path": str(inbox),
    }


def get_recent_datapoints(limit: int = 20, profile_id: str | None = None) -> list[dict[str, Any]]:
    ensure_datapoint_tables(profile_id)
    conn = health_db.connect(profile_id)
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT id, type, event_date, title_ru, source, source_file, created_at FROM datapoints ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    ]
    conn.close()
    return rows
