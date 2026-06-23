"use client";

import { useId } from "react";
import { Area, AreaChart, CartesianGrid, ReferenceArea, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { cn } from "@/lib/utils";
import { flagInfo } from "@/lib/lab-flag";
import type { LabChart } from "@/lib/types";

export function LabAreaChart({
  chart,
  index,
  highlighted,
  onSelect,
}: {
  chart: LabChart;
  index: number;
  highlighted?: boolean;
  onSelect?: (chart: LabChart) => void;
}) {
  const uid = useId().replace(/:/g, "");
  const gradId = `lab-grad-${uid}`;

  const rows = chart.labels.map((date, i) => ({ date, value: chart.values[i] }));
  const fi = flagInfo(chart.latest_flag);

  const config = {
    value: { label: chart.title, color: chart.color },
  } satisfies ChartConfig;

  const values = chart.values.filter((v) => v != null);
  const lo = Math.min(...values, chart.ref_low ?? Infinity);
  const hi = Math.max(...values, chart.ref_high ?? -Infinity);
  const pad = (hi - lo) * 0.25 || 1;

  return (
    <Card
      className={cn(
        "zh-rise transition-all hover:shadow-md",
        highlighted && "ring-2 ring-primary shadow-lg",
        onSelect && "cursor-pointer",
      )}
      id={`chart-${chart.code}`}
      onClick={() => onSelect?.(chart)}
      onKeyDown={(e) => {
        if (onSelect && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onSelect(chart);
        }
      }}
      role={onSelect ? "button" : undefined}
      style={{ animationDelay: `${0.05 * index}s` }}
      tabIndex={onSelect ? 0 : undefined}
    >
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <CardTitle className="flex flex-wrap items-center gap-2 text-base">
              {chart.title}
              <Badge variant={fi.variant} className={fi.className}>
                {chart.latest != null ? `${chart.latest} ${chart.unit ?? ""}`.trim() : "—"}{fi.label ? ` · ${fi.label}` : ""}
              </Badge>
            </CardTitle>
            <CardDescription className="mt-1 line-clamp-2">
              {chart.explain?.purpose_ru || ""}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ChartContainer className="aspect-21/9 min-h-36 w-full p-0" config={config}>
          <AreaChart data={rows} margin={{ left: 4, right: 12, top: 8 }}>
            <CartesianGrid className="stroke-border" strokeDasharray="3 3" vertical={false} />
            <XAxis
              axisLine={false}
              dataKey="date"
              tickFormatter={(v) => String(v).slice(5).replace("-", ".")}
              tickLine={false}
              tickMargin={8}
            />
            <YAxis domain={[lo - pad, hi + pad]} hide />
            {chart.ref_low != null && chart.ref_high != null ? (
              <ReferenceArea
                fill="var(--status-good)"
                fillOpacity={0.07}
                y1={chart.ref_low}
                y2={chart.ref_high}
              />
            ) : null}
            <ChartTooltip content={<ChartTooltipContent />} cursor={false} />
            <defs>
              <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor={chart.color} stopOpacity={0.4} />
                <stop offset="95%" stopColor={chart.color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              dataKey="value"
              dot={{ r: 3, fill: chart.color, strokeWidth: 0 }}
              fill={`url(#${gradId})`}
              stroke={chart.color}
              strokeWidth={1.5}
              type="monotone"
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
