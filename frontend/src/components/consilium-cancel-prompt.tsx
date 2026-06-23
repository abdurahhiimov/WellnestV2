import { createPortal } from "react-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useI18n } from "@/lib/i18n";
import { OctagonXIcon } from "lucide-react";

export function ConsiliumCancelPrompt({
  open,
  busy,
  onConfirm,
  onDismiss,
}: {
  open: boolean;
  busy?: boolean;
  onConfirm: () => void | Promise<void>;
  onDismiss: () => void;
}) {
  const { t } = useI18n();

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/55 p-4"
      onClick={onDismiss}
    >
      <Card className="zh-rise w-full max-w-md shadow-xl" onClick={(e) => e.stopPropagation()}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <OctagonXIcon className="size-4 text-destructive" />
            {t("consiliumCancelTitle")}
          </CardTitle>
          <CardDescription>{t("consiliumCancelBody")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <Button className="w-full" disabled={busy} onClick={() => void onConfirm()} variant="destructive">
            {busy ? <Spinner data-icon="inline-start" /> : <OctagonXIcon data-icon="inline-start" />}
            {t("consiliumCancelYes")}
          </Button>
          <Button className="w-full" disabled={busy} onClick={onDismiss} variant="outline">
            {t("consiliumCancelNo")}
          </Button>
        </CardContent>
      </Card>
    </div>,
    document.body,
  );
}
