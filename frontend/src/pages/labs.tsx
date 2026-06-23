import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { findLabChart, LabDetailSheet, labRowToCode } from "@/components/lab-detail-sheet";
import { labDisplayName, labFreshnessMessage } from "@/lib/clinical-labels";
import { flagInfo } from "@/lib/lab-flag";
import { useI18n } from "@/lib/i18n";
import { useStore } from "@/lib/store";
import { api } from "@/lib/api";
import { PlusIcon, CheckIcon } from "lucide-react";
import type { LabChart } from "@/lib/types";

function today() {
  return new Date().toISOString().slice(0, 10);
}

function LabFlagBadge({ flag }: { flag: string | null | undefined }) {
  const fi = flagInfo(flag);
  if (!fi.label) return null;
  return <Badge variant={fi.variant} className={fi.className}>{fi.label}</Badge>;
}

function AddLabSheet({
  open,
  onOpenChange,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSaved: () => void;
}) {
  const { t } = useI18n();
  const [name, setName] = React.useState("");
  const [date, setDate] = React.useState(today);
  const [value, setValue] = React.useState("");
  const [unit, setUnit] = React.useState("");
  const [refLow, setRefLow] = React.useState("");
  const [refHigh, setRefHigh] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [saved, setSaved] = React.useState(false);
  const [error, setError] = React.useState("");

  const reset = () => {
    setName(""); setDate(today()); setValue(""); setUnit("");
    setRefLow(""); setRefHigh(""); setSaved(false); setError("");
  };

  const handleSave = async () => {
    if (!name.trim() || !date) return;
    setSaving(true);
    setError("");
    try {
      const res = await api.addLabResult({
        test_name: name.trim(),
        value: value ? parseFloat(value) : null,
        unit: unit.trim() || undefined,
        sample_date: date,
        ref_low: refLow ? parseFloat(refLow) : null,
        ref_high: refHigh ? parseFloat(refHigh) : null,
      });
      if (res.ok) {
        setSaved(true);
        onSaved();
        setTimeout(() => { onOpenChange(false); reset(); }, 1200);
      } else if (res.error === "duplicate") {
        setError(t("addLabDuplicate"));
      } else {
        setError(t("addLabError"));
      }
    } catch {
      setError(t("addLabError"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) reset(); }}>
      <SheetContent className="flex flex-col gap-5 overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t("addLabTitle")}</SheetTitle>
        </SheetHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">{t("addLabTestName")} *</label>
            <Input
              placeholder={t("addLabTestNamePh")}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">{t("addLabDate")} *</label>
            <Input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">{t("addLabValue")}</label>
              <Input
                placeholder={t("addLabValuePh")}
                type="number"
                step="any"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">{t("addLabUnit")}</label>
              <Input
                placeholder={t("addLabUnitPh")}
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">{t("addLabRefLow")}</label>
              <Input
                placeholder="—"
                type="number"
                step="any"
                value={refLow}
                onChange={(e) => setRefLow(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">{t("addLabRefHigh")}</label>
              <Input
                placeholder="—"
                type="number"
                step="any"
                value={refHigh}
                onChange={(e) => setRefHigh(e.target.value)}
              />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button
            className="w-full"
            disabled={saving || !name.trim() || !date}
            onClick={() => void handleSave()}
          >
            {saving ? (
              <Spinner data-icon="inline-start" />
            ) : saved ? (
              <CheckIcon data-icon="inline-start" />
            ) : (
              <PlusIcon data-icon="inline-start" />
            )}
            {saved ? t("addLabSaved") : t("addLabSave")}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export function LabsPage() {
  const { t, lang } = useI18n();
  const { data, reload } = useStore();
  const [detail, setDetail] = React.useState<LabChart | null>(null);
  const [addOpen, setAddOpen] = React.useState(false);

  if (!data) return null;

  const charts = data.charts?.lab_charts || [];
  const labs = [...(data.lab_results || [])].sort((a, b) =>
    (b.sample_date || "").localeCompare(a.sample_date || ""),
  );

  const openLab = (code: string) => {
    const c = findLabChart(charts, code);
    if (c) setDetail(c);
  };

  return (
    <div className="flex flex-1 flex-col gap-6 py-6">
      <div className="zh-rise flex items-center justify-between gap-4">
        <h1 className="font-semibold text-xl leading-tight">{t("labsTable")}</h1>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          <PlusIcon data-icon="inline-start" />
          {t("addLabBtn")}
        </Button>
      </div>
      <p className="text-muted-foreground text-sm">{t("labsTapHint")}</p>

      <LabDetailSheet chart={detail} onOpenChange={(o) => !o && setDetail(null)} open={!!detail} />
      <AddLabSheet open={addOpen} onOpenChange={setAddOpen} onSaved={() => void reload()} />

      <Card className="zh-rise zh-rise-1 py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">{t("thDate")}</TableHead>
                <TableHead>{t("thTest")}</TableHead>
                <TableHead>{t("thValue")}</TableHead>
                <TableHead className="hidden sm:table-cell">{t("thRef")}</TableHead>
                <TableHead className="hidden pr-6 md:table-cell">{t("thFresh")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {labs.map((lab) => {
                const hasChart = !!findLabChart(charts, labRowToCode(lab));
                const clickable = hasChart;
                // Numeric value with no flag = sub-component of a panel test (e.g. QuantiFERON sub-tests)
                const isComponent = lab.flag == null && lab.value != null;
                return (
                  <TableRow
                    className={clickable ? "cursor-pointer hover:bg-muted/50" : undefined}
                    key={lab.id}
                    onClick={() => { if (clickable) openLab(labRowToCode(lab)); }}
                  >
                    <TableCell className="pl-6 text-muted-foreground tabular-nums">
                      {lab.sample_date}
                    </TableCell>
                    <TableCell className="font-medium">{labDisplayName(lab, lang)}</TableCell>
                    <TableCell>
                      <span className="flex items-center gap-2 tabular-nums">
                        {lab.value != null ? `${lab.value} ${lab.unit ?? ""}`.trim() : (lab.value_text ?? "—")}
                        {isComponent
                          ? <Badge variant="outline" className="text-[10px] text-muted-foreground border-muted-foreground/30">{lang === "ru" ? "Компонент" : "Component"}</Badge>
                          : <LabFlagBadge flag={lab.flag} />}
                      </span>
                    </TableCell>
                    <TableCell className="hidden text-muted-foreground tabular-nums sm:table-cell">
                      {lab.ref_low != null && lab.ref_high != null
                        ? `${lab.ref_low}–${lab.ref_high}`
                        : "—"}
                    </TableCell>
                    <TableCell className="hidden pr-6 text-muted-foreground text-xs md:table-cell">
                      {labFreshnessMessage(lab.freshness, lang)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
