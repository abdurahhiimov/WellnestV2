import * as React from "react";
import { api, type Profile } from "@/lib/api";
import { useI18n, type Lang } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { HeartPulseIcon, CheckIcon } from "lucide-react";

// Common conditions, mapped to catalog condition codes. Bilingual labels.
const CONDITIONS: { code: string; en: string; ru: string }[] = [
  { code: "hypertension", en: "High blood pressure", ru: "Высокое давление" },
  { code: "high_cholesterol", en: "High cholesterol", ru: "Высокий холестерин" },
  { code: "diabetes", en: "Diabetes / pre-diabetes", ru: "Диабет / преддиабет" },
  { code: "hypothyroidism", en: "Thyroid problem", ru: "Проблемы щитовидной железы" },
  { code: "menopause", en: "Menopause", ru: "Менопауза" },
  { code: "osteoporosis", en: "Osteoporosis / weak bones", ru: "Остеопороз / слабые кости" },
  { code: "arthritis", en: "Arthritis / joint pain", ru: "Артрит / боли в суставах" },
  { code: "anemia", en: "Anemia / low iron", ru: "Анемия / низкое железо" },
  { code: "gerd", en: "Reflux / stomach issues", ru: "Рефлюкс / желудок" },
  { code: "anxiety", en: "Anxiety / depression", ru: "Тревога / депрессия" },
  { code: "migraine", en: "Migraines / headaches", ru: "Мигрени / головные боли" },
  { code: "heart_disease", en: "Heart disease", ru: "Болезнь сердца" },
  { code: "prostate", en: "Prostate issues", ru: "Проблемы с простатой" },
];

const CONCERN_TAGS: { tag: string; en: string; ru: string }[] = [
  { tag: "sleep", en: "Sleep", ru: "Сон" },
  { tag: "fatigue", en: "Fatigue / energy", ru: "Усталость / энергия" },
  { tag: "weight", en: "Weight", ru: "Вес" },
  { tag: "mood", en: "Mood / stress", ru: "Настроение / стресс" },
  { tag: "heart", en: "Heart / blood pressure", ru: "Сердце / давление" },
  { tag: "digestion", en: "Digestion", ru: "Пищеварение" },
  { tag: "joints", en: "Joints / bones", ru: "Суставы / кости" },
  { tag: "memory", en: "Memory / focus", ru: "Память / концентрация" },
  { tag: "hormones", en: "Hormones", ru: "Гормоны" },
];

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-4 py-2 text-sm transition-colors",
        active
          ? "border-primary bg-primary/15 text-primary"
          : "border-border bg-background hover:bg-muted",
      )}
    >
      {active && <CheckIcon className="mr-1.5 inline size-3.5" />}
      {children}
    </button>
  );
}

type Draft = {
  language_primary: Lang;
  display_name: string;
  sex: string;
  birth_year: string;
  conditionCodes: string[];
  meds: string;
  concernTags: string[];
  concernText: string;
};

const TOTAL_STEPS = 6;

