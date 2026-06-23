import type { Lang } from "@/lib/i18n";
import type { EngineStatus, Snapshot } from "@/lib/types";

export type ExtractedLabRow = {
  test_name: string;
  value: number | null;
  value_text?: string | null;
  unit?: string;
  ref_low?: number | null;
  ref_high?: number | null;
  sample_date: string;
};

export type ProfileCondition = { code: string; label: string; status?: string };
export type ProfileMedication = { name: string; dose?: string; purpose?: string };

export type Allergy = { allergen: string; reaction?: string; severity?: string };
export type Immunization = { name: string; date?: string };
export type Procedure = { name: string; date?: string; notes?: string };
export type FamilyHistory = { relation: string; condition: string };
export type EmergencyContact = { name: string; relation?: string; phone?: string };
export type Provider = { name: string; specialty?: string; phone?: string; kind?: string };

export type Profile = {
  onboarding_complete: boolean;
  display_name: string;
  sex: string;
  gender_identity?: string;
  birth_year: number | null;
  language_primary: Lang;
  conditions: ProfileCondition[];
  medications: ProfileMedication[];
  allergies: Allergy[];
  immunizations: Immunization[];
  procedures: Procedure[];
  family_history: FamilyHistory[];
  emergency_contacts: EmergencyContact[];
  providers: Provider[];
  concerns: string[];
  concern_tags: string[];
  specialist_panel: string[];
};

export type CatalogSpecialist = {
  id: string;
  name: string;
  focus: string;
  always: boolean;
};

export type ConsiliumProgress = {
  state: "idle" | "running" | "done" | "error" | "cancelled";
  stage?: "evidence" | "doctors";
  done_ids?: string[];
  failed_ids?: string[];
  specialist_ids?: string[];
  total?: number;
  error?: string;
};

export type SymptomProgress = {
  state: "idle" | "running" | "done" | "error";
  question?: string;
  mode?: string;
  error?: string;
};

// Dev: vite proxy forwards /api to 127.0.0.1:8787. Prod: served by FastAPI, same origin.
const BASE = "";

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(BASE + path, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(BASE + path, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = (data as { error?: string }).error || `${path}: ${r.status}`;
    throw new Error(msg);
  }
  return data as T;
}

