import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { cn } from "@/lib/utils";
import { findLabChart, LabDetailSheet } from "@/components/lab-detail-sheet";
import { HealthSystemSheet } from "@/components/health-system-sheet";
import { TaskStatusControls } from "@/components/task-status-controls";
import { ReportDownloadButton } from "@/components/report-download-button";
import { useI18n } from "@/lib/i18n";
import { navigate, useStore } from "@/lib/store";
import { api } from "@/lib/api";
import { SymptomAnswer } from "@/components/symptom-answer";
import { SymptomSavePrompt } from "@/components/symptom-save-prompt";
import type { LabChart, SystemCard } from "@/lib/types";
import {
  ArrowRightIcon,
  FileUpIcon,
  FlaskConicalIcon,
  SaveIcon,
  SparklesIcon,
  StethoscopeIcon,
} from "lucide-react";
import { ImportLabsSheet } from "@/components/import-labs-sheet";
import type { ExtractedLabRow } from "@/lib/api";

const SYMPTOM_CHIPS_BY_LANG: Record<string, string[]> = {
  ru: ["усталость", "головная боль", "плохо сплю", "боль в спине", "тошнота"],
  en: ["tired", "headache", "poor sleep", "back pain", "nausea"],
};

const STATUS_DOT: Record<string, string> = {
  good: "bg-status-good",
  caution: "bg-status-warn",
  bad: "bg-status-bad",
  warn: "bg-status-warn",
};

function greetingKey(): "greetingMorning" | "greetingDay" | "greetingEvening" {
  const h = new Date().getHours();
  if (h < 12) return "greetingMorning";
  if (h < 18) return "greetingDay";
  return "greetingEvening";
}

