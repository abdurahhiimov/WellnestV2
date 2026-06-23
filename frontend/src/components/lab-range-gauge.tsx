import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import type { LabBenchmark, LabChart } from "@/lib/types";
import { buildGaugeScale, formatLabValue } from "@/lib/lab-chart-utils";

/**
 * Bullet-style range gauge (Stephen Few): one glance shows patient vs lab norm vs clinical target.
 * Pure CSS — no Recharts — so scales stay readable.
 */
export function LabRangeGauge({ chart }: { chart: LabChart }) {
  const { lang, t } = useI18n();
  const b = chart.benchmark as LabBenchmark | undefined;
  const labLo = (b?.lab_ref?.low ?? chart.ref_low) as number | null;
  const labHi = (b?.lab_ref?.high ?? chart.ref_high) as number | null;

  if (!b || b.patient_value == null || (labLo == null && labHi == null)) {
    return <p className="text-muted-foreground text-sm">{t("chartNoBenchmark")}</p>;
  }

  const val = b.patient_value as number;
  const target = b.clinical_target;
  const scale = buildGaugeScale(val, labLo, labHi, target?.low, target?.high);
  const valPct = scale.pct(val);

  const hasLab = labLo != null && labHi != null;
  const labLoPct = hasLab ? scale.pct(labLo) : 0;
  const labHiPct = hasLab ? scale.pct(labHi) : 100;
  const hasTarget =
    target?.low != null && target?.high != null && target.low !== labLo && target.high !== labHi;
  const targetLoPct = hasTarget ? scale.pct(target!.low!) : 0;
  const targetHiPct = hasTarget ? scale.pct(target!.high!) : 0;

  const inLab =
    hasLab && val >= labLo! && val <= labHi!
      ? "inside"
      : hasLab && val < labLo!
        ? "below"
        : hasLab && val > labHi!
          ? "above"
          : "unknown";

  return (
    <div className="flex flex-col gap-4">
      {/* Track */}
      <div className="relative pt-8 pb-2">
        <div className="relative h-3 w-full overflow-hidden rounded-full bg-muted">
          {/* Below-normal zone */}
          {hasLab ? (
            <div
              className="absolute inset-y-0 left-0 bg-status-bad/15"
              style={{ width: `${labLoPct}%` }}
            />
          ) : null}
          {/* Lab normal zone */}
          {hasLab ? (
            <div
              className="absolute inset-y-0 bg-status-good/35"
              style={{ left: `${labLoPct}%`, width: `${labHiPct - labLoPct}%` }}
            />
          ) : null}
          {/* Above-normal zone */}
          {hasLab ? (
            <div
              className="absolute inset-y-0 right-0 bg-status-bad/15"
              style={{ width: `${100 - labHiPct}%` }}
            />
          ) : null}
          {/* Clinical target overlay */}
          {hasTarget ? (
            <div
              className="absolute inset-y-0 border-primary/60 border-x-2 bg-primary/20"
              style={{ left: `${targetLoPct}%`, width: `${targetHiPct - targetLoPct}%` }}
            />
          ) : null}
        </div>

        {/* Patient marker */}
        <div
          className="absolute top-0 flex -translate-x-1/2 flex-col items-center"
          style={{ left: `${valPct}%` }}
        >
          <div
            className={cn(
              "rounded-md px-2 py-0.5 font-semibold text-xs tabular-nums shadow-sm",
              inLab === "inside"
                ? "bg-status-good text-white"
                : "bg-status-warn text-white",
            )}
          >
            {formatLabValue(val)} {b.unit}
          </div>
          <div
            className={cn(
              "mt-0.5 size-0 border-x-[7px] border-x-transparent border-t-[9px]",
              inLab === "inside" ? "border-t-status-good" : "border-t-status-warn",
            )}
          />
        </div>

        {/* Scale labels */}
        <div className="mt-2 flex justify-between text-[10px] text-muted-foreground tabular-nums">
          <span>{formatLabValue(scale.viewMin)}</span>
          {hasLab ? (
            <span className="text-center">
              {formatLabValue(labLo!)} — {formatLabValue(labHi!)}
            </span>
          ) : null}
          <span>{formatLabValue(scale.viewMax)}</span>
        </div>
      </div>

      {/* Legend rows */}
      <div className="flex flex-col gap-2 text-xs">
        {hasLab ? (
          <div className="flex items-start gap-2 rounded-lg border bg-muted/30 px-3 py-2">
            <span className="mt-1 size-2.5 shrink-0 rounded-sm bg-status-good/70" />
            <div>
              <p className="font-medium">
                {lang === "ru" ? b.lab_ref?.label_ru : b.lab_ref?.label_en}
              </p>
              <p className="text-muted-foreground tabular-nums">
                {formatLabValue(labLo!)} – {formatLabValue(labHi!)} {b.unit}
              </p>
            </div>
          </div>
        ) : null}
        {hasTarget ? (
          <div className="flex items-start gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2">
            <span className="mt-1 size-2.5 shrink-0 rounded-sm bg-primary/60" />
            <div>
              <p className="font-medium">
                {lang === "ru" ? target!.label_ru : target!.label_en}
              </p>
              <p className="text-muted-foreground tabular-nums">
                {formatLabValue(target!.low!)} – {formatLabValue(target!.high!)} {b.unit}
              </p>
              {target!.note_ru ? (
                <p className="mt-1 text-muted-foreground leading-relaxed">{target!.note_ru}</p>
              ) : null}
            </div>
          </div>
        ) : null}
        <div className="flex items-start gap-2 rounded-lg border px-3 py-2">
          <span
            className={cn(
              "mt-1 size-2.5 shrink-0 rounded-full",
              inLab === "inside" ? "bg-status-good" : "bg-status-warn",
            )}
          />
          <div>
            <p className="font-medium">{lang === "ru" ? "Ваш результат" : "Your result"}</p>
            <p className="text-muted-foreground">
              {inLab === "inside" && t("gaugeInside")}
              {inLab === "below" && t("gaugeBelow")}
              {inLab === "above" && t("gaugeAbove")}
            </p>
          </div>
        </div>
      </div>

      {b.clinical_band_ru ? (
        <p className="rounded-md bg-muted/50 px-3 py-2 text-sm">{b.clinical_band_ru}</p>
      ) : null}
      {(b.notes_ru || []).map((note, i) => (
        <p className="text-muted-foreground text-xs leading-relaxed" key={i}>
          {note}
        </p>
      ))}
    </div>
  );
}
