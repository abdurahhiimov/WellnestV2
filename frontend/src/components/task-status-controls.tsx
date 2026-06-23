import * as React from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useI18n, type StringKey } from "@/lib/i18n";
import { useStore } from "@/lib/store";
import { ChevronDownIcon, Trash2Icon } from "lucide-react";

export type TaskStatus = "not_started" | "in_progress" | "done";

const STATUSES: TaskStatus[] = ["not_started", "in_progress", "done"];

const PILL: Record<TaskStatus, string> = {
  not_started: "border-border bg-muted/90 text-muted-foreground hover:bg-muted",
  in_progress: "border-status-warn/50 bg-status-warn text-white border-status-warn shadow-[0_0_16px_oklch(0.75_0.14_85_/_25%)]",
  done: "border-status-good/50 bg-status-good text-white border-status-good shadow-[0_0_16px_oklch(0.72_0.12_155_/_25%)]",
};

const OPTION: Record<TaskStatus, string> = {
  not_started: "border-border bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground",
  in_progress: "border-status-warn/40 bg-status-warn/20 text-foreground hover:bg-status-warn/35",
  done: "border-status-good/40 bg-status-good/20 text-foreground hover:bg-status-good/35",
};

const STATUS_KEYS: Record<TaskStatus, StringKey> = {
  not_started: "taskNotStarted",
  in_progress: "taskInProgress",
  done: "taskDone",
};

function normalizeStatus(s: string): TaskStatus {
  if (s === "open" || s === "dismissed") return "not_started";
  if (s === "completed") return "done";
  if (STATUSES.includes(s as TaskStatus)) return s as TaskStatus;
  return "not_started";
}

export function TaskStatusControls({
  taskId,
  status,
  compact,
}: {
  taskId: number;
  status: string;
  compact?: boolean;
}) {
  const { t } = useI18n();
  const { reload } = useStore();
  const [busy, setBusy] = React.useState(false);
  const [open, setOpen] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState(false);
  const rootRef = React.useRef<HTMLDivElement>(null);
  const current = normalizeStatus(status);

  React.useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false);
        setConfirmDelete(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        setConfirmDelete(false);
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const setStatus = async (next: TaskStatus) => {
    if (next === current) {
      setOpen(false);
      return;
    }
    setBusy(true);
    setOpen(false);
    try {
      await api.updateTaskStatus(taskId, next);
      await reload();
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await api.deleteTask(taskId);
      setConfirmDelete(false);
      setOpen(false);
      await reload();
    } finally {
      setBusy(false);
    }
  };

  const otherStatuses = STATUSES.filter((s) => s !== current);

  return (
    <div className={cn("relative", compact ? "w-full max-w-[200px]" : "inline-block")} ref={rootRef}>
      <button
        className={cn(
          "zh-task-pill flex h-8 w-full min-w-[9rem] items-center justify-between gap-2 rounded-full border px-3 text-xs font-medium transition-all",
          PILL[current],
          open && "ring-2 ring-primary/40",
          busy && "pointer-events-none opacity-70",
        )}
        disabled={busy}
        onClick={(e) => {
          e.stopPropagation();
          setConfirmDelete(false);
          setOpen((v) => !v);
        }}
        type="button"
      >
        <span className="truncate">{t(STATUS_KEYS[current])}</span>
        {busy ? (
          <Spinner className="size-3.5 shrink-0" />
        ) : (
          <ChevronDownIcon
            className={cn("size-3.5 shrink-0 transition-transform duration-300", open && "rotate-180")}
          />
        )}
      </button>

      {open ? (
        <div
          className="zh-task-menu absolute top-[calc(100%+6px)] right-0 z-50 flex min-w-[11rem] flex-col gap-1.5 rounded-xl border border-border/80 bg-popover/95 p-1.5 shadow-lg backdrop-blur-sm"
          onClick={(e) => e.stopPropagation()}
        >
          {otherStatuses.map((key, i) => (
            <button
              className={cn(
                "zh-task-option flex h-8 w-full items-center rounded-lg border px-3 text-left text-xs font-medium transition-colors",
                OPTION[key],
              )}
              key={key}
              onClick={() => void setStatus(key)}
              style={{ animationDelay: `${0.04 + i * 0.06}s` }}
              type="button"
            >
              {t(STATUS_KEYS[key])}
            </button>
          ))}

          {!confirmDelete ? (
            <button
              className="zh-task-option flex h-8 w-full items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 text-left text-destructive text-xs font-medium transition-colors hover:bg-destructive/20"
              onClick={() => setConfirmDelete(true)}
              style={{ animationDelay: `${0.04 + otherStatuses.length * 0.06}s` }}
              type="button"
            >
              <Trash2Icon className="size-3.5" />
              {t("taskDelete")}
            </button>
          ) : (
            <div
              className="zh-task-option flex flex-col gap-2 rounded-lg border border-destructive/40 bg-destructive/5 p-2.5"
              style={{ animationDelay: `${0.04 + otherStatuses.length * 0.06}s` }}
            >
              <p className="font-medium text-xs leading-snug">{t("taskDeleteConfirm")}</p>
              <div className="flex gap-1.5">
                <Button
                  className="h-7 flex-1 text-xs"
                  disabled={busy}
                  onClick={() => void remove()}
                  size="sm"
                  variant="destructive"
                >
                  {t("taskDeleteYes")}
                </Button>
                <Button
                  className="h-7 flex-1 text-xs"
                  disabled={busy}
                  onClick={() => setConfirmDelete(false)}
                  size="sm"
                  variant="outline"
                >
                  {t("taskDeleteCancel")}
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