export function TodayPage() {
  const { t, lang } = useI18n();
  const {
    data,
    engine,
    reload,
    symptomAsking,
    symptomJob,
    symptomSavePromptPending,
    clearSymptomSavePrompt,
    startSymptomAsk,
  } = useStore();
  const [question, setQuestion] = React.useState("");
  const [attachments, setAttachments] = React.useState<{ name: string; path: string }[]>([]);
  const [uploading, setUploading] = React.useState(false);
  const [systemOpen, setSystemOpen] = React.useState<SystemCard | null>(null);
  const [labDetail, setLabDetail] = React.useState<LabChart | null>(null);
  const [savePromptOpen, setSavePromptOpen] = React.useState(false);
  const [savingHistory, setSavingHistory] = React.useState(false);
  const [justSaved, setJustSaved] = React.useState(false);
  const [saveError, setSaveError] = React.useState("");
  const [importing, setImporting] = React.useState(false);
  const [importError, setImportError] = React.useState("");
  const [importedRows, setImportedRows] = React.useState<ExtractedLabRow[]>([]);
  const [importSheetOpen, setImportSheetOpen] = React.useState(false);
  const fileRef = React.useRef<HTMLInputElement>(null);

  const openLabByCode = React.useCallback(
    (code: string) => {
      const c = findLabChart(data?.charts?.lab_charts, code);
      if (c) setLabDetail(c);
    },
    [data],
  );

  React.useEffect(() => {
    const qa = data?.symptom_qa;
    if (symptomSavePromptPending && qa?.has_answer && qa.answer && !qa.answer.saved_to_history) {
      setSavePromptOpen(true);
      clearSymptomSavePrompt();
    }
  }, [symptomSavePromptPending, data?.symptom_qa, clearSymptomSavePrompt]);

  if (!data) return null;
  const firstName = data.profile.display_name.split(" ")[0];
  const brief = data.weekly_brief;
  const systems = data.charts?.systems || [];
  const tasks = (data.tasks_open || []).slice(0, 4);
  const qa = data.symptom_qa;
  const attachmentPaths = attachments.map((a) => a.path);

  const onFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setUploading(true);
    try {
      const res = await api.uploadFiles(Array.from(files));
      setAttachments((prev) => [...prev, ...res.files]);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const extractAndImport = async () => {
    if (!attachments.length) return;
    setImporting(true);
    setImportError("");
    try {
      const res = await api.extractLabsFromFile(attachments[0].path);
      if (!res.ok || !res.rows?.length) {
        setImportError(t(res.rows?.length === 0 ? "importLabsNoResults" : "importLabsError"));
      } else {
        setImportedRows(res.rows);
        setImportSheetOpen(true);
      }
    } catch {
      setImportError(t("importLabsError"));
    } finally {
      setImporting(false);
    }
  };

  const askSymptom = async (mode: "quick" | "consilium") => {
    let q = question.trim();
    const paths = attachmentPaths;
    // Allow asking with just an attachment (no typed text): send a default prompt.
    if (q.length < 2 && paths.length === 0) return;
    if (q.length < 2) q = lang === "ru" ? "Посмотрите, пожалуйста, этот файл" : "Please review this file";
    setJustSaved(false);
    setQuestion("");
    setAttachments([]);
    try {
      await startSymptomAsk(mode, q, paths);
    } catch {
      /* error surfaced via symptomJob */
    }
  };

  const askFullConsilium = async () => {
    if (engine?.enabled) {
      try {
        await api.consiliumGenerate();
      } catch {
        /* consilium page will show error */
      }
    }
    navigate("consilium");
  };

  const saveMemory = async () => {
    const q = qa?.answer?.question || question;
    const paths = qa?.answer?.attachments || attachmentPaths;
    setSavingHistory(true);
    setSaveError("");
    try {
      await api.saveSymptomMemory(q, paths);
      await reload();
      setJustSaved(true);
      setSavePromptOpen(true);
    } catch {
      setSaveError(t("saveMemoError"));
    } finally {
      setSavingHistory(false);
    }
  };

  const sourceNote = (s: SystemCard) => {
    const src = s.explain?.sources?.[0];
    if (!src) return null;
    return `${src.file || "health.db"} · ${src.test} · ${src.date}`;
  };

  return (
    <div className="flex flex-1 flex-col gap-6 py-6">
      <div className="zh-rise flex flex-col gap-1">
        <h1 className="font-semibold text-xl leading-tight">
          {t(greetingKey())}, {firstName}!
        </h1>
        <p className="text-base text-muted-foreground">
          {lang === "ru" ? brief?.headline_ru : brief?.headline_en}
        </p>
      </div>

      {/* Body systems — tap for explainer sheet */}
      <div className="zh-rise zh-rise-1 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {systems.map((s) => (
          <Card
            className="cursor-pointer gap-1 py-3 transition-all hover:-translate-y-0.5 hover:shadow-md"
            key={s.id}
            onClick={() => setSystemOpen(s)}
          >
            <CardHeader className="px-3 pb-0">
              <CardTitle className="flex items-center gap-2 text-sm">
                <span
                  className={cn("size-2 shrink-0 rounded-full", STATUS_DOT[s.status] || "bg-muted-foreground")}
                />
                <span className="truncate">{lang === "ru" ? s.title : s.title_en}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pt-1">
              <p className="text-muted-foreground text-xs">{t("sysTapToExplain")}</p>
              {sourceNote(s) ? (
                <p className="mt-1 truncate text-[10px] text-muted-foreground/80">{sourceNote(s)}</p>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>

      <HealthSystemSheet
        onOpenChange={(o) => !o && setSystemOpen(null)}
        onOpenLab={openLabByCode}
        open={!!systemOpen}
        system={systemOpen}
      />
      <LabDetailSheet chart={labDetail} onOpenChange={(o) => !o && setLabDetail(null)} open={!!labDetail} />

      <div className="zh-rise zh-rise-2 grid grid-cols-1 gap-4 lg:grid-cols-5">
        {/* Symptom Q&A */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <SparklesIcon className="size-4 text-primary" />
              {t("askSymptomTitle")}
            </CardTitle>
            <CardDescription>{symptomAsking ? t("symptomThinking") : t("askSymptomHint")}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-wrap gap-1.5">
              {(SYMPTOM_CHIPS_BY_LANG[lang] || SYMPTOM_CHIPS_BY_LANG.en).map((chip) => (
                <Badge
                  className="cursor-pointer transition-colors hover:bg-accent"
                  key={chip}
                  onClick={() => setQuestion((q) => (q ? `${q}, ${chip}` : chip))}
                  variant="outline"
                >
                  {chip}
                </Badge>
              ))}
            </div>
            <Textarea
              className="min-h-16 resize-none"
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={t("askSymptomPh")}
              value={question}
            />
            <div className="flex flex-wrap items-center gap-2">
              <input
                className="hidden"
                multiple
                onChange={(e) => void onFiles(e.target.files)}
                ref={fileRef}
                type="file"
              />
              <Button disabled={uploading} onClick={() => fileRef.current?.click()} size="sm" variant="outline">
                {uploading ? <Spinner data-icon="inline-start" /> : <FileUpIcon data-icon="inline-start" />}
                {t("symptomUpload")}
              </Button>
              {attachments.map((a) => (
                <Badge key={a.path} variant="secondary">
                  {a.name}
                </Badge>
              ))}
            </div>
            {attachments.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <p className="text-xs text-muted-foreground">{t("uploadHint")}</p>
                {engine?.enabled && (
                  <Button
                    disabled={importing}
                    onClick={() => void extractAndImport()}
                    size="sm"
                    variant="outline"
                  >
                    {importing ? <Spinner data-icon="inline-start" /> : <FlaskConicalIcon data-icon="inline-start" />}
                    {importing ? t("importLabsExtracting") : t("importLabsBtn")}
                  </Button>
                )}
                {importError && <p className="text-xs text-destructive">{importError}</p>}
              </div>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <Button
                disabled={symptomAsking || !engine?.enabled || (question.trim().length < 2 && attachments.length === 0)}
                onClick={() => void askSymptom("quick")}
              >
                {symptomAsking && <Spinner data-icon="inline-start" />}
                {t("symptomAsk")}
              </Button>
              <Button
                disabled={symptomAsking || (question.trim().length < 2 && attachments.length === 0) || !engine?.enabled}
                onClick={() => void askSymptom("consilium")}
                variant="secondary"
              >
                <StethoscopeIcon data-icon="inline-start" />
                {t("symptomConsilium")}
              </Button>
            </div>
            {!engine?.enabled && (
              <p className="text-xs text-muted-foreground">
                {lang === "ru"
                  ? "Добавьте API-ключ OpenRouter на странице «Подключение», чтобы задавать вопросы."
                  : "Add your OpenRouter API key on the Connect page to ask questions."}
              </p>
            )}
            {symptomAsking ? (
              <div className="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2">
                <Spinner className="size-4 text-primary" />
                <p className="animate-pulse text-muted-foreground text-sm">{t("symptomThinking")}</p>
              </div>
            ) : null}
            {symptomJob?.state === "error" ? (
              <p className="text-destructive text-sm">
                {(() => {
                  const e = symptomJob.error || "";
                  if (e.includes("Errno 8") || e.includes("nodename") || e.includes("servname") || e.includes("network") || e.includes("ConnectionError") || e.includes("ConnectTimeout")) {
                    return lang === "ru"
                      ? "Нет соединения с сервером ИИ. Проверьте интернет-подключение."
                      : "Could not reach the AI server. Check your internet connection.";
                  }
                  return e || t("consiliumError");
                })()}
              </p>
            ) : null}
            {qa?.has_answer && qa.answer && !symptomAsking && (
              <>
                <SymptomAnswer answer={qa.answer} />
                <div className="flex flex-col gap-2 border-t pt-3">
                  {qa.answer.saved_to_history ? (
                    <Badge className="w-fit" variant="secondary">
                      {t("symptomSavedBadge")}
                    </Badge>
                  ) : (
                    <>
                      <Button
                        className="w-full"
                        disabled={savingHistory}
                        onClick={() => void saveMemory()}
                        variant="default"
                      >
                        {savingHistory ? <Spinner data-icon="inline-start" /> : <SaveIcon data-icon="inline-start" />}
                        {t("symptomSaveToDb")}
                      </Button>
                      {saveError && <p className="text-sm text-destructive">{saveError}</p>}
                    </>
                  )}
                  <ReportDownloadButton
                    className="w-full"
                    filename={lang === "ru" ? "symptom_session.html" : "symptom_session_en.html"}
                    label={t("symptomReport")}
                    prepare={async (uiLang) => {
                      const q = qa.answer?.question || question;
                      const paths = qa.answer?.attachments || attachmentPaths;
                      const res = await api.symptomReport(q, paths, uiLang);
                      return res.filename || (uiLang === "ru" ? "symptom_session.html" : "symptom_session_en.html");
                    }}
                    variant="outline"
                  />
                  <Button
                    className="w-full"
                    disabled={!engine?.enabled}
                    onClick={() => void askFullConsilium()}
                    variant="secondary"
                  >
                    <StethoscopeIcon data-icon="inline-start" />
                    {t("symptomAskConsilium")}
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Right column */}
        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card className="zh-breathe border-primary/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <StethoscopeIcon className="size-4 text-primary" />
                {t("consiliumTitle")}
              </CardTitle>
              <CardDescription>
                {engine?.enabled ? t("consiliumIntro") : t("consiliumNoEngine")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" onClick={() => navigate("consilium")} variant="default">
                {t("consiliumGenerate")}
                <ArrowRightIcon data-icon="inline-end" />
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("openTasks")}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {tasks.length === 0 ? (
                <Empty className="py-4">
                  <EmptyHeader>
                    <EmptyTitle className="text-sm">{t("noTasks")}</EmptyTitle>
                    <EmptyDescription> </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : (
                tasks.map((task) => (
                  <div className="flex flex-col gap-2 border-b border-border/50 pb-3 last:border-0" key={task.id}>
                    <span className="text-sm leading-snug">{task.title_ru}</span>
                    <TaskStatusControls compact status={task.status} taskId={task.id} />
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <ImportLabsSheet
        onOpenChange={setImportSheetOpen}
        onSaved={() => {
          setAttachments([]);
          void reload();
        }}
        open={importSheetOpen}
        rows={importedRows}
      />

      <SymptomSavePrompt
        onDismiss={() => {
          setSavePromptOpen(false);
          setJustSaved(false);
        }}
        onSave={saveMemory}
        open={savePromptOpen}
        saved={justSaved}
        saving={savingHistory}
      />

    </div>
  );
}
