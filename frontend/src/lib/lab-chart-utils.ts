import type { LabBenchmark, LabChart } from "@/lib/types";

export function formatLabValue(v: number): string {
  if (!Number.isFinite(v)) return "—";
  const abs = Math.abs(v);
  if (abs >= 1000) return v.toFixed(0);
  if (abs >= 100) return v.toFixed(0);
  if (abs >= 10) return v.toFixed(1);
  if (abs >= 1) return v.toFixed(2);
  return v.toFixed(2);
}

export type TrendPoint = {
  date: string;
  value: number;
  flag: string;
  isOutlier?: boolean;
};

/** Split history when one pre-treatment spike hides recent dynamics (e.g. prolactin 2268 → 219). */
export function splitTrendPoints(chart: LabChart): {
  main: TrendPoint[];
  outliers: TrendPoint[];
  useLogScale: boolean;
} {
  const all: TrendPoint[] = chart.labels
    .map((date, i) => ({
      date,
      value: chart.values[i],
      flag: chart.flags[i] || "normal",
    }))
    .filter((p): p is TrendPoint => p.value != null);

  if (all.length < 2) return { main: all, outliers: [], useLogScale: false };

  const refHi = chart.ref_high ?? Infinity;
  const sorted = [...all].map((p) => p.value).sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)] ?? sorted[0];
  const max = Math.max(...all.map((p) => p.value));

  const outliers = all.filter(
    (p) => p.value > Math.max(refHi * 2.5, median * 8) && p.value > max * 0.4,
  );
  const outlierDates = new Set(outliers.map((p) => p.date));
  const main = all.filter((p) => !outlierDates.has(p.date));

  const mainMax = main.length ? Math.max(...main.map((p) => p.value)) : max;
  const mainMin = main.length ? Math.min(...main.map((p) => p.value)) : 0;
  const useLogScale =
    outliers.length === 0 && mainMin > 0 && mainMax / mainMin > 12 && all.length >= 3;

  return {
    main: main.length >= 2 ? main : all,
    outliers,
    useLogScale,
  };
}

export function trendYDomain(
  points: TrendPoint[],
  refLow: number | null | undefined,
  refHigh: number | null | undefined,
  log: boolean,
): [number, number] {
  const vals = points.map((p) => p.value);
  if (!vals.length) return [0, 1];

  let lo = Math.min(...vals, refLow ?? Infinity);
  let hi = Math.max(...vals, refHigh ?? -Infinity);

  if (log) {
    const minPos = Math.min(...vals.filter((v) => v > 0));
    return [minPos * 0.85, hi * 1.15];
  }

  if (lo === hi) {
    lo -= Math.abs(lo) * 0.15 || 1;
    hi += Math.abs(hi) * 0.15 || 1;
  }

  const span = hi - lo;
  const pad = span * 0.12 || 1;
  lo = lo - pad;
  hi = hi + pad;

  // Most lab values cannot be negative
  if ((refLow ?? 0) >= 0 && Math.min(...vals) >= 0) {
    lo = Math.max(0, lo);
  }

  return [lo, hi];
}

export type GaugeScale = {
  viewMin: number;
  viewMax: number;
  pct: (v: number) => number;
};

export function buildGaugeScale(
  value: number,
  labLo: number | null | undefined,
  labHi: number | null | undefined,
  targetLo?: number | null,
  targetHi?: number | null,
): GaugeScale {
  const anchors = [value, labLo, labHi, targetLo, targetHi].filter(
    (x): x is number => x != null && Number.isFinite(x),
  );
  if (!anchors.length) {
    return { viewMin: 0, viewMax: 100, pct: () => 50 };
  }

  let viewMin = Math.min(...anchors);
  let viewMax = Math.max(...anchors);

  if (labLo != null && labHi != null) {
    const span = labHi - labLo || viewMax - viewMin || 1;
    viewMin = Math.min(viewMin, labLo - span * 0.35);
    viewMax = Math.max(viewMax, labHi + span * 0.35);
  } else {
    const span = viewMax - viewMin || Math.abs(value) || 1;
    viewMin -= span * 0.2;
    viewMax += span * 0.2;
  }

  viewMin = Math.max(0, viewMin);

  return {
    viewMin,
    viewMax,
    pct: (v: number) =>
      Math.min(100, Math.max(0, ((v - viewMin) / (viewMax - viewMin)) * 100)),
  };
}

export type Verdict = {
  tone: "good" | "warn" | "bad";
  headline_ru: string;
  headline_en: string;
  detail_ru: string;
  detail_en: string;
};

