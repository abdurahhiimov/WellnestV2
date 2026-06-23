import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { flagInfo } from "@/lib/lab-flag";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { LabRangeGauge } from "@/components/lab-range-gauge";
import { LabTrendChart } from "@/components/lab-trend-chart";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { useStore } from "@/lib/store";
import { api } from "@/lib/api";
import { buildVerdict } from "@/lib/lab-chart-utils";
import type { LabChart } from "@/lib/types";

// Cache explanations by chart code so re-opening doesn't refetch
const explanationCache: Record<string, { ru: string; en: string }> = {};

export function LabDetailSheet({
  chart,
  open,
  onOpenChange,
}: {
  chart: LabChart | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { t, lang } = useI18n();
  const { engine } = useStore();
  const [explanation, setExplanation] = React.useState<{ ru: string; en: string } | null>(null);
  const [loadingExplanation, setLoadingExplanation] = React.useState(false);

  // Fetch AI explanation when sheet opens
  React.useEffect(() => {
    if (!open || !chart || !engine?.enabled) return;

    const cached = explanationCache[chart.code];
    if (cached) { setExplanation(cached); return; }

    setExplanation(null);
    setLoadingExplanation(true);

    api.explainLabResult({
      test_code: chart.code,
      test_name: chart.title,
      value: chart.latest,
      value_text: chart.value_text,
      unit: chart.unit,
      flag: chart.latest_flag,
      ref_low: chart.ref_low,
      ref_high: chart.ref_high,
    }).then((res) => {
      if (res.ok && (res.explanation_ru || res.explanation_en)) {
        const entry = { ru: res.explanation_ru || "", en: res.explanation_en || "" };
        explanationCache[chart.code] = entry;
        setExplanation(entry);
      }
    }).catch(() => {}).finally(() => setLoadingExplanation(false));
  }, [open, chart?.code, engine?.enabled]);

  if (!chart) return null;

  const verdict = buildVerdict(chart, chart.benchmark);
  const fi = flagInfo(chart.latest_flag);
  const isQualitative = chart.latest == null && chart.benchmark?.patient_value == null;

  const valueLabel = chart.latest != null
    ? `${chart.latest} ${chart.unit ?? ""}`.trim()
    : (chart.value_text ?? "—");

  const explainText = explanation ? (lang === "ru" ? explanation.ru : explanation.en) : null;

  return (
    <Sheet onOpenChange={onOpenChange} open={open}>
      <SheetContent className="overflow-y-auto sm:max-w-xl px-6 pt-5">
        <SheetHeader className="pr-6">
          <SheetTitle className="flex flex-wrap items-center gap-2">
            {chart.title}
            <Badge variant={fi.variant} className={fi.className}>
              {valueLabel}{fi.label ? ` · ${fi.label}` : ""}
            </Badge>
          </SheetTitle>
          <SheetDescription>
            {chart.latest_date} ·{" "}
            {lang === "ru" ? chart.explain?.purpose_ru : chart.explain?.purpose_en || chart.explain?.purpose_ru || ""}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4 flex flex-col gap-6 pb-10">
          {/* Plain-language verdict */}
          <div
            className={cn(
              "rounded-xl border px-4 py-3",
              verdict.tone === "good" && "border-status-good/40 bg-status-good/10",
              verdict.tone === "warn" && "border-status-warn/40 bg-status-warn/10",
              verdict.tone === "bad" && "border-destructive/40 bg-destructive/10",
            )}
          >
            <p className="font-medium text-sm leading-snug">
              {lang === "ru" ? verdict.headline_ru : verdict.headline_en}
            </p>
            {(verdict.detail_ru || verdict.detail_en) ? (
              <p className="mt-1 text-muted-foreground text-xs leading-relaxed">
                {lang === "ru" ? verdict.detail_ru : verdict.detail_en}
              </p>
            ) : null}
          </div>

          {/* AI explanation */}
          {engine?.enabled && (
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{lang === "ru" ? "Что это значит" : "What this means"}</span>
                {loadingExplanation && <Spinner className="size-3.5 text-muted-foreground" />}
              </div>
              {explainText ? (
                <p className="text-sm leading-relaxed text-muted-foreground break-words overflow-wrap-anywhere">{
                  // Strip obviously corrupted runs of zeros (LLM float overflow artifact)
                  explainText.replace(/0{20,}/g, "…")
                }</p>
              ) : !loadingExplanation ? (
                <p className="text-muted-foreground text-xs italic">
                  {lang === "ru" ? "Не удалось получить объяснение." : "Could not load explanation."}
                </p>
              ) : null}
            </div>
          )}

          {isQualitative ? (
            chart.labels.length > 0 ? (
              <section className="flex flex-col gap-2">
                <h3 className="font-medium text-sm">{t("chartTrendTitle")}</h3>
                <div className="flex flex-col gap-1">
                  {chart.labels.map((date, i) => {
                    const rawFlag = chart.flags[i] || null;
                    const fi2 = flagInfo(rawFlag);
                    const v = chart.values[i];
                    const display = v != null ? `${v} ${chart.unit ?? ""}`.trim() : (chart.value_text ?? "—");
                    return (
                      <div
                        key={date}
                        className="flex items-center justify-between rounded-lg border bg-muted/20 px-3 py-2 text-sm"
                      >
                        <span className="tabular-nums text-muted-foreground">{date}</span>
                        <span className="flex items-center gap-2">
                          <span className="tabular-nums font-medium">{display}</span>
                          {fi2.label ? (
                            <Badge variant={fi2.variant} className={cn("text-xs", fi2.className)}>
                              {fi2.label}
                            </Badge>
                          ) : null}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </section>
            ) : null
          ) : (
            <>
              <section className="flex flex-col gap-2">
                <h3 className="font-medium text-sm">{t("chartBenchmarkTitle")}</h3>
                <p className="text-muted-foreground text-xs">{t("chartBenchmarkHint")}</p>
                <LabRangeGauge chart={chart} />
              </section>

              <section className="flex flex-col gap-2">
                <h3 className="font-medium text-sm">{t("chartTrendTitle")}</h3>
                <p className="text-muted-foreground text-xs">{t("chartTrendHint")}</p>
                <LabTrendChart chart={chart} />
              </section>
            </>
          )}

          {chart.benchmark?.interpretation_ru ? (
            <p className="rounded-lg border bg-muted/30 p-3 text-sm leading-relaxed">
              {lang === "ru"
                ? chart.benchmark.interpretation_ru
                : (chart.benchmark as any).interpretation_en || chart.benchmark.interpretation_ru}
            </p>
          ) : null}

          {chart.benchmark?.sources?.length ? (
            <p className="text-muted-foreground text-[10px]">
              {t("chartSources")}: {chart.benchmark.sources.join(" · ")}
            </p>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}

export function findLabChart(charts: LabChart[] | undefined, code: string): LabChart | null {
  if (!charts?.length) return null;
  return charts.find((c) => c.code === code) ?? null;
}

export function labRowToCode(row: { test_code?: string }): string {
  return row.test_code || "";
}
