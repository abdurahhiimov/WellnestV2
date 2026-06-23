import type { Lang } from "@/lib/i18n";
import type { LabResult } from "@/lib/types";

const LAB_NAME_EN: Record<string, string> = {
  prolactin: "Prolactin",
  tsh: "TSH",
  ft4: "Free T4",
  estradiol: "Estradiol",
  vitamin_d: "Vitamin D",
  ferritin: "Ferritin",
  hemoglobin: "Hemoglobin",
  hematocrit: "Hematocrit",
  neutrophils: "Neutrophils",
  lymphocytes: "Lymphocytes",
  platelets: "Platelets",
  wbc: "White blood cells",
};

const PURPOSE: Record<string, { ru: string; en: string }> = {
  prolactinoma: { ru: "пролактинома", en: "prolactinoma" },
  hypothyroidism: { ru: "гипотиреоз", en: "hypothyroidism" },
  "HRT / menopause": { ru: "ЗГТ / менопауза", en: "HRT / menopause" },
  HRT: { ru: "ЗГТ", en: "HRT" },
};

const CATEGORY: Record<string, { ru: string; en: string }> = {
  imaging: { ru: "Обследование", en: "Imaging" },
  labs: { ru: "Анализы", en: "Labs" },
  visit: { ru: "Визит", en: "Visit" },
  meds: { ru: "Препараты", en: "Medications" },
  lifestyle: { ru: "Образ жизни", en: "Lifestyle" },
};

export function labDisplayName(lab: LabResult, lang: Lang): string {
  if (lang === "ru") return lab.test_name_ru;
  return LAB_NAME_EN[lab.test_code] || lab.test_name_ru;
}

export function medPurpose(purpose: string, lang: Lang): string {
  const row = PURPOSE[purpose];
  if (row) return lang === "ru" ? row.ru : row.en;
  return purpose;
}

export function taskCategory(category: string, lang: Lang): string {
  const row = CATEGORY[category];
  if (row) return lang === "ru" ? row.ru : row.en;
  return category;
}

export function labFreshnessMessage(
  freshness: { message_ru?: string; message_en?: string; status?: string } | undefined,
  lang: Lang,
): string {
  if (!freshness) return "";
  if (lang === "en") return freshness.message_en || freshness.message_ru || "";
  return freshness.message_ru || "";
}
