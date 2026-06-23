import * as React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { ConsiliumHero } from "@/components/consilium-hero";
import { ConsiliumCancelPrompt } from "@/components/consilium-cancel-prompt";
import { SpecialistCard } from "@/components/specialist-card";
import { ReportDownloadButton } from "@/components/report-download-button";
import { api, type ConsiliumProgress } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { navigate, useStore } from "@/lib/store";
import { AlertTriangleIcon, CheckCircle2Icon, OctagonXIcon, StethoscopeIcon } from "lucide-react";

const DOCTOR_LABELS: Record<string, { ru: string; en: string; emoji: string }> = {
  endo: { ru: "Эндокринолог", en: "Endocrinologist", emoji: "🔬" },
  gyn: { ru: "Гинеколог", en: "Gynecologist", emoji: "🌸" },
  neuro: { ru: "Невролог", en: "Neurologist", emoji: "🧠" },
  nutri: { ru: "Нутрициолог", en: "Nutritionist", emoji: "🥦" },
  ortho: { ru: "Ортопед", en: "Orthopedist", emoji: "🦴" },
  gp: { ru: "Семейный врач", en: "Family doctor", emoji: "🩺" },
};

const ALL_DOCTOR_IDS = Object.keys(DOCTOR_LABELS);

// Doctors that are only appropriate for specific sexes
const SEX_RESTRICTED: Record<string, string[]> = {
  gyn: ["f", "female"],
};

function availableDoctorIds(sex: string | undefined): string[] {
  const s = (sex ?? "").toLowerCase();
  return ALL_DOCTOR_IDS.filter((id) => {
    const allowed = SEX_RESTRICTED[id];
    return !allowed || allowed.includes(s);
  });
}

