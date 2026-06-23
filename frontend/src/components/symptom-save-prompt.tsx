import { createPortal } from "react-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useI18n } from "@/lib/i18n";
import { DatabaseIcon, SparklesIcon } from "lucide-react";

export function SymptomSavePrompt({
  open,
  saving,
  saved,
  onSave,
  onDismiss,
}: {
  open: boolean;
  saving?: boolean;
  saved?: boolean;
  onSave: () => void | Promise<void>;
  onDismiss: () => void;
}) {
  const { t } = useI18n();

  if (!open && !saved) return null;

  // Portal to <body> so no ancestor transform/stacking-context can swallow
  // clicks (the native <dialog> top-layer approach was unreliable in Safari).
  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/55 p-4"
      onClick={onDismiss}
    >
      <Card
        className="zh-rise w-full max-w-md shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <DatabaseIcon className="size-4 text-primary" />
            {saved ? t("symptomSavedTitle") : t("symptomSavePromptTitle")}
          </CardTitle>
          <CardDescription>
            {saved ? t("symptomSavedBody") : t("symptomSavePromptBody")}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {!saved ? (
            <>
              <Button className="w-full" disabled={saving} onClick={() => void onSave()}>
                {saving ? <Spinner data-icon="inline-start" /> : <DatabaseIcon data-icon="inline-start" />}
                {t("symptomSaveToDb")}
              </Button>
              <Button className="w-full" disabled={saving} onClick={onDismiss} variant="outline">
                <SparklesIcon data-icon="inline-start" />
                {t("symptomJustCurious")}
              </Button>
            </>
          ) : (
            <Button className="w-full" onClick={onDismiss} variant="outline">
              {t("symptomSavePromptClose")}
            </Button>
          )}
        </CardContent>
      </Card>
    </div>,
    document.body,
  );
}
