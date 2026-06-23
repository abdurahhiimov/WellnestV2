import * as React from "react";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { LabAreaChart } from "@/components/lab-area-chart";
import { findLabChart, LabDetailSheet } from "@/components/lab-detail-sheet";
import { useI18n } from "@/lib/i18n";
import { navigate, useHashQuery, useStore } from "@/lib/store";
import type { LabChart } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { WatchIcon } from "lucide-react";
import { flagInfo, isConcerningFlag } from "@/lib/lab-flag";

export function ChartsPage() {
  const { t } = useI18n();
  const { data } = useStore();
  const query = useHashQuery();
  const [detail, setDetail] = React.useState<LabChart | null>(null);
  const highlight = React.useMemo(
    () => new Set((query.get("highlight") || "").split(",").filter(Boolean)),
    [query],
  );
  const focusCode = query.get("focus") || "";

  React.useEffect(() => {
    if (!data) return;
    const charts = data.charts?.lab_charts || [];
    if (focusCode) {
      const c = findLabChart(charts, focusCode);
      if (c) setDetail(c);
      return;
    }
    if (!highlight.size) return;
    const first = [...highlight][0];
    const el = document.getElementById(`chart-${first}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [highlight, focusCode, data]);

  if (!data) return null;

  const labCharts = data.charts?.lab_charts || [];
  const wearables = data.charts?.wearable_charts || [];
  const concerning = labCharts.filter((c) => isConcerningFlag(c.latest_flag));

  return (
    <div className="flex flex-1 flex-col gap-6 py-6">
      <div className="zh-rise flex flex-col gap-1">
        <h1 className="font-semibold text-xl leading-tight">{t("chartsTitle")}</h1>
        <p className="text-muted-foreground text-sm">{t("chartsTapHint")}</p>
      </div>

      {concerning.length ? (
        <div className="zh-rise flex flex-wrap gap-2">
          {concerning.map((c) => {
            const fi = flagInfo(c.latest_flag);
            return (
              <Button key={c.code} onClick={() => setDetail(c)} size="sm" variant="outline">
                {c.title} {c.latest != null ? `${c.latest} ${c.unit ?? ""}`.trim() : ""} {fi.label}
              </Button>
            );
          })}
        </div>
      ) : null}

      <LabDetailSheet chart={detail} onOpenChange={(o) => !o && setDetail(null)} open={!!detail} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {labCharts.map((chart, i) => (
          <LabAreaChart
            chart={chart}
            highlighted={highlight.has(chart.code)}
            index={i}
            key={chart.code}
            onSelect={setDetail}
          />
        ))}
      </div>

      <h2 className="zh-rise font-medium text-muted-foreground text-sm">{t("wearables")}</h2>
      {wearables.length ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {wearables.map((chart, i) => (
            <LabAreaChart chart={chart} index={i} key={chart.code} />
          ))}
        </div>
      ) : (
        <Empty className="border border-dashed py-10">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <WatchIcon />
            </EmptyMedia>
            <EmptyTitle>{t("noWearable")}</EmptyTitle>
            <EmptyDescription> </EmptyDescription>
          </EmptyHeader>
          <Button onClick={() => navigate("connect")} size="sm" variant="outline">
            {t("navConnect")}
          </Button>
        </Empty>
      )}
    </div>
  );
}
