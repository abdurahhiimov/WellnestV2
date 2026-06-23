import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { EvidenceList } from "@/components/evidence-list";
import { useI18n } from "@/lib/i18n";
import type { SymptomQA } from "@/lib/types";
import { MessageCircleHeartIcon } from "lucide-react";

export function SymptomAnswer({ answer }: { answer: NonNullable<SymptomQA["answer"]> }) {
  const { t, lang } = useI18n();

  // Pick the language-appropriate field, falling back to the other language if not yet available
  const summary = lang === "ru"
    ? (answer.summary_ru || answer.summary_en || "")
    : (answer.summary_en || answer.summary_ru || "");
  const links = lang === "ru"
    ? (answer.possible_links_ru?.length ? answer.possible_links_ru : answer.possible_links_en)
    : (answer.possible_links_en?.length ? answer.possible_links_en : answer.possible_links_ru);
  const discuss = lang === "ru"
    ? (answer.discuss_with_doctor_ru || answer.discuss_with_doctor_en || "")
    : (answer.discuss_with_doctor_en || answer.discuss_with_doctor_ru || "");

  return (
    <div className="zh-rise flex flex-col gap-3 rounded-lg border bg-muted/30 p-4">
      {answer.question && (
        <p className="text-muted-foreground text-xs italic">«{answer.question}»</p>
      )}
      <p className="whitespace-pre-line text-sm leading-relaxed">{summary}</p>

      {links?.length ? (
        <>
          <Separator />
          <div className="flex flex-col gap-1.5">
            <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
              {t("possibleLinks")}
            </p>
            <ul className="flex list-disc flex-col gap-1 pl-4 text-sm">
              {links.map((link, i) => (
                <li key={i}>{link}</li>
              ))}
            </ul>
          </div>
        </>
      ) : null}

      {answer.evidence?.length ? (
        <>
          <Separator />
          <div className="flex flex-col gap-1.5">
            <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
              {t("secEvidence")}
            </p>
            <EvidenceList items={answer.evidence} />
          </div>
        </>
      ) : null}

      {discuss ? (
        <Alert>
          <MessageCircleHeartIcon />
          <AlertTitle>{t("discussDoctor")}</AlertTitle>
          <AlertDescription>{discuss}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
