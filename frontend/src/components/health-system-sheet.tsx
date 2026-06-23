import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useI18n } from "@/lib/i18n";
import type { SystemCard } from "@/lib/types";
import { LineChartIcon } from "lucide-react";

const STATUS_LABEL: Record<string, { ru: string; en: string; variant: "default" | "secondary" | "destructive" }> = {
  good: { ru: "В норме", en: "OK", variant: "default" },
  caution: { ru: "Наблюдать", en: "Watch", variant: "secondary" },
  warn: { ru: "Обсудить с врачом", en: "Discuss", variant: "destructive" },
  unknown: { ru: "Нет данных", en: "No data", variant: "secondary" },
};

type SourceRow = {
  code?: string;
  test?: string;
  value?: number | string | null;
  unit?: string;
  date?: string;
  flag?: string;
  file?: string;
};

export function HealthSystemSheet({
  system,
  open,
  onOpenChange,
  onOpenLab,
}: {
  system: SystemCard | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onOpenLab?: (code: string) => void;
}) {
  const { lang, t } = useI18n();
  if (!system) return null;

  const ex = system.explain;
  const status = STATUS_LABEL[system.status] || STATUS_LABEL.unknown;
  const sources = (ex?.sources as SourceRow[] | undefined) || [];
  const chartCodes = (ex?.chart_codes as string[] | undefined) || [];

  const openCharts = () => {
    onOpenChange(false);
    const first = chartCodes[0];
    if (first && onOpenLab) {
      onOpenLab(first);
    }
  };

  return (
    <Sheet onOpenChange={onOpenChange} open={open}>
      <SheetContent className="overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{lang === "ru" ? system.title : system.title_en}</SheetTitle>
          <SheetDescription>
            {lang === "ru" ? ex?.diagnosis_ru : ex?.diagnosis_en}
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-4 px-4 pb-6">
          <Badge variant={status.variant}>
            {lang === "ru" ? status.ru : status.en}
          </Badge>

          {ex?.purpose_ru ? (
            <p className="text-sm leading-relaxed">{lang === "ru" ? ex.purpose_ru : ex.purpose_en}</p>
          ) : null}

          <section className="flex flex-col gap-2">
            <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
              {t("sysWhy")}
            </p>
            <p className="text-sm leading-relaxed">{ex?.why_ru || ex?.status_ru}</p>
          </section>

          {sources.length ? (
            <>
              <Separator />
              <section className="flex flex-col gap-2">
                <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
                  {t("sysSources")}
                </p>
                <ul className="flex flex-col gap-2">
                  {sources.map((s, i) => (
                    <li
                      className={
                        s.code && onOpenLab
                          ? "cursor-pointer rounded-lg border bg-muted/30 px-3 py-2 text-sm transition-colors hover:bg-muted/60"
                          : "rounded-lg border bg-muted/30 px-3 py-2 text-sm"
                      }
                      key={i}
                      onClick={() => {
                        if (s.code && onOpenLab) {
                          onOpenChange(false);
                          onOpenLab(s.code);
                        }
                      }}
                    >
                      <div className="font-medium">
                        {s.test}: {s.value} {s.unit}
                        {s.flag === "high" ? " ↑" : s.flag === "low" ? " ↓" : ""}
                      </div>
                      <div className="mt-1 text-muted-foreground text-xs">
                        {s.file || "health.db"} · {s.date}
                        {s.code && onOpenLab ? ` · ${t("chartOpenDetail")}` : ""}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            </>
          ) : null}

          {ex?.meds_ru?.length ? (
            <p className="text-muted-foreground text-xs">
              {t("sysMeds")}: {(lang === "ru" ? ex.meds_ru : ex.meds_en)?.join(", ")}
            </p>
          ) : null}

          <Button className="w-full" onClick={openCharts} variant="outline">
            <LineChartIcon data-icon="inline-start" />
            {t("sysOpenCharts")}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
