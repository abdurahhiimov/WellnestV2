"""Autonomous LLM engine (OpenRouter) — dashboard generates consilium/answers directly.

No Claude Desktop step. The FastAPI backend calls a model with the full clinical
briefing + specialist personas + gold standard, parses JSON, and saves to dashboard.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from backend.integrations import load_integrations
from backend.paths import REPO_ROOT, profile_dir

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Strong FREE models on OpenRouter (June 2026 catalog), in fallback order.
# Probed 2026-06-10: gpt-oss-120b answers in ~6s; kimi-k2.6 is no longer free (404);
# nemotron-3-ultra is a slow thinking model (~100s for 10 tokens) — excluded.
# openrouter/free = auto-router across whatever free models are currently live.
DEFAULT_MODEL = "openai/gpt-oss-120b:free"
FALLBACK_MODELS = [
    "openai/gpt-oss-120b:free",
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
]
TIMEOUT = httpx.Timeout(90.0, connect=10.0)


# ---------------------------------------------------------------- config

def engine_config() -> dict[str, Any]:
    cfg = (load_integrations().get("openrouter") or {})
    api_key = cfg.get("api_key") or os.environ.get("OPENROUTER_API_KEY", "")
    model = cfg.get("model") or DEFAULT_MODEL
    return {
        "api_key": (api_key or "").strip(),
        "model": model,
        "enabled": bool((api_key or "").strip() and not api_key.startswith("YOUR_")),
    }


def engine_status() -> dict[str, Any]:
    cfg = engine_config()
    try:
        from backend.evidence_retrieval import sources_status

        sources = sources_status()
    except Exception:
        sources = {"europepmc": True, "pubmed": True, "openevidence": False}
    return {
        "enabled": cfg["enabled"],
        "model": cfg["model"],
        "free_models": FALLBACK_MODELS,
        "provider": "openrouter",
        "evidence_sources": sources,
        "message_ru": (
            "Движок подключён — дашборд генерирует разбор сам."
            if cfg["enabled"]
            else "Добавьте бесплатный ключ OpenRouter во вкладке «Подключения», чтобы дашборд работал автономно."
        ),
    }


def save_engine_config(api_key: str | None = None, model: str | None = None) -> dict[str, Any]:
    from backend.integrations import integrations_path

    path = integrations_path()
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    block = data.get("openrouter") or {}
    if api_key is not None and api_key.strip():
        block["api_key"] = api_key.strip()
    if model is not None and model.strip():
        block["model"] = model.strip()
    block.setdefault("model", DEFAULT_MODEL)
    data["openrouter"] = block
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return engine_status()


# ---------------------------------------------------------------- llm call

def _repair_truncated_json(t: str) -> Any:
    """Best-effort repair of JSON cut off mid-generation (max_tokens hit).

    Walks the text tracking nesting, remembers "safe" cut points (just before a
    comma outside of strings) with the nesting stack at that moment, then tries
    to close the JSON from the latest cut point backwards.
    """
    start = t.find("{")
    if start == -1:
        raise ValueError("no JSON found in model response")
    t = t[start:]

    stack: list[str] = []
    in_str = False
    escape = False
    cuts: list[tuple[int, str]] = []  # (index, closers at that point)
    for i, ch in enumerate(t):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if in_str:
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack:
                stack.pop()
            if not stack:
                return json.loads(t[: i + 1], strict=False)
        elif ch == ",":
            cuts.append((i, "".join(reversed(stack))))

    for idx, closers in reversed(cuts[-25:]):
        try:
            return json.loads(t[:idx] + closers, strict=False)
        except json.JSONDecodeError:
            continue
    raise ValueError("unrepairable JSON in model response")


def _extract_json(text: str) -> Any:
    """Tolerant JSON extraction (handles ```json fences, prose, truncation)."""
    if not text:
        raise ValueError("empty response")
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    # strict=False allows raw control chars (newlines/tabs) inside strings —
    # models frequently emit these and strict parsing throws "Invalid control character".
    try:
        return json.loads(t, strict=False)
    except json.JSONDecodeError:
        pass
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(t[start : end + 1], strict=False)
        except json.JSONDecodeError:
            pass
    return _repair_truncated_json(t)


def _chat(system: str, user: str, *, want_json: bool = True, max_tokens: int = 6000) -> str:
    cfg = engine_config()
    if not cfg["enabled"]:
        raise RuntimeError("engine_not_configured")

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:8787",
        "X-Title": "Wellnest",
    }
    body: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }
    if want_json:
        body["response_format"] = {"type": "json_object"}

    models = [cfg["model"]] + [m for m in FALLBACK_MODELS if m != cfg["model"]]
    last_err: Exception | None = None
    with httpx.Client(timeout=TIMEOUT) as client:
        for model in models:
            body["model"] = model
            t0 = time.monotonic()
            try:
                r = client.post(OPENROUTER_URL, headers=headers, json=body)
                if r.status_code in (404, 429, 503):
                    last_err = RuntimeError(f"{model}: unavailable ({r.status_code})")
                    print(f"[llm_engine] {model}: HTTP {r.status_code} in {time.monotonic()-t0:.1f}s, trying next", flush=True)
                    continue
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    print(f"[llm_engine] {model}: ok in {time.monotonic()-t0:.1f}s", flush=True)
                    return content
                last_err = RuntimeError(f"{model}: empty content")
            except Exception as exc:  # try next model
                last_err = exc
                print(f"[llm_engine] {model}: {type(exc).__name__} in {time.monotonic()-t0:.1f}s, trying next", flush=True)
                continue
    raise RuntimeError(f"all models failed: {last_err}")


# ---------------------------------------------------------------- prompts

def _gold_standard() -> str:
    for p in (profile_dir() / "CONSILIUM_GOLD_STANDARD.md", profile_dir("default") / "CONSILIUM_GOLD_STANDARD.md"):
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


SPECIALISTS_RU: dict[str, str] = {
    "endo": "эндокринолог (щитовидная железа, пролактинома, гипофиз, гормональные оси, дозы каберголина/левотироксина)",
    "gyn": "гинеколог (менопауза, ЗГТ, эстрадиол/прогестерон, эндометрий, маммография)",
    "neuro": "невролог (головные боли, МРТ головного мозга, аденома гипофиза и зрение, сон, когнитивные жалобы)",
    "nutri": "нутрициолог (дефициты витаминов/минералов, ферритин, D3, B12, взаимодействия добавок с препаратами, питание)",
    "ortho": "ортопед (костно-мышечная система, плотность костей, остеопороз в менопаузу, суставы, физическая активность)",
    "gp": "семейный врач — сводный план: приоритет 1, приоритет 2, safety net (красные флаги, при которых не ждать)",
}


# ---------------------------------------------------------------- persona

def _profile_persona(profile_id: str | None = None) -> dict[str, Any]:
    """Demographics + language + panel pulled from the live profile."""
    from backend.profile_store import age_from_profile, load_profile

    from backend.medical_graph import allergy_summary

    p = load_profile(profile_id)
    return {
        "lang": "ru" if p.get("language_primary") == "ru" else "en",
        "age": age_from_profile(p),
        "sex": (p.get("sex") or "").lower(),
        "conditions": [
            (c.get("label") or c.get("code"))
            for c in (p.get("conditions") or [])
            if (c.get("label") or c.get("code"))
        ],
        "panel": p.get("specialist_panel") or [],
        "allergies": allergy_summary(p),
    }


def _allergy_line(persona: dict[str, Any]) -> str:
    """A hard safety line for prompts; empty string if no allergies."""
    a = persona.get("allergies")
    if not a:
        return ""
    if persona.get("lang") == "ru":
        return f" ВАЖНО: аллергии — {a}. НИКОГДА не рекомендуй то, на что есть аллергия."
    return f" IMPORTANT: allergies — {a}. NEVER recommend anything the patient is allergic to."


def _demographic_phrase(persona: dict[str, Any]) -> str:
    age, sex, lang = persona.get("age"), persona.get("sex"), persona.get("lang")
    conds = persona.get("conditions") or []
    if lang == "ru":
        noun = "пациентки" if sex == "female" else "пациента"
        age_s = f"{age} лет" if age else "взрослого возраста"
        cond_s = f" ({', '.join(conds)})" if conds else ""
        return f"{noun} {age_s}{cond_s}"
    sex_word = {"female": "female", "male": "male"}.get(sex, "")
    age_s = f"{age}-year-old" if age else "adult"
    cond_s = f" with {', '.join(conds)}" if conds else ""
    return " ".join(f"{age_s} {sex_word} patient{cond_s}".split())


def _role_desc(spec_id: str, lang: str) -> str:
    from backend.specialist_selector import specialist_by_id

    s = specialist_by_id(spec_id)
    if not s:
        return SPECIALISTS_RU.get(spec_id, spec_id)
    name = (s.get("name") or {}).get(lang) or (s.get("name") or {}).get("en", spec_id)
    focus = (s.get("focus") or {}).get(lang) or (s.get("focus") or {}).get("en", "")
    return f"{name} ({focus})" if focus else name


def _consilium_system(spec_id: str, persona: dict[str, Any]) -> str:
    lang = persona.get("lang", "en")
    role = _role_desc(spec_id, lang)
    who = _demographic_phrase(persona)
    if lang == "ru":
        return (
            f"Ты — {role} в виртуальном консилиуме для {who}. "
            "Пишешь по-русски, простым человеческим языком, как опытный врач объясняет пациенту. "
            "НЕ шаблон «обратитесь к врачу» — конкретика: цифры с датами, динамика, механизмы простыми словами, "
            "точные шаги (что, когда, какая доза, что НЕ менять). "
            "Используй ТОЛЬКО предоставленные данные пациента; не выдумывай анализы, которых нет. "
            "Эталон качества дан в тексте GOLD STANDARD — соответствуй ему."
            + _allergy_line(persona)
        )
    return (
        f"You are a {role} on a virtual medical board for a {who}. "
        "Write in clear, plain English, the way an experienced doctor explains to a patient. "
        "Not a template 'see a doctor' — be specific: numbers with dates, trends, mechanisms in plain words, "
        "exact steps (what, when, what dose, what NOT to change). "
        "Use ONLY the provided patient data; do not invent labs that aren't there. "
        "A GOLD STANDARD quality sample is included — match its level."
        + _allergy_line(persona)
    )


def _evidence_block(library: list[dict]) -> str:
    if not library:
        return (
            "\n\nEVIDENCE LIBRARY: пусто (нет интернета). "
            "НЕ выдумывай URL — для evidence.study_url оставляй пустую строку, заполняй source_label.\n"
        )
    lines = []
    for i, e in enumerate(library, 1):
        lines.append(
            f"[{i}] {e.get('title','')} — {e.get('source_label','')} — {e.get('study_url','')}"
        )
    return (
        "\n\nEVIDENCE LIBRARY (реальные источники; используй ТОЛЬКО эти URL в evidence.study_url, "
        "не выдумывай других ссылок):\n" + "\n".join(lines) + "\n"
    )


def _consilium_user(spec_id: str, briefing: dict, gold: str, library: list[dict], lang: str = "en") -> str:
    if lang == "ru":
        header = "ДАННЫЕ ПАЦИЕНТА (JSON):\n"
        gold_label = "\n\nЭТАЛОН КАЧЕСТВА (фрагмент твоей специальности — соответствуй уровню):\n"
        ask = f"\n\nДай ТОЛЬКО своё заключение ({spec_id}). ВЕРНИ СТРОГО JSON такого вида:\n"
        footer = (
            "\n\nВажно: see ≥ 25 слов, ≥ 2 рекомендации, ≥ 2 evidence. "
            "study_url добавляй только если уверен в официальном источнике; иначе оставь source_label."
        )
    else:
        header = "PATIENT DATA (JSON):\n"
        gold_label = "\n\nGOLD STANDARD (a sample from your specialty — match this level):\n"
        ask = f"\n\nGive ONLY your own assessment ({spec_id}). RETURN STRICTLY JSON of this shape:\n"
        footer = (
            "\n\nImportant: 'see' ≥ 25 words, ≥ 2 recommendations, ≥ 2 evidence items. "
            "Write all content in English. Add study_url only if sure of an official source; otherwise leave source_label."
        )
    return (
        header
        + json.dumps(briefing, ensure_ascii=False, indent=2)
        + _evidence_block(library)
        + gold_label
        + gold
        + ask
        + json.dumps(
            {
                "id": spec_id,
                "opinion": {
                    "see": ["связный текст: 3–8 предложений с цифрами, датами, динамикой"],
                    "concerns": ["конкретные риски и диагностические пробелы"],
                    "recommendations": ["минимум 2 пункта: действие + срок + доза/уточнение"],
                    "evidence": [
                        {
                            "claim_ru": "ТТГ 3,07 мМЕ/л, 22.05.2026",
                            "kind": "lab|imaging|guideline|checkin|profile",
                            "ref": "tsh",
                            "date": "2026-05-22",
                            "source_label": "health.db / lab_results",
                            "study_url": "https://... (только из EVIDENCE LIBRARY или известных гайдлайнов ATA/NAMS/Endocrine Society)",
                        }
                    ],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + footer
    )


def _validate_opinion(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict) or not isinstance(parsed.get("opinion"), dict):
        raise ValueError("bad opinion JSON shape")
    op = parsed["opinion"]
    see_words = len(" ".join(str(x) for x in (op.get("see") or [])).split())
    recs = len(op.get("recommendations") or [])
    if see_words < 10 or recs < 1:
        raise ValueError(f"opinion too thin (see={see_words} words, recs={recs})")
    return parsed


def _generate_one_specialist(spec_id: str, briefing: dict, gold: str, library: list[dict],
                             persona: dict[str, Any]) -> dict[str, Any]:
    system = _consilium_system(spec_id, persona)
    user = _consilium_user(spec_id, briefing, gold, library, persona.get("lang", "en"))
    last_err: Exception | None = None
    for attempt in (1, 2, 3):
        try:
            # gpt-oss is a reasoning model: its hidden reasoning counts toward
            # max_tokens, so the budget must be generous or the JSON gets cut off.
            raw = _chat(system, user, want_json=True, max_tokens=8000)
            parsed = _validate_opinion(_extract_json(raw))
            parsed["id"] = spec_id
            return parsed
        except Exception as exc:
            last_err = exc
            print(f"[llm_engine] {spec_id}: attempt {attempt} failed: {exc}", flush=True)
            if attempt < 3:
                time.sleep(5 * attempt)  # let free-tier rate limits cool down
    raise ValueError(f"{spec_id}: {last_err}")


def generate_consilium(profile_id: str | None = None, progress: dict[str, Any] | None = None,
                       specialist_ids: list[str] | None = None) -> dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from backend.clinical_history import build_consilium_briefing
    from backend.consilium_ai import save_claude_consilium_report
    from backend.evidence_retrieval import evidence_library_for_patient

    briefing = build_consilium_briefing(profile_id)
    library = evidence_library_for_patient(profile_id)
    gold = _gold_standard()
    persona = _profile_persona(profile_id)
    if progress is not None:
        progress["stage"] = "doctors"

    # One LLM call per specialist, in parallel: faster wall time than a single
    # monolithic 6-doctor generation, and each opinion gets more depth.
    # max_workers=3 keeps us under OpenRouter free-tier rate limits (429s at 6).
    t0 = time.monotonic()
    all_ids = persona.get("panel") or list(SPECIALISTS_RU)
    spec_ids = [s for s in specialist_ids if s in all_ids] if specialist_ids else all_ids
    specialists: list[dict[str, Any]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_generate_one_specialist, sid, briefing, gold, library, persona): sid for sid in spec_ids}
        for fut in as_completed(futures):
            with _JOB_LOCK:
                if progress is not None and progress.get("cancel_requested"):
                    for pending in futures:
                        pending.cancel()
                    raise ConsiliumCancelled("user_cancelled")
            sid = futures[fut]
            try:
                specialists.append(fut.result())
                if progress is not None:
                    progress.setdefault("done_ids", []).append(sid)
            except Exception as exc:
                errors.append(f"{sid}: {exc}")
                if progress is not None:
                    progress.setdefault("failed_ids", []).append(sid)
    print(f"[llm_engine] consilium: {len(specialists)}/{len(spec_ids)} specialists in {time.monotonic()-t0:.1f}s", flush=True)

    if not specialists:
        raise ValueError(f"all specialists failed: {'; '.join(errors)}")

    result = save_claude_consilium_report(specialists, profile_id=profile_id)
    result["engine"] = engine_config()["model"]
    if errors:
        result["partial_errors"] = errors
    return result


# ---------------------------------------------------------------- background job

class ConsiliumCancelled(Exception):
    """Raised when the user stops a running consilium job."""


_JOB_LOCK = threading.Lock()
_JOB: dict[str, Any] = {"state": "idle"}


def consilium_job_status() -> dict[str, Any]:
    with _JOB_LOCK:
        snap = dict(_JOB)
    panel = _profile_persona().get("panel") or list(SPECIALISTS_RU)
    snap["total"] = len(panel)
    snap["specialist_ids"] = panel
    return snap


def cancel_consilium_job() -> dict[str, Any]:
    """Request stop of the in-flight consilium job (best-effort)."""
    with _JOB_LOCK:
        if _JOB.get("state") != "running":
            return consilium_job_status()
        _JOB["cancel_requested"] = True
    return consilium_job_status()


def start_consilium_job(profile_id: str | None = None, specialist_ids: list[str] | None = None) -> dict[str, Any]:
    """Kick off consilium generation in a background thread (non-blocking)."""
    with _JOB_LOCK:
        if _JOB.get("state") == "running":
            return consilium_job_status()
        _JOB.clear()
        _JOB.update({"state": "running", "stage": "evidence", "started_at": time.time(), "done_ids": [], "failed_ids": [],
                     "specialist_ids": specialist_ids or []})

    def _run() -> None:
        try:
            result = generate_consilium(profile_id, progress=_JOB, specialist_ids=specialist_ids)
            with _JOB_LOCK:
                if _JOB.get("cancel_requested"):
                    _JOB["state"] = "cancelled"
                    _JOB["finished_at"] = time.time()
                    return
                _JOB["state"] = "done"
                _JOB["result"] = result
                _JOB["finished_at"] = time.time()
        except ConsiliumCancelled:
            with _JOB_LOCK:
                _JOB["state"] = "cancelled"
                _JOB["finished_at"] = time.time()
        except Exception as exc:
            with _JOB_LOCK:
                _JOB["state"] = "error"
                _JOB["error"] = str(exc)
                _JOB["finished_at"] = time.time()

    threading.Thread(target=_run, name="consilium-job", daemon=True).start()
    return consilium_job_status()


# ---------------------------------------------------------------- symptom background job

_SYMPTOM_JOB_LOCK = threading.Lock()
_SYMPTOM_JOB: dict[str, Any] = {"state": "idle"}


def symptom_job_status() -> dict[str, Any]:
    with _SYMPTOM_JOB_LOCK:
        return dict(_SYMPTOM_JOB)


def start_symptom_job(
    question: str,
    *,
    attachments: list[str] | None = None,
    mode: str = "quick",
    also_full_consilium: bool = False,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Start symptom answer generation in the background (non-blocking)."""
    display_q = (question or "").strip()
    if len(display_q) < 2:
        return {"state": "error", "error": "question_too_short"}

    with _SYMPTOM_JOB_LOCK:
        if _SYMPTOM_JOB.get("state") == "running":
            return symptom_job_status()
        _SYMPTOM_JOB.clear()
        _SYMPTOM_JOB.update(
            {
                "state": "running",
                "question": display_q,
                "mode": mode,
                "started_at": time.time(),
            }
        )

    enriched = display_q
    if attachments:
        from backend.attachments import attachments_context

        names = ", ".join(Path(str(a)).name for a in attachments)
        enriched += f"\n\nВложения (файлы пациента): {names}"
        extracted = attachments_context(attachments, profile_id)
        if extracted:
            enriched += (
                "\n\nСОДЕРЖИМОЕ ВЛОЖЕНИЙ (распознанный текст — анализируй эти данные) / "
                "ATTACHMENT CONTENT (extracted text — analyze this):\n" + extracted
            )

    def _run() -> None:
        try:
            result = generate_symptom_answer(
                enriched,
                profile_id=profile_id,
                attachments=attachments,
                mode=mode,
                display_question=display_q,
            )
            if also_full_consilium:
                start_consilium_job(profile_id)
            with _SYMPTOM_JOB_LOCK:
                _SYMPTOM_JOB["state"] = "done"
                _SYMPTOM_JOB["result"] = result
                _SYMPTOM_JOB["finished_at"] = time.time()
        except Exception as exc:
            with _SYMPTOM_JOB_LOCK:
                _SYMPTOM_JOB["state"] = "error"
                _SYMPTOM_JOB["error"] = str(exc)
                _SYMPTOM_JOB["finished_at"] = time.time()

    threading.Thread(target=_run, name="symptom-job", daemon=True).start()
    return symptom_job_status()


# ---------------------------------------------------------------- symptom Q&A

def _symptom_system(persona: dict[str, Any]) -> str:
    who = _demographic_phrase(persona)
    if persona.get("lang") == "ru":
        return (
            f"Ты — заботливый семейный врач для {who}. "
            "Отвечаешь по-русски, тепло и просто, 2–4 коротких абзаца. НЕ ставишь диагноз. "
            "Объясняешь возможные причины простым языком, связываешь с состоянием и анализами, "
            "даёшь конкретные мягкие шаги. Только предоставленные данные."
            + _allergy_line(persona)
        )
    return (
        f"You are a caring family doctor for a {who}. "
        "Answer in warm, plain English, 2–4 short paragraphs. Do NOT diagnose. "
        "Explain possible causes in plain words, connect them to the patient's conditions and labs, "
        "give specific gentle next steps. Use only the provided data."
        + _allergy_line(persona)
    )


def _symptom_user(question: str, briefing: dict, library: list[dict], lang: str = "en") -> str:
    # Always request both languages so the user can switch without re-asking.
    schema = {
        "summary_ru": "2–4 абзаца простым языком, тёплый тон (на РУССКОМ)",
        "summary_en": "2–4 paragraphs in plain, warm English",
        "possible_links_ru": ["возможная связь 1 (по-русски)", "возможная связь 2"],
        "possible_links_en": ["possible link 1 (English)", "possible link 2"],
        "evidence": [
            {"claim_ru": "на русском", "claim_en": "in English",
             "kind": "lab|guideline|checkin|profile", "source_label": "...", "study_url": ""}
        ],
        "discuss_with_doctor_ru": "что обсудить с врачом (по-русски)",
        "discuss_with_doctor_en": "what to discuss with the doctor (English)",
    }
    if lang == "ru":
        header = f"ВОПРОС ПАЦИЕНТА: {question}\n\nКОНТЕКСТ (JSON):\n"
        footer = "\n\nВЕРНИ СТРОГО JSON (оба языка — ru и en):\n"
    else:
        header = f"PATIENT QUESTION: {question}\n\nCONTEXT (JSON):\n"
        footer = "\n\nRETURN STRICTLY JSON (both languages — ru and en):\n"
    return (
        header
        + json.dumps(briefing, ensure_ascii=False, indent=2)
        + _evidence_block(library)
        + footer
        + json.dumps(schema, ensure_ascii=False, indent=2)
    )


def generate_symptom_answer(
    question: str,
    profile_id: str | None = None,
    *,
    attachments: list[str] | None = None,
    mode: str | None = None,
    display_question: str | None = None,
) -> dict[str, Any]:
    from backend.clinical_history import build_consilium_briefing
    from backend.evidence_retrieval import evidence_library_for_query
    from backend.symptom_qa import save_symptom_answer

    briefing = build_consilium_briefing(profile_id)
    library = evidence_library_for_query(question)
    persona = _profile_persona(profile_id)
    raw = _chat(_symptom_system(persona), _symptom_user(question, briefing, library, persona.get("lang", "en")), want_json=True)
    parsed = _extract_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError("bad symptom answer")
    res = save_symptom_answer(
        summary_ru=parsed.get("summary_ru", ""),
        summary_en=parsed.get("summary_en", ""),
        possible_links_ru=parsed.get("possible_links_ru") or [],
        possible_links_en=parsed.get("possible_links_en") or [],
        evidence=parsed.get("evidence") or [],
        discuss_with_doctor_ru=parsed.get("discuss_with_doctor_ru", ""),
        discuss_with_doctor_en=parsed.get("discuss_with_doctor_en", ""),
        attachments=attachments,
        mode=mode,
        question=display_question or question.split("\n\nВложения")[0].strip(),
        profile_id=profile_id,
    )
    res["engine"] = engine_config()["model"]
    return res


def extract_labs_from_text(text: str, hint_date: str | None = None,
                           profile_id: str | None = None) -> dict[str, Any]:
    """Use the LLM to extract structured lab rows from OCR/PDF text.

    Returns {"ok": True, "sample_date": "...", "rows": [...]} on success.
    """
    from datetime import date

    today = date.today().isoformat()

    # Build patient context for reference-range lookup
    patient_ctx = ""
    try:
        from backend.health_db import get_patient_profile
        p = get_patient_profile(profile_id)
        sex = p.get("sex") or "unknown"
        age = p.get("age") or "unknown"
        conditions = ", ".join(
            (d.get("label") or d.get("code", "")) for d in (p.get("diagnoses") or [])
        ) or "none"
        patient_ctx = (
            f"\nPatient context: sex={sex}, age={age}, conditions={conditions}.\n"
            "For any test where ref_low/ref_high are NOT in the document, fill them in using "
            "standard evidence-based reference ranges appropriate for this patient's sex and age. "
            "If no standard range exists for a test, leave ref_low/ref_high as null."
        )
    except Exception:
        pass

    system = (
        "You are a medical lab result extraction and interpretation specialist.\n"
        "Extract ALL lab test results from the document text provided by the user.\n"
        + patient_ctx + "\n\n"
        "Return ONLY valid JSON with this exact structure — no markdown, no explanation:\n"
        "{\n"
        '  "sample_date": "YYYY-MM-DD",\n'
        '  "rows": [\n'
        "    {\n"
        '      "test_name": "exact name from document",\n'
        '      "value": 1.23,\n'
        '      "value_text": null,\n'
        '      "unit": "unit",\n'
        '      "ref_low": 0.5,\n'
        '      "ref_high": 4.5\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Include every lab test present — do not skip any.\n"
        "- value: numeric float/int. Set null if result is text-only (e.g. 'negative').\n"
        "- value_text: the string result when value is null, otherwise null.\n"
        "- ref_low/ref_high: first read from the document; if not stated, use standard ranges for this patient.\n"
        f"- sample_date: from the document in YYYY-MM-DD. Use {hint_date or today} if not found.\n"
        "- Preserve test names exactly as shown (any language)."
    )
    user = f"Extract all lab results from this medical document:\n\n{text}"
    raw = _chat(system, user, want_json=True, max_tokens=4000)
    parsed = _extract_json(raw)
    if not isinstance(parsed, dict) or "rows" not in parsed:
        return {"ok": False, "error": "no_rows_extracted"}
    rows = [r for r in (parsed.get("rows") or []) if isinstance(r, dict) and r.get("test_name")]
    sample_date = str(parsed.get("sample_date") or hint_date or today)
    for row in rows:
        if not row.get("sample_date"):
            row["sample_date"] = sample_date
    return {"ok": True, "sample_date": sample_date, "rows": rows}


def explain_lab_result(
    test_name: str,
    value: float | None,
    value_text: str | None,
    unit: str,
    flag: str | None,
    ref_low: float | None,
    ref_high: float | None,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Generate a bilingual patient-friendly explanation for a single lab result."""
    # Build patient context
    patient_ctx = ""
    try:
        from backend.health_db import get_patient_profile
        p = get_patient_profile(profile_id)
        sex = p.get("sex") or "unknown"
        age = p.get("age") or "unknown"
        conditions = ", ".join(
            (d.get("label") or d.get("code", "")) for d in (p.get("diagnoses") or [])
        ) or "none"
        patient_ctx = f"Patient: sex={sex}, age={age}, diagnoses={conditions}."
    except Exception:
        pass

    # Format value safely — avoid floating-point strings like 0.010000000000000002
    def _fmt(v: float) -> str:
        return f"{v:.6g}"
    value_str = f"{_fmt(value)} {unit}".strip() if value is not None else (value_text or "—")
    ref_str = f"{_fmt(ref_low)}–{_fmt(ref_high)} {unit}".strip() if (ref_low is not None and ref_high is not None) else "not provided"
    flag_str = flag or "none"

    system = (
        "You are a medical AI assistant helping a patient understand their lab results. "
        "Write short, clear, friendly explanations. Avoid jargon. "
        "Do not diagnose. Do not advise changing medications without a doctor."
    )
    user = (
        f"Lab test: {test_name}\n"
        f"Result: {value_str}\n"
        f"Reference range: {ref_str}\n"
        f"Status flag: {flag_str}\n"
        f"{patient_ctx}\n\n"
        "Write a 3–5 sentence explanation covering:\n"
        "1. What this test measures and why it matters\n"
        "2. Whether this result is normal for this patient\n"
        "3. What it means for their health / any relevant context\n\n"
        "Return JSON only:\n"
        '{"explanation_ru": "...", "explanation_en": "..."}'
    )
    try:
        raw = _chat(system, user, want_json=True, max_tokens=600)
        parsed = _extract_json(raw)
        if isinstance(parsed, dict) and (parsed.get("explanation_ru") or parsed.get("explanation_en")):
            return {"ok": True, "explanation_ru": parsed.get("explanation_ru", ""), "explanation_en": parsed.get("explanation_en", "")}
        return {"ok": False, "error": "parse_error"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
