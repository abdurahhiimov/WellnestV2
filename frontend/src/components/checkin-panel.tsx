import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useStore } from "@/lib/store";

const MOOD = ["😞", "🙁", "😐", "🙂", "😄"];
// Russian "Выспал(ся/ась)" is gendered; pick the form from the profile sex.
const SLEEP_OPTS = [
  { id: "good", ruF: "Выспалась", ruM: "Выспался", en: "Rested" },
  { id: "ok", ruF: "Так себе", ruM: "Так себе", en: "So-so" },
  { id: "bad", ruF: "Плохо", ruM: "Плохо", en: "Poor" },
];

export function CheckinPanel() {
  const { t, lang } = useI18n();
  const { data, reload } = useStore();
  const [mood, setMood] = React.useState(3);
  const [sleep, setSleep] = React.useState("ok");
  const [notes, setNotes] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  if (!data) return null;
  const recent = data.checkins?.recent || [];

  const save = async () => {
    setSaving(true);
    try {
      await api.saveCheckin({ mood, sleep, symptoms: [], notes });
      setNotes("");
      await reload();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        {recent.slice(-7).map((c) => (
          <div
            className="flex min-w-14 flex-col items-center gap-1 rounded-lg border bg-muted/40 px-3 py-2"
            key={c.date}
            title={c.notes || ""}
          >
            <span className="text-lg">
              {c.mood == null ? "·" : MOOD[Math.max(0, Math.min(4, (c.mood || 3) - 1))]}
            </span>
            <span className="text-muted-foreground text-xs tabular-nums">
              {c.date.slice(5).replace("-", ".")}
            </span>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-2 rounded-lg border border-dashed p-3">
        <p className="font-medium text-sm">{t("checkinToday")}</p>
        <div className="flex flex-wrap gap-1.5">
          {MOOD.map((emoji, i) => (
            <Button
              key={i}
              onClick={() => setMood(i + 1)}
              size="sm"
              variant={mood === i + 1 ? "default" : "outline"}
            >
              {emoji}
            </Button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {SLEEP_OPTS.map((opt) => (
            <Badge
              className="cursor-pointer px-2 py-1"
              key={opt.id}
              onClick={() => setSleep(opt.id)}
              variant={sleep === opt.id ? "default" : "outline"}
            >
              {lang === "ru" ? (data.profile?.sex === "male" ? opt.ruM : opt.ruF) : opt.en}
            </Badge>
          ))}
        </div>
        <Textarea
          className="min-h-12 resize-none text-sm"
          onChange={(e) => setNotes(e.target.value)}
          placeholder={t("checkinNotesPh")}
          value={notes}
        />
        <Button disabled={saving} onClick={save} size="sm">
          {saving && <Spinner data-icon="inline-start" />}
          {t("checkinSave")}
        </Button>
      </div>
    </div>
  );
}
