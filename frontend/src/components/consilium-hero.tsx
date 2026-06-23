import * as React from "react";
import { useI18n } from "@/lib/i18n";
import { api } from "@/lib/api";
import { StethoscopeIcon } from "lucide-react";

// Emoji per specialist id (from the backend catalog). Falls back to 🩺.
const SPEC_EMOJI: Record<string, string> = {
  gp: "🩺", endo: "🔬", gyn: "🌸", uro: "🚹", cardio: "❤️", neuro: "🧠",
  nutri: "🥦", ortho: "🦴", gastro: "🌿", mental: "🧘",
};

export function ConsiliumHero({ selectedDoctors }: { selectedDoctors?: { id: string; name: string }[] }) {
  const { t, lang } = useI18n();
  const [catalogSpecialists, setCatalogSpecialists] = React.useState<{ id: string; name: string }[]>([]);

  React.useEffect(() => {
    if (selectedDoctors) return; // parent is driving the list
    let cancelled = false;
    (async () => {
      try {
        const [profile, cat] = await Promise.all([api.getProfile(), api.specialistCatalog(lang)]);
        if (cancelled) return;
        const names: Record<string, string> = {};
        for (const s of cat.specialists) names[s.id] = s.name;
        const panel = (profile.specialist_panel || []).map((id) => ({ id, name: names[id] || id }));
        setCatalogSpecialists(panel);
      } catch {
        /* leave empty */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [lang, selectedDoctors]);

  const specialists = selectedDoctors ?? catalogSpecialists;

  const count = specialists.length;
  const lead =
    count > 0
      ? lang === "ru"
        ? `${count} виртуальных специалиста`
        : `${count} virtual specialists`
      : t("consiliumHeroSix");

  return (
    <div className="zh-rise relative overflow-hidden rounded-xl border border-primary/30 bg-gradient-to-br from-primary/12 via-background to-background p-5 sm:p-6">
      <div className="zh-hero-glow pointer-events-none absolute -right-10 -top-10 size-40 rounded-full bg-primary/15 blur-3xl" />
      <div className="relative flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <StethoscopeIcon className="size-5" />
          </div>
          <h1 className="font-semibold text-xl leading-tight">{t("consiliumTitle")}</h1>
        </div>

        <p className="max-w-3xl text-base leading-relaxed">
          <span className="zh-hero-highlight font-semibold text-primary">{lead}</span>{" "}
          {t("consiliumHeroReview")}
        </p>

        <p className="max-w-3xl text-muted-foreground text-sm italic">{t("consiliumHeroDisclaimer")}</p>

        {specialists.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {specialists.map((s, i) => (
              <span
                className="zh-hero-badge inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/8 px-2.5 py-1 text-xs"
                key={s.id}
                style={{ animationDelay: `${0.05 + i * 0.07}s` }}
              >
                <span className="text-sm">{SPEC_EMOJI[s.id] || "🩺"}</span>
                {s.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