export const api = {
  snapshot: () => getJson<Snapshot>("/api/snapshot"),
  refresh: () => postJson<{ ok: boolean }>("/api/refresh"),

  engineStatus: () => getJson<EngineStatus>("/api/engine/status"),
  engineConfigure: (apiKey: string, model: string) =>
    postJson<EngineStatus>("/api/engine/configure", { api_key: apiKey, model }),

  consiliumGenerate: (specialistIds?: string[]) =>
    postJson<{ ok: boolean; error?: string }>("/api/consilium/generate",
      specialistIds?.length ? { specialist_ids: specialistIds } : undefined),
  consiliumProgress: () => getJson<ConsiliumProgress>("/api/consilium/progress"),
  consiliumCancel: () => postJson<{ ok: boolean; job: ConsiliumProgress }>("/api/consilium/cancel"),
  consiliumRequestClaude: () => postJson<{ ok: boolean }>("/api/consilium/request-claude"),
  consiliumStatus: () =>
    getJson<{ claude_pending: boolean; has_claude_report: boolean }>("/api/consilium/status"),

  askSymptom: (question: string, attachments?: string[]) =>
    postJson<{ ok: boolean; mode?: string; job?: SymptomProgress }>("/api/symptom-question", {
      question,
      attachments,
    }),

  askSymptomConsilium: (question: string, attachments?: string[], alsoFullConsilium?: boolean) =>
    postJson<{ ok: boolean; job?: SymptomProgress; error?: string }>("/api/symptom-consilium", {
      question,
      attachments,
      also_full_consilium: alsoFullConsilium,
    }),

  symptomProgress: () => getJson<SymptomProgress>("/api/symptom-question/progress"),

  uploadFiles: async (files: File[]) => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    const r = await fetch(BASE + "/api/uploads", { method: "POST", body: fd });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((data as { error?: string }).error || "upload failed");
    return data as { ok: boolean; files: { name: string; path: string }[] };
  },

  saveSymptomMemory: (question: string, attachments?: string[]) =>
    postJson<{ ok: boolean }>("/api/symptom-answer/save-memory", { question, attachments }),

  symptomReport: (question: string, attachments?: string[], lang?: Lang) =>
    postJson<{ ok: boolean; url: string; filename?: string }>("/api/symptom-answer/report", {
      question,
      attachments,
      lang: lang || "ru",
    }),

  visitPack: (lang?: Lang, sections?: string[]) =>
    postJson<{ ok: boolean; url: string; filename?: string }>("/api/visit-pack", { lang: lang || "ru", sections }),

  saveCheckin: (body: { mood: number; sleep: string; symptoms?: string[]; notes?: string }) =>
    postJson<{ ok: boolean }>("/api/symptom-survey", body),

  updateTaskStatus: (taskId: number, status: string) =>
    postJson<{ ok: boolean }>(`/api/tasks/${taskId}/status`, { status }),

  deleteTask: (taskId: number) =>
    fetch(BASE + `/api/tasks/${taskId}`, { method: "DELETE" }).then(async (r) => {
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error((data as { error?: string }).error || "delete failed");
      return data as { ok: boolean };
    }),

  downloadReport: async (filename: string) => {
    const r = await fetch(BASE + `/api/reports/download/${encodeURIComponent(filename)}`);
    if (!r.ok) throw new Error("download failed");
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
  symptomStatus: () =>
    getJson<{ pending: boolean; has_answer: boolean }>("/api/symptom-question/status"),

  extractLabsFromFile: (path: string) =>
    postJson<{
      ok: boolean;
      sample_date?: string;
      rows?: ExtractedLabRow[];
      error?: string;
    }>("/api/labs/extract-from-file", { path }),

  addLabResult: (row: {
    test_name: string;
    value?: number | null;
    value_text?: string;
    unit?: string;
    sample_date: string;
    ref_low?: number | null;
    ref_high?: number | null;
  }) => postJson<{ ok: boolean; test_code?: string; flag?: string; error?: string }>("/api/labs/add", row),

  explainLabResult: (params: {
    test_code: string;
    test_name: string;
    value?: number | null;
    value_text?: string | null;
    unit?: string;
    flag?: string | null;
    ref_low?: number | null;
    ref_high?: number | null;
  }) => postJson<{ ok: boolean; explanation_ru?: string; explanation_en?: string; error?: string }>("/api/labs/explain", params),

  syncAppleHealth: () => postJson<{ ok: boolean }>("/api/sync/apple-health"),

  // profile / onboarding
  onboardingStatus: () =>
    getJson<{ onboarding_complete: boolean }>("/api/onboarding/status"),
  getProfile: () => getJson<Profile>("/api/profile"),
  specialistCatalog: (lang: Lang) =>
    getJson<{ specialists: CatalogSpecialist[] }>(`/api/specialist-catalog?lang=${lang}`),
  suggestPanel: (draft: Partial<Profile> & { use_llm?: boolean }) =>
    postJson<{ panel: string[]; rule_based: string[]; llm_added: string[] }>(
      "/api/specialist-panel/suggest",
      draft,
    ),
  saveProfile: (profile: Partial<Profile>) =>
    postJson<Profile>("/api/profile", profile),
  patchProfile: (patch: Partial<Profile>) =>
    fetch(BASE + "/api/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }).then(async (r) => {
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error((data as { error?: string }).error || "save failed");
      return data as Profile;
    }),
};

export const SERVER_BASE = BASE;

export async function downloadReport(filename: string) {
  return api.downloadReport(filename);
}
