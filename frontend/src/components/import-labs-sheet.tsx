import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { useI18n } from "@/lib/i18n";
import { api } from "@/lib/api";
import type { ExtractedLabRow } from "@/lib/api";
import { CheckIcon, Trash2Icon } from "lucide-react";

type EditableRow = ExtractedLabRow & { _id: number; _skip?: boolean };

function RowEditor({
  row,
  onChange,
  onDelete,
}: {
  row: EditableRow;
  onChange: (patch: Partial<ExtractedLabRow>) => void;
  onDelete: () => void;
}) {
  return (
    <div className="grid grid-cols-[1fr_auto] gap-2 border-b border-border/50 pb-3">
      <div className="flex flex-col gap-2">
        <Input
          className="h-7 text-sm font-medium"
          value={row.test_name}
          onChange={(e) => onChange({ test_name: e.target.value })}
          placeholder="Test name"
        />
        <div className="grid grid-cols-3 gap-1.5">
          <Input
            className="h-7 text-xs"
            type="number"
            step="any"
            placeholder="Value"
            value={row.value ?? ""}
            onChange={(e) =>
              onChange({ value: e.target.value ? parseFloat(e.target.value) : null })
            }
          />
          <Input
            className="h-7 text-xs"
            placeholder="Unit"
            value={row.unit ?? ""}
            onChange={(e) => onChange({ unit: e.target.value })}
          />
          <Input
            className="h-7 text-xs"
            type="date"
            value={row.sample_date}
            onChange={(e) => onChange({ sample_date: e.target.value })}
          />
        </div>
        <div className="flex gap-1.5">
          <Input
            className="h-7 text-xs"
            type="number"
            step="any"
            placeholder="Ref min"
            value={row.ref_low ?? ""}
            onChange={(e) =>
              onChange({ ref_low: e.target.value ? parseFloat(e.target.value) : null })
            }
          />
          <Input
            className="h-7 text-xs"
            type="number"
            step="any"
            placeholder="Ref max"
            value={row.ref_high ?? ""}
            onChange={(e) =>
              onChange({ ref_high: e.target.value ? parseFloat(e.target.value) : null })
            }
          />
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7 self-start text-muted-foreground hover:text-destructive"
        onClick={onDelete}
      >
        <Trash2Icon className="size-3.5" />
      </Button>
    </div>
  );
}

export function ImportLabsSheet({
  open,
  rows: initialRows,
  onOpenChange,
  onSaved,
}: {
  open: boolean;
  rows: ExtractedLabRow[];
  onOpenChange: (v: boolean) => void;
  onSaved: () => void;
}) {
  const { t } = useI18n();
  const [rows, setRows] = React.useState<EditableRow[]>([]);
  const [saving, setSaving] = React.useState(false);
  const [saved, setSaved] = React.useState(false);
  const [saveError, setSaveError] = React.useState("");

  React.useEffect(() => {
    if (open) {
      setRows(initialRows.map((r, i) => ({ ...r, _id: i })));
      setSaved(false);
      setSaveError("");
    }
  }, [open, initialRows]);

  const update = (id: number, patch: Partial<ExtractedLabRow>) => {
    setRows((prev) => prev.map((r) => (r._id === id ? { ...r, ...patch } : r)));
  };

  const remove = (id: number) => {
    setRows((prev) => prev.filter((r) => r._id !== id));
  };

  const handleSave = async () => {
    const valid = rows.filter((r) => r.test_name.trim() && r.sample_date);
    if (!valid.length) return;
    setSaving(true);
    setSaveError("");
    let savedCount = 0;
    for (const row of valid) {
      try {
        const res = await api.addLabResult({
          test_name: row.test_name.trim(),
          value: row.value ?? null,
          value_text: row.value_text ?? undefined,
          unit: row.unit ?? "",
          sample_date: row.sample_date,
          ref_low: row.ref_low ?? null,
          ref_high: row.ref_high ?? null,
        });
        if (res.ok) savedCount++;
      } catch {
        // skip duplicates / errors for individual rows
      }
    }
    setSaving(false);
    if (savedCount > 0) {
      setSaved(true);
      onSaved();
      setTimeout(() => onOpenChange(false), 1000);
    } else {
      setSaveError("All rows were duplicates or failed to save.");
    }
  };

  const activeRows = rows.filter((r) => !r._skip);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex flex-col gap-4 overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t("importLabsTitle")}</SheetTitle>
          <SheetDescription>{t("importLabsSubtitle")}</SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-3">
          {activeRows.map((row) => (
            <RowEditor
              key={row._id}
              row={row}
              onChange={(patch) => update(row._id, patch)}
              onDelete={() => remove(row._id)}
            />
          ))}
        </div>

        {saveError && <p className="text-sm text-destructive">{saveError}</p>}

        <Button
          className="w-full"
          disabled={saving || saved || activeRows.length === 0}
          onClick={() => void handleSave()}
        >
          {saving ? (
            <Spinner data-icon="inline-start" />
          ) : saved ? (
            <CheckIcon data-icon="inline-start" />
          ) : null}
          {saved
            ? t("importLabsSaved")
            : `${t("importLabsSaveAll")} ${activeRows.length > 0 ? `(${activeRows.length})` : ""}`}
        </Button>

        {activeRows.length > 0 && (
          <p className="text-center text-xs text-muted-foreground">
            {activeRows.length} {activeRows.length === 1 ? "result" : "results"} ·{" "}
            <Badge variant="outline" className="text-xs">
              {activeRows[0]?.sample_date}
            </Badge>
          </p>
        )}
      </SheetContent>
    </Sheet>
  );
}
