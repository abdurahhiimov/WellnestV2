import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { EvidenceList } from "@/components/evidence-list";
import { useI18n } from "@/lib/i18n";
import type { Specialist } from "@/lib/types";
import { EyeIcon, AlertTriangleIcon, ClipboardCheckIcon } from "lucide-react";

const SPECIALIST_META: Record<string, { emoji: string; ru: string; en: string }> = {
  endo: { emoji: "🔬", ru: "Эндокринолог", en: "Endocrinologist" },
  gyn: { emoji: "🌸", ru: "Гинеколог", en: "Gynecologist" },
  neuro: { emoji: "🧠", ru: "Невролог", en: "Neurologist" },
  nutri: { emoji: "🥗", ru: "Нутрициолог", en: "Nutritionist" },
  ortho: { emoji: "🦴", ru: "Ортопед", en: "Orthopedist" },
  gp: { emoji: "🩺", ru: "Семейный врач", en: "Family doctor" },
};

export function SpecialistCard({ specialist, index }: { specialist: Specialist; index: number }) {
  const { t, lang } = useI18n();
  const meta = SPECIALIST_META[specialist.id] || { emoji: "🩺", ru: specialist.title_ru || specialist.id, en: specialist.title || specialist.id };
  const op = specialist.opinion;

  return (
    <Card
      className="zh-rise transition-all hover:shadow-md"
      style={{ animationDelay: `${0.06 * index}s` }}
    >
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <span className="text-xl">{meta.emoji}</span>
          {lang === "ru" ? meta.ru : meta.en}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {op.see?.length ? (
          <section className="flex flex-col gap-1.5">
            <p className="flex items-center gap-1.5 font-medium text-muted-foreground text-xs uppercase tracking-wide">
              <EyeIcon className="size-3.5" /> {t("secSee")}
            </p>
            {op.see.map((para, i) => (
              <p className="text-sm leading-relaxed" key={i}>
                {para}
              </p>
            ))}
          </section>
        ) : null}

        {op.concerns?.length ? (
          <>
            <Separator />
            <section className="flex flex-col gap-1.5">
              <p className="flex items-center gap-1.5 font-medium text-status-warn text-xs uppercase tracking-wide">
                <AlertTriangleIcon className="size-3.5" /> {t("secConcerns")}
              </p>
              <ul className="flex list-disc flex-col gap-1 pl-4 text-sm leading-relaxed">
                {op.concerns.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </section>
          </>
        ) : null}

        {op.recommendations?.length ? (
          <>
            <Separator />
            <section className="flex flex-col gap-1.5">
              <p className="flex items-center gap-1.5 font-medium text-primary text-xs uppercase tracking-wide">
                <ClipboardCheckIcon className="size-3.5" /> {t("secRec")}
              </p>
              <ul className="flex list-disc flex-col gap-1 pl-4 text-sm leading-relaxed">
                {op.recommendations.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </section>
          </>
        ) : null}

        {op.evidence?.length ? (
          <Accordion collapsible type="single">
            <AccordionItem className="border-0" value="evidence">
              <AccordionTrigger className="py-1 text-muted-foreground text-xs hover:no-underline">
                {t("secEvidence")} ({op.evidence.length})
              </AccordionTrigger>
              <AccordionContent>
                <EvidenceList items={op.evidence} />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        ) : null}
      </CardContent>
    </Card>
  );
}