export function buildVerdict(chart: LabChart, b?: LabBenchmark): Verdict {
  const flag = b?.flag || chart.latest_flag;

  // Qualitative tests: no numeric value
  if (chart.latest == null && b?.patient_value == null) {
    const qualMap: Record<string, Verdict> = {
      neg: {
        tone: "good",
        headline_ru: "Отрицательный — инфекция/антиген не обнаружен",
        headline_en: "Negative — infection / antigen not detected",
        detail_ru: chart.explain?.purpose_ru || "",
        detail_en: chart.explain?.purpose_en || chart.explain?.purpose_ru || "",
      },
      pos: {
        tone: "bad",
        headline_ru: "Положительный — обнаружен антиген или инфекция",
        headline_en: "Positive — antigen or infection detected",
        detail_ru: chart.explain?.purpose_ru || "",
        detail_en: chart.explain?.purpose_en || chart.explain?.purpose_ru || "",
      },
      immune: {
        tone: "good",
        headline_ru: "Иммунитет подтверждён — защитные антитела присутствуют",
        headline_en: "Immune — protective antibodies present",
        detail_ru: chart.explain?.purpose_ru || "",
        detail_en: chart.explain?.purpose_en || chart.explain?.purpose_ru || "",
      },
      not_immune: {
        tone: "warn",
        headline_ru: "Иммунитет не подтверждён — защитных антител нет",
        headline_en: "Not immune — no protective antibodies detected",
        detail_ru: chart.explain?.purpose_ru || "",
        detail_en: chart.explain?.purpose_en || chart.explain?.purpose_ru || "",
      },
      equivocal: {
        tone: "warn",
        headline_ru: "Сомнительный результат — требуется повторный анализ",
        headline_en: "Equivocal — result inconclusive, retest recommended",
        detail_ru: chart.explain?.purpose_ru || "",
        detail_en: chart.explain?.purpose_en || chart.explain?.purpose_ru || "",
      },
    };
    return qualMap[flag ?? ""] ?? {
      tone: "warn",
      headline_ru: chart.value_text || "Качественный результат",
      headline_en: chart.value_text || "Qualitative result",
      detail_ru: chart.explain?.purpose_ru || "",
      detail_en: chart.explain?.purpose_en || chart.explain?.purpose_ru || "",
    };
  }

  const val = (b?.patient_value ?? chart.latest) as number;
  const unit = b?.unit || chart.unit;
  const labLo = b?.lab_ref?.low ?? chart.ref_low;
  const labHi = b?.lab_ref?.high ?? chart.ref_high;

  const fmt = formatLabValue(val);

  if (labLo != null && labHi != null) {
    if (flag === "low" || val < labLo) {
      const delta = labLo - val;
      return {
        tone: "bad",
        headline_ru: `${fmt} ${unit} — ниже нормы лаборатории`,
        headline_en: `${fmt} ${unit} — below lab reference`,
        detail_ru: `Референс ${formatLabValue(labLo)}–${formatLabValue(labHi)} ${unit}. Ваш результат на ${formatLabValue(delta)} ${unit} ниже нижней границы.`,
        detail_en: `Reference ${formatLabValue(labLo)}–${formatLabValue(labHi)} ${unit}. You are ${formatLabValue(delta)} ${unit} below the lower limit.`,
      };
    }
    if (flag === "high" || val > labHi) {
      const delta = val - labHi;
      return {
        tone: "warn",
        headline_ru: `${fmt} ${unit} — выше нормы лаборатории`,
        headline_en: `${fmt} ${unit} — above lab reference`,
        detail_ru: `Референс ${formatLabValue(labLo)}–${formatLabValue(labHi)} ${unit}. Ваш результат на ${formatLabValue(delta)} ${unit} выше верхней границы.`,
        detail_en: `Reference ${formatLabValue(labLo)}–${formatLabValue(labHi)} ${unit}. You are ${formatLabValue(delta)} ${unit} above the upper limit.`,
      };
    }
    return {
      tone: "good",
      headline_ru: `${fmt} ${unit} — в пределах нормы лаборатории`,
      headline_en: `${fmt} ${unit} — within lab reference`,
      detail_ru: `Референс ${formatLabValue(labLo)}–${formatLabValue(labHi)} ${unit}.`,
      detail_en: `Reference ${formatLabValue(labLo)}–${formatLabValue(labHi)} ${unit}.`,
    };
  }

  return {
    tone: "good",
    headline_ru: `${fmt} ${unit} — референсный диапазон не применяется`,
    headline_en: `${fmt} ${unit} — no reference range for this component`,
    detail_ru: chart.explain?.purpose_ru || "",
    detail_en: chart.explain?.purpose_en || chart.explain?.purpose_ru || "",
  };
}
