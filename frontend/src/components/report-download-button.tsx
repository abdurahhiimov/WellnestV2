import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { downloadReport } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { DownloadIcon } from "lucide-react";
import * as React from "react";

export function ReportDownloadButton({
  filename,
  label,
  prepare,
  variant = "outline",
  className,
}: {
  filename: string;
  label?: string;
  /** Optional async step before download (e.g. regenerate HTML). Receives current UI language. */
  prepare?: (lang: "ru" | "en") => Promise<string | void>;
  variant?: "default" | "outline" | "secondary";
  className?: string;
}) {
  const { t, lang } = useI18n();
  const [busy, setBusy] = React.useState(false);

  const onClick = async () => {
    setBusy(true);
    try {
      let target = filename;
      if (prepare) {
        const next = await prepare(lang);
        if (typeof next === "string" && next) target = next;
      }
      await downloadReport(target);
    } catch {
      window.open(`/reports/${filename}`, "_blank");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Button className={className} disabled={busy} onClick={() => void onClick()} variant={variant}>
      {busy ? <Spinner data-icon="inline-start" /> : <DownloadIcon data-icon="inline-start" />}
      {label || t("downloadReport")}
    </Button>
  );
}