export function Onboarding({ onComplete }: { onComplete: () => void }) {
  const { lang, setLang } = useI18n();
  const [step, setStep] = React.useState(0);
  const [saving, setSaving] = React.useState(false);
  const [panel, setPanel] = React.useState<string[]>([]);
  const [panelNames, setPanelNames] = React.useState<Record<string, string>>({});
  const [draft, setDraft] = React.useState<Draft>({
    language_primary: lang,
    display_name: "",
    sex: "",
    birth_year: "",
    conditionCodes: [],
    meds: "",
    concernTags: [],
    concernText: "",
  });

  const ru = lang === "ru";
  const tr = (en: string, rus: string) => (ru ? rus : en);

  const set = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }));
  const toggle = (key: "conditionCodes" | "concernTags", v: string) =>
    setDraft((d) => ({
      ...d,
      [key]: d[key].includes(v) ? d[key].filter((x) => x !== v) : [...d[key], v],
    }));

  const buildProfile = React.useCallback((): Partial<Profile> => {
    const conditions = draft.conditionCodes.map((code) => {
      const c = CONDITIONS.find((x) => x.code === code);
      return { code, label: c ? (ru ? c.ru : c.en) : code, status: "active" };
    });
    const medications = draft.meds
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((name) => ({ name }));
    const concerns = draft.concernText
      .split(/[\n.]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    return {
      language_primary: draft.language_primary,
      display_name: draft.display_name.trim(),
      sex: draft.sex,
      birth_year: draft.birth_year ? Number(draft.birth_year) : null,
      conditions,
      medications,
      concern_tags: draft.concernTags,
      concerns,
    };
  }, [draft, ru]);

  // When reaching the review step, fetch the recommended panel.
  React.useEffect(() => {
    if (step !== TOTAL_STEPS - 1) return;
    let cancelled = false;
    (async () => {
      try {
        const [rec, cat] = await Promise.all([
          api.suggestPanel({ ...(buildProfile() as Partial<Profile>), use_llm: false }),
          api.specialistCatalog(draft.language_primary),
        ]);
        if (cancelled) return;
        setPanel(rec.panel);
        const names: Record<string, string> = {};
        for (const s of cat.specialists) names[s.id] = s.name;
        setPanelNames(names);
      } catch {
        /* leave panel empty; backend computes on save */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [step, buildProfile, draft.language_primary]);

  const finish = async () => {
    setSaving(true);
    try {
      await api.saveProfile({ ...(buildProfile() as Partial<Profile>), specialist_panel: panel, onboarding_complete: true });
      onComplete();
    } finally {
      setSaving(false);
    }
  };

  const canNext = () => {
    if (step === 1) return draft.display_name.trim() !== "" && draft.sex !== "";
    if (step === 2) return draft.birth_year !== "" && Number(draft.birth_year) > 1900;
    return true;
  };

  const next = () => setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
  const back = () => setStep((s) => Math.max(s - 1, 0));

  // Press Enter/Return to advance (Finish on the last step). Textareas keep
  // Enter for newlines.
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Enter") return;
      if (document.activeElement?.tagName === "TEXTAREA") return;
      e.preventDefault();
      if (step < TOTAL_STEPS - 1) {
        if (canNext()) setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
      } else if (!saving) {
        void finish();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, draft, saving, panel]);

  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col px-5 py-10">
      <div className="mb-6 flex items-center gap-2 text-primary">
        <HeartPulseIcon className="size-6" />
        <span className="text-lg font-semibold">Wellnest</span>
      </div>

      {/* progress */}
      <div className="mb-8 flex gap-1.5">
        {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
          <div key={i} className={cn("h-1.5 flex-1 rounded-full", i <= step ? "bg-primary" : "bg-muted")} />
        ))}
      </div>

      <Card className="flex-1">
        <CardContent className="flex flex-col gap-5 py-6">
          {step === 0 && (
            <Step title={tr("Welcome", "Добро пожаловать")} subtitle={tr("Let's set up your health companion. Choose a language.", "Давайте настроим вашего помощника. Выберите язык.")}>
              <div className="flex gap-3">
                <Chip active={draft.language_primary === "en"} onClick={() => { set({ language_primary: "en" }); setLang("en"); }}>English</Chip>
                <Chip active={draft.language_primary === "ru"} onClick={() => { set({ language_primary: "ru" }); setLang("ru"); }}>Русский</Chip>
              </div>
            </Step>
          )}

          {step === 1 && (
            <Step title={tr("About you", "О вас")} subtitle={tr("Your name and biological sex — this tailors clinical ranges and which specialists review your health.", "Имя и биологический пол — это настраивает нормы анализов и состав врачей.")}>
              <Input
                autoFocus
                placeholder={tr("Your name", "Ваше имя")}
                value={draft.display_name}
                onChange={(e) => set({ display_name: e.target.value })}
              />
              <div className="flex justify-center gap-4 pt-1">
                {([
                  { v: "female", icon: "♀", en: "Female", ru: "Женский" },
                  { v: "male", icon: "♂", en: "Male", ru: "Мужской" },
                ] as const).map((o) => {
                  const active = draft.sex === o.v;
                  return (
                    <button
                      key={o.v}
                      type="button"
                      onClick={() => set({ sex: o.v })}
                      className={cn(
                        "flex w-32 flex-col items-center gap-2 rounded-2xl border-2 px-4 py-5 transition-all duration-200",
                        active
                          ? "scale-105 border-primary bg-primary/10 shadow-lg shadow-primary/20"
                          : "border-border bg-background hover:scale-105 hover:border-primary/50",
                      )}
                    >
                      <span className={cn("text-4xl leading-none", active ? "text-primary" : "text-muted-foreground")}>
                        {o.icon}
                      </span>
                      <span className={cn("text-sm font-medium", active && "text-primary")}>{ru ? o.ru : o.en}</span>
                    </button>
                  );
                })}
              </div>
            </Step>
          )}

          {step === 2 && (
            <Step title={tr("Your age", "Ваш возраст")} subtitle={tr("Year of birth.", "Год рождения.")}>
              <Input
                type="number"
                inputMode="numeric"
                placeholder={tr("e.g. 1965", "напр. 1965")}
                value={draft.birth_year}
                onChange={(e) => set({ birth_year: e.target.value })}
              />
            </Step>
          )}

          {step === 3 && (
            <Step title={tr("Known conditions", "Известные состояния")} subtitle={tr("Select any that apply. You can change these later.", "Отметьте подходящие. Можно изменить позже.")}>
              <div className="flex flex-wrap gap-2">
                {CONDITIONS.map((c) => (
                  <Chip key={c.code} active={draft.conditionCodes.includes(c.code)} onClick={() => toggle("conditionCodes", c.code)}>
                    {ru ? c.ru : c.en}
                  </Chip>
                ))}
              </div>
            </Step>
          )}

          {step === 4 && (
            <Step title={tr("Medications & supplements", "Лекарства и добавки")} subtitle={tr("List anything you take regularly, one per line (optional).", "Перечислите, что принимаете регулярно, по одному в строке (необязательно).")}>
              <textarea
                className="min-h-28 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
                placeholder={tr("e.g. Levothyroxine\nVitamin D", "напр. Эутирокс\nВитамин D")}
                value={draft.meds}
                onChange={(e) => set({ meds: e.target.value })}
              />
            </Step>
          )}

          {step === 5 && (
            <Step title={tr("Main concerns", "Что беспокоит")} subtitle={tr("What would you like to focus on? Pick topics and add a note.", "На чём сосредоточиться? Выберите темы и добавьте заметку.")}>
              <div className="flex flex-wrap gap-2">
                {CONCERN_TAGS.map((c) => (
                  <Chip key={c.tag} active={draft.concernTags.includes(c.tag)} onClick={() => toggle("concernTags", c.tag)}>
                    {ru ? c.ru : c.en}
                  </Chip>
                ))}
              </div>
              <textarea
                className="min-h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
                placeholder={tr("Anything else in your own words…", "Что-то ещё своими словами…")}
                value={draft.concernText}
                onChange={(e) => set({ concernText: e.target.value })}
              />
              {panel.length > 0 && (
                <div className="mt-2 rounded-lg border border-border bg-muted/40 p-4">
                  <p className="mb-2 text-sm font-medium">{tr("Your care team", "Ваша команда врачей")}</p>
                  <div className="flex flex-wrap gap-2">
                    {panel.map((id) => (
                      <span key={id} className="rounded-full bg-primary/15 px-3 py-1 text-xs text-primary">
                        {panelNames[id] || id}
                      </span>
                    ))}
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {tr("Chosen automatically from your answers. You can adjust later in settings.", "Выбраны автоматически по вашим ответам. Можно изменить позже в настройках.")}
                  </p>
                </div>
              )}
            </Step>
          )}
        </CardContent>
      </Card>

      <div className="mt-6 flex items-center justify-between">
        <Button variant="ghost" onClick={back} disabled={step === 0 || saving}>
          {tr("Back", "Назад")}
        </Button>
        {step < TOTAL_STEPS - 1 ? (
          <Button onClick={next} disabled={!canNext()}>
            {tr("Continue", "Далее")}
          </Button>
        ) : (
          <Button onClick={finish} disabled={saving}>
            {saving ? tr("Setting up…", "Настраиваю…") : tr("Finish", "Готово")}
          </Button>
        )}
      </div>
    </div>
  );
}

function Step({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <>
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
      </div>
      {children}
    </>
  );
}
