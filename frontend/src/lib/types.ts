export type Diagnosis = { code: string; label_ru: string; status: string };

export type Profile = {
  profile_id: string;
  display_name: string;
  age: number;
  sex: string;
  diagnoses: Diagnosis[];
  last_labs_note?: string;
  specialist_panel?: string[];
};

export type LabResult = {
  id: number;
  test_code: string;
  test_name_ru: string;
  value: number | null;
  value_text: string | null;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  flag: "normal" | "low" | "high" | string;
  sample_date: string;
  source_file: string;
  freshness: { status: string; days_old: number; message_ru: string; message_en?: string };
};

export type Task = {
  id: number;
  title_ru: string;
  priority: "urgent" | "high" | "normal" | string;
  status: string;
  due_date: string | null;
  category: string;
};

export type Medication = {
  id: number;
  name: string;
  generic: string;
  dose: string;
  purpose: string;
  status: string;
};

export type LabBenchmark = {
  patient_value?: number | null;
  unit?: string;
  date?: string;
  flag?: string;
  lab_ref?: { low?: number | null; high?: number | null; label_ru?: string; label_en?: string };
  clinical_target?: {
    low?: number | null;
    high?: number | null;
    label_ru?: string;
    label_en?: string;
    note_ru?: string;
  };
  clinical_band_ru?: string;
  notes_ru?: string[];
  interpretation_ru?: string;
  sources?: string[];
};

export type LabChart = {
  code: string;
  title: string;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  color: string;
  labels: string[];
  values: (number | null)[];
  flags: string[];
  latest: number | null;
  latest_flag: string | null;
  latest_date: string;
  value_text?: string | null;
  benchmark?: LabBenchmark;
  explain?: { purpose_ru?: string; purpose_en?: string; latest_ru?: string };
};

export type SystemCard = {
  id: string;
  title: string;
  title_en: string;
  status: "good" | "warn" | "bad" | string;
  icon: string;
  explain?: {
    purpose_ru?: string;
    purpose_en?: string;
    diagnosis_ru?: string;
    diagnosis_en?: string;
    status_ru?: string;
    why_ru?: string;
    why_en?: string;
    tests_ru?: string[];
    meds_ru?: string[];
    meds_en?: string[];
    chart_codes?: string[];
    sources?: {
      code?: string;
      test?: string;
      value?: number | string | null;
      unit?: string;
      date?: string;
      flag?: string;
      file?: string;
    }[];
  };
};

export type Evidence = {
  claim_ru?: string;
  kind?: string;
  ref?: string;
  date?: string;
  source_label?: string;
  study_url?: string;
};

export type SpecialistOpinion = {
  see: string[];
  concerns: string[];
  recommendations: string[];
  evidence?: Evidence[];
};

export type Specialist = {
  id: string;
  title_ru?: string;
  title?: string;
  opinion: SpecialistOpinion;
};

export type ConsiliumReport = {
  source?: string;
  generated_at?: string;
  headline_ru?: string;
  specialists: Specialist[];
};

export type ConsiliumStatus = {
  claude_pending: boolean;
  requested_at?: string;
  has_claude_report: boolean;
  claude_generated_at?: string | null;
  claude_report?: ConsiliumReport | null;
};

export type SymptomQA = {
  pending: boolean;
  pending_question: string;
  has_answer: boolean;
  answer?: {
    question?: string;
    summary_ru?: string;
    summary_en?: string;
    possible_links_ru?: string[];
    possible_links_en?: string[];
    evidence?: Evidence[];
    discuss_with_doctor_ru?: string;
    discuss_with_doctor_en?: string;
    answered_at?: string;
    attachments?: string[];
    mode?: string;
    saved_to_history?: boolean;
    saved_at?: string;
  } | null;
};

export type WeeklyBriefItem = {
  kind: string;
  priority?: string;
  text_ru: string;
  text_en: string;
};

export type Snapshot = {
  generated_at?: string;
  profile: Profile;
  medications: Medication[];
  tasks_open: Task[];
  tasks_board: Task[];
  lab_results: LabResult[];
  alerts: { stale_or_aging_labs: number; urgent_tasks: number };
  weekly_brief: { headline_ru: string; headline_en: string; items: WeeklyBriefItem[] };
  checkins: {
    has_today: boolean;
    recent: { date: string; mood: number | null; sleep_quality: number | null; symptoms?: string[]; notes?: string }[];
    latest?: { date: string; mood: number | null; sleep_quality: number | null; notes?: string } | null;
  };
  consilium_status: ConsiliumStatus;
  consilium_preview?: { specialists: Specialist[]; headline_ru?: string };
  symptom_qa: SymptomQA;
  charts: { lab_charts: LabChart[]; wearable_charts: LabChart[]; systems: SystemCard[] };
  integrations?: {
    oura?: { connected: boolean; last_sync?: string };
    apple_health?: { last_sync?: string | null; folder?: string };
  };
};

export type EngineStatus = {
  enabled: boolean;
  model: string;
  free_models: string[];
  evidence_sources?: { europepmc?: boolean; pubmed?: boolean; openevidence?: boolean };
  message_ru?: string;
};
