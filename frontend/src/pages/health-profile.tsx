import * as React from "react";
import { api, type Profile } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PlusIcon, Trash2Icon, FileTextIcon } from "lucide-react";

type Row = Record<string, string>;

// A generic, add/remove list editor for one profile section.
function ListEditor({
  title,
  rows,
  columns,
  onChange,
}: {
  title: string;
  rows: Row[];
  columns: { key: string; placeholder: string }[];
  onChange: (rows: Row[]) => void;
}) {
  const update = (i: number, key: string, val: string) => {
    const next = rows.map((r, idx) => (idx === i ? { ...r, [key]: val } : r));
    onChange(next);
  };
  const add = () => onChange([...rows, Object.fromEntries(columns.map((c) => [c.key, ""]))]);
  const remove = (i: number) => onChange(rows.filter((_, idx) => idx !== i));

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        <Button variant="ghost" size="sm" onClick={add}>
          <PlusIcon className="size-4" />
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {rows.length === 0 && <p className="text-sm text-muted-foreground">—</p>}
        {rows.map((row, i) => (
          <div key={i} className="flex items-center gap-2">
            {columns.map((c) => (
              <Input
                key={c.key}
                className="h-9"
                placeholder={c.placeholder}
                value={row[c.key] || ""}
                onChange={(e) => update(i, c.key, e.target.value)}
              />
            ))}
            <Button variant="ghost" size="sm" onClick={() => remove(i)}>
              <Trash2Icon className="size-4 text-muted-foreground" />
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

const REPORT_SECTIONS = [
  "diagnoses", "week", "allergies", "meds", "labs",
  "immunizations", "procedures", "family_history", "tasks", "questions",
];

export function HealthProfilePage() {
  const { lang } = useI18n();
  const ru = lang === "ru";
  const tr = (en: string, rus: string) => (ru ? rus : en);

  const [profile, setProfile] = React.useState<Profile | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [savedAt, setSavedAt] = React.useState<number | null>(null);
  const [sections, setSections] = React.useState<string[]>([
    "diagnoses", "week", "allergies", "meds", "labs", "tasks", "questions",
  ]);

  React.useEffect(() => {
    api.getProfile().then(setProfile).catch(() => setProfile(null));
  }, []);

  const patch = (key: keyof Profile, rows: Row[]) =>
    setProfile((p) => (p ? { ...p, [key]: rows } : p));

  const save = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      await api.patchProfile({
        allergies: profile.allergies,
        immunizations: profile.immunizations,
        procedures: profile.procedures,
        family_history: profile.family_history,
        emergency_contacts: profile.emergency_contacts,
        providers: profile.providers,
      });
      setSavedAt(Date.now());
    } finally {
      setSaving(false);
    }
  };

  const toggleSection = (s: string) =>
    setSections((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));

  const generateReport = async () => {
    const ordered = REPORT_SECTIONS.filter((s) => sections.includes(s));
    const res = await api.visitPack(lang, ordered);
    window.open(res.url, "_blank");
  };

  if (!profile) {
    return (
      <div className="flex flex-col gap-4 py-6">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const sectionLabel: Record<string, string> = {
    diagnoses: tr("Diagnoses", "Диагнозы"),
    week: tr("This week", "На неделе"),
    allergies: tr("Allergies", "Аллергии"),
    meds: tr("Medications", "Препараты"),
    labs: tr("Labs", "Анализы"),
    immunizations: tr("Immunizations", "Прививки"),
    procedures: tr("Procedures", "Процедуры"),
    family_history: tr("Family history", "Семейный анамнез"),
    tasks: tr("Tasks", "Задачи"),
    questions: tr("Questions", "Вопросы"),
  };

  return (
    <div className="flex flex-col gap-5 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{tr("Health profile", "Медицинский профиль")}</h1>
        <Button onClick={save} disabled={saving}>
          {saving ? tr("Saving…", "Сохраняю…") : savedAt ? tr("Saved ✓", "Сохранено ✓") : tr("Save", "Сохранить")}
        </Button>
      </div>

      <ListEditor
        title={tr("Allergies", "Аллергии")}
        rows={profile.allergies as unknown as Row[]}
        columns={[
          { key: "allergen", placeholder: tr("Allergen (e.g. Penicillin)", "Аллерген (напр. Пенициллин)") },
          { key: "reaction", placeholder: tr("Reaction", "Реакция") },
          { key: "severity", placeholder: tr("mild / moderate / severe", "лёгкая / средняя / тяжёлая") },
        ]}
        onChange={(r) => patch("allergies", r)}
      />
      <ListEditor
        title={tr("Immunizations", "Прививки")}
        rows={profile.immunizations as unknown as Row[]}
        columns={[
          { key: "name", placeholder: tr("Vaccine", "Вакцина") },
          { key: "date", placeholder: tr("Date (e.g. 2025-10)", "Дата (напр. 2025-10)") },
        ]}
        onChange={(r) => patch("immunizations", r)}
      />
      <ListEditor
        title={tr("Procedures & surgeries", "Процедуры и операции")}
        rows={profile.procedures as unknown as Row[]}
        columns={[
          { key: "name", placeholder: tr("Procedure", "Процедура") },
          { key: "date", placeholder: tr("Date", "Дата") },
          { key: "notes", placeholder: tr("Notes", "Заметки") },
        ]}
        onChange={(r) => patch("procedures", r)}
      />
      <ListEditor
        title={tr("Family history", "Семейный анамнез")}
        rows={profile.family_history as unknown as Row[]}
        columns={[
          { key: "relation", placeholder: tr("Relation (e.g. Mother)", "Родство (напр. Мать)") },
          { key: "condition", placeholder: tr("Condition", "Заболевание") },
        ]}
        onChange={(r) => patch("family_history", r)}
      />
      <ListEditor
        title={tr("Emergency contacts", "Экстренные контакты")}
        rows={profile.emergency_contacts as unknown as Row[]}
        columns={[
          { key: "name", placeholder: tr("Name", "Имя") },
          { key: "relation", placeholder: tr("Relation", "Родство") },
          { key: "phone", placeholder: tr("Phone", "Телефон") },
        ]}
        onChange={(r) => patch("emergency_contacts", r)}
      />
      <ListEditor
        title={tr("Doctors & pharmacies", "Врачи и аптеки")}
        rows={profile.providers as unknown as Row[]}
        columns={[
          { key: "name", placeholder: tr("Name", "Имя / название") },
          { key: "specialty", placeholder: tr("Specialty", "Специальность") },
          { key: "phone", placeholder: tr("Phone", "Телефон") },
        ]}
        onChange={(r) => patch("providers", r)}
      />

      <Card>
        <CardHeader className="pb-2">
          <h3 className="text-sm font-semibold">{tr("Build doctor report", "Собрать отчёт для врача")}</h3>
          <p className="text-xs text-muted-foreground">
            {tr("Pick what to include, then open a printable report.", "Выберите, что включить, и откройте отчёт для печати.")}
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            {REPORT_SECTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => toggleSection(s)}
                className={
                  "rounded-full border px-3 py-1.5 text-xs transition-colors " +
                  (sections.includes(s)
                    ? "border-primary bg-primary/15 text-primary"
                    : "border-border bg-background hover:bg-muted")
                }
              >
                {sectionLabel[s]}
              </button>
            ))}
          </div>
          <Button className="w-max" onClick={generateReport} disabled={sections.length === 0}>
            <FileTextIcon className="mr-1.5 size-4" />
            {tr("Open report", "Открыть отчёт")}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