export function ConsiliumPage() {
  const { t, lang } = useI18n();
  const { data, engine, reload } = useStore();
  const [generating, setGenerating] = React.useState(false);
  const [progress, setProgress] = React.useState<ConsiliumProgress | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [cancelPromptOpen, setCancelPromptOpen] = React.useState(false);
  const [cancelling, setCancelling] = React.useState(false);
  const [cancelledNotice, setCancelledNotice] = React.useState(false);
  const [selectedDoctors, setSelectedDoctors] = React.useState<Set<string>>(new Set(ALL_DOCTOR_IDS));
  const pollRef = React.useRef<number | null>(null);

  const doctorIds = React.useMemo(
    () => availableDoctorIds(data?.profile?.sex),
    [data?.profile?.sex],
  );

  // Sync selection from profile panel once data loads; respect available doctors
  React.useEffect(() => {
    if (!data?.profile) return;
    const panel = (data.profile.specialist_panel ?? []).filter((id) => doctorIds.includes(id));
    setSelectedDoctors(panel.length > 0 ? new Set(panel) : new Set(doctorIds));
  }, [data?.profile, doctorIds]);

  const toggleDoctor = (id: string) => {
    setSelectedDoctors((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        if (next.size > 1) next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const stopPolling = React.useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = React.useCallback(() => {
    stopPolling();
    setGenerating(true);
    pollRef.current = window.setInterval(async () => {
      try {
        const p = await api.consiliumProgress();
        setProgress(p);
        if (p.state === "done" || p.state === "error" || p.state === "idle" || p.state === "cancelled") {
          stopPolling();
          setGenerating(false);
          if (p.state === "error") setError(p.error || t("consiliumError"));
          if (p.state === "cancelled") {
            setCancelledNotice(true);
            setError(null);
          }
          if (p.state === "done") await reload();
        }
      } catch {
        // transient poll failure — keep trying
      }
    }, 2500);
  }, [reload, stopPolling, t]);

  // Resume polling if a job is already running (user navigated away and back).
  React.useEffect(() => {
    let cancelled = false;
    api.consiliumProgress().then((p) => {
      if (!cancelled && p.state === "running") {
        setProgress(p);
        startPolling();
      }
    }).catch(() => {});
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [startPolling, stopPolling]);

  if (!data) return null;
  const status = data.consilium_status;
  const report = status?.claude_report || null;
  const specialists = report?.specialists || [];

  const generate = async () => {
    setError(null);
    setCancelledNotice(false);
    if (!engine?.enabled) {
      // No-key fallback: Claude Desktop / MCP pending flow.
      await api.consiliumRequestClaude();
      await reload();
      return;
    }
    try {
      const ids = selectedDoctors.size === ALL_DOCTOR_IDS.length ? undefined : [...selectedDoctors];
      const r = await api.consiliumGenerate(ids);
      if (!r.ok) throw new Error(r.error || "generation failed");
      setProgress(null);
      startPolling();
    } catch {
      setError(t("consiliumError"));
    }
  };

  const confirmCancel = async () => {
    setCancelling(true);
    try {
      await api.consiliumCancel();
      setCancelPromptOpen(false);
    } finally {
      setCancelling(false);
    }
  };

  const visitPackFilename = lang === "ru" ? "visit_pack_latest.html" : "visit_pack_latest_en.html";

  return (
    <div className="flex flex-1 flex-col gap-6 py-6">
      <ConsiliumHero
        selectedDoctors={[...selectedDoctors].map((id) => ({
          id,
          name: lang === "ru" ? DOCTOR_LABELS[id]?.ru : DOCTOR_LABELS[id]?.en,
        }))}
      />

      <div className="zh-rise zh-rise-1 flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          {doctorIds.map((id) => {
            const label = DOCTOR_LABELS[id];
            const active = selectedDoctors.has(id);
            return (
              <Button
                key={id}
                disabled={generating}
                onClick={() => toggleDoctor(id)}
                size="sm"
                variant={active ? "default" : "outline"}
                className="gap-1"
              >
                {label.emoji} {lang === "ru" ? label.ru : label.en}
              </Button>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button disabled={generating || selectedDoctors.size === 0} onClick={generate}>
            {generating ? <Spinner data-icon="inline-start" /> : <StethoscopeIcon data-icon="inline-start" />}
            {t("consiliumGenerate")}
            {selectedDoctors.size < doctorIds.length ? ` (${selectedDoctors.size})` : ""}
          </Button>
          {status?.has_claude_report ? (
            <ReportDownloadButton filename="consilium_ai.html" label={t("downloadConsilium")} />
          ) : null}
          <ReportDownloadButton
            filename={visitPackFilename}
            label={t("downloadVisitPack")}
            prepare={async (uiLang) => {
              const res = await api.visitPack(uiLang);
              return res.filename || (uiLang === "ru" ? "visit_pack_latest.html" : "visit_pack_latest_en.html");
            }}
            variant="secondary"
          />
        </div>
      </div>

      {report?.generated_at && !generating ? (
        <div className="zh-rise zh-rise-1 flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{t("consiliumReady")}</Badge>
          <span className="text-muted-foreground text-xs">
            {report.generated_at.replace("T", " ").slice(0, 16)}
          </span>
          {status?.has_claude_report ? (
            <ReportDownloadButton filename="consilium_ai.html" label={t("downloadConsilium")} />
          ) : null}
        </div>
      ) : null}

      {cancelledNotice && !generating ? (
        <Alert>
          <OctagonXIcon />
          <AlertTitle>{t("consiliumCancelled")}</AlertTitle>
        </Alert>
      ) : null}

      {error && (
        <Alert variant="destructive">
          <AlertTriangleIcon />
          <AlertTitle>{t("consiliumError")}</AlertTitle>
          <AlertDescription>
            <Button onClick={() => navigate("connect")} size="sm" variant="outline">
              {t("navConnect")}
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {generating ? (
        <div className="flex flex-col gap-4">
          <Card className="zh-breathe border-primary/40">
            <CardContent className="flex flex-col gap-4 py-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex items-center gap-3">
                  <Spinner className="text-primary" />
                  <p className="animate-pulse text-sm">{t("consiliumThinking")}</p>
                </div>
                <Button
                  className="w-full shrink-0 sm:w-auto"
                  onClick={() => setCancelPromptOpen(true)}
                  size="sm"
                  variant="outline"
                >
                  <OctagonXIcon data-icon="inline-start" />
                  {t("consiliumCancel")}
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(DOCTOR_LABELS)
                  .filter(([id]) => doctorIds.includes(id) && selectedDoctors.has(id))
                  .map(([id, label]) => {
                    const done = progress?.done_ids?.includes(id);
                    const failed = progress?.failed_ids?.includes(id);
                    return (
                      <Badge
                        className="gap-1.5 py-1"
                        key={id}
                        variant={done ? "default" : failed ? "destructive" : "outline"}
                      >
                        {done ? <CheckCircle2Icon className="size-3.5" /> : failed ? <AlertTriangleIcon className="size-3.5" /> : <Spinner className="size-3" />}
                        {label.emoji} {lang === "ru" ? label.ru : label.en}
                      </Badge>
                    );
                  })}
              </div>
            </CardContent>
          </Card>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-40" />
                </CardHeader>
                <CardContent className="flex flex-col gap-2">
                  <Skeleton className="h-3.5 w-full" />
                  <Skeleton className="h-3.5 w-5/6" />
                  <Skeleton className="h-3.5 w-4/6" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : specialists.length ? (
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
          {specialists.map((s, i) => (
            <SpecialistCard index={i} key={s.id || i} specialist={s} />
          ))}
        </div>
      ) : (
        <Empty className="zh-rise zh-rise-2 border border-dashed py-16">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <StethoscopeIcon />
            </EmptyMedia>
            <EmptyTitle>{t("consiliumEmpty")}</EmptyTitle>
            <EmptyDescription>
              {engine?.enabled ? t("consiliumIntro") : t("consiliumNoEngine")}
            </EmptyDescription>
          </EmptyHeader>
          {!engine?.enabled && (
            <Button onClick={() => navigate("connect")} size="sm" variant="outline">
              {t("navConnect")}
            </Button>
          )}
        </Empty>
      )}

      <ConsiliumCancelPrompt
        busy={cancelling}
        onConfirm={confirmCancel}
        onDismiss={() => setCancelPromptOpen(false)}
        open={cancelPromptOpen}
      />
    </div>
  );
}
