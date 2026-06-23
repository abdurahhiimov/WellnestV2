import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import type { LabChart } from "@/lib/types";
import {
  formatLabValue,
  splitTrendPoints,
  trendYDomain,
  type TrendPoint,
} from "@/lib/lab-chart-utils";

function DotLabel(props: {
  cx?: number;
  cy?: number;
  payload?: TrendPoint;
}) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return null;
  const bad = payload.flag === "low" || payload.flag === "high";
  return (
    <g>
      <circle
        cx={cx}
        cy={cy}
        fill={bad ? "var(--status-warn)" : "var(--status-good)"}
        r={5}
        stroke="var(--background)"
        strokeWidth={2}
      />
      <text
        className="fill-foreground text-[10px] font-medium tabular-nums"
        dominantBaseline="auto"
        textAnchor="middle"
        x={cx}
        y={cy - 10}
      >
        {formatLabValue(payload.value)}
      </text>
    </g>
  );
}

export function LabTrendChart({ chart }: { chart: LabChart }) {
  const { t } = useI18n();
  const { main, outliers, useLogScale } = splitTrendPoints(chart);
  const refLo = chart.ref_low;
  const refHi = chart.ref_high;
  const target = chart.benchmark?.clinical_target;
  const [yMin, yMax] = trendYDomain(main, refLo, refHi, useLogScale);

  const config = {
    value: { label: chart.title, color: chart.color },
  } satisfies ChartConfig;

  const delta =
    main.length >= 2
      ? main[main.length - 1].value - main[0].value
      : null;

  return (
    <div className="flex flex-col gap-3">
      {outliers.length > 0 ? (
        <div className="rounded-lg border border-dashed bg-muted/30 px-3 py-2 text-xs leading-relaxed">
          <p className="font-medium text-muted-foreground">{t("trendOutlierTitle")}</p>
          {outliers.map((o) => (
            <p className="mt-1 tabular-nums" key={o.date}>
              {o.date.slice(0, 10).replace(/-/g, ".")}:{" "}
              <strong>
                {formatLabValue(o.value)} {chart.unit}
              </strong>
              {" — "}
              {t("trendOutlierHint")}
            </p>
          ))}
          <p className="mt-1 text-muted-foreground">{t("trendOutlierFoot")}</p>
        </div>
      ) : null}

      {delta != null && main.length >= 2 ? (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Badge variant="outline">
            {main[0].date.slice(5).replace("-", ".")} →{" "}
            {main[main.length - 1].date.slice(5).replace("-", ".")}
          </Badge>
          <span
            className={cn(
              "font-medium tabular-nums",
              delta > 0 ? "text-status-warn" : delta < 0 ? "text-status-good" : "",
            )}
          >
            {delta > 0 ? "+" : ""}
            {formatLabValue(delta)} {chart.unit}
          </span>
        </div>
      ) : null}

      <ChartContainer className="aspect-[5/3] min-h-44 w-full" config={config}>
        <LineChart data={main} margin={{ left: 4, right: 16, top: 20, bottom: 4 }}>
          <CartesianGrid className="stroke-border/60" strokeDasharray="3 3" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="date"
            tickFormatter={(v) => String(v).slice(5).replace("-", ".")}
            tickLine={false}
            tickMargin={8}
          />
          <YAxis
            domain={[yMin, yMax]}
            scale={useLogScale ? "log" : "linear"}
            tickFormatter={(v) => formatLabValue(Number(v))}
            tickLine={false}
            width={44}
          />
          {refLo != null && refHi != null ? (
            <ReferenceArea
              fill="var(--status-good)"
              fillOpacity={0.22}
              stroke="var(--status-good)"
              strokeOpacity={0.35}
              y1={refLo}
              y2={refHi}
            />
          ) : null}
          {target?.low != null && target.high != null ? (
            <ReferenceArea
              fill="var(--primary)"
              fillOpacity={0.12}
              stroke="var(--primary)"
              strokeDasharray="4 4"
              strokeOpacity={0.5}
              y1={target.low}
              y2={target.high}
            />
          ) : null}
          {refLo != null ? (
            <ReferenceLine
              label={{ value: t("refLow"), position: "insideTopLeft", fontSize: 10 }}
              stroke="var(--status-good)"
              strokeDasharray="3 3"
              y={refLo}
            />
          ) : null}
          {refHi != null ? (
            <ReferenceLine
              label={{ value: t("refHigh"), position: "insideTopLeft", fontSize: 10 }}
              stroke="var(--status-good)"
              strokeDasharray="3 3"
              y={refHi}
            />
          ) : null}
          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(v) => `${formatLabValue(Number(v))} ${chart.unit}`}
              />
            }
          />
          <Line
            connectNulls
            dataKey="value"
            dot={(props) => <DotLabel {...props} payload={props.payload as TrendPoint} />}
            stroke={chart.color}
            strokeWidth={2.5}
            type="monotone"
          />
        </LineChart>
      </ChartContainer>

      <div className="flex flex-wrap gap-3 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded-sm bg-status-good/40" />
          {t("legendLabRef")}
        </span>
        {target?.low != null ? (
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-4 rounded-sm border border-primary/50 bg-primary/20" />
            {t("legendClinical")}
          </span>
        ) : null}
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 rounded-full bg-status-good" />
          {t("legendNormalPoint")}
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block size-2 rounded-full bg-status-warn" />
          {t("legendFlagPoint")}
        </span>
      </div>
    </div>
  );
}
