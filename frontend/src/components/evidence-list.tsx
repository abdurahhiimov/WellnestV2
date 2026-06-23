import { FlaskConicalIcon, BookOpenIcon, ScanIcon, ClipboardListIcon, UserIcon, ExternalLinkIcon } from "lucide-react";
import type { Evidence } from "@/lib/types";

const KIND_ICON: Record<string, React.ReactNode> = {
  lab: <FlaskConicalIcon className="size-3.5" />,
  guideline: <BookOpenIcon className="size-3.5" />,
  imaging: <ScanIcon className="size-3.5" />,
  checkin: <ClipboardListIcon className="size-3.5" />,
  profile: <UserIcon className="size-3.5" />,
};

export function EvidenceList({ items }: { items: Evidence[] }) {
  if (!items?.length) return null;
  return (
    <ul className="flex flex-col gap-1.5">
      {items.map((ev, i) => (
        <li className="flex items-start gap-2 text-muted-foreground text-xs" key={i}>
          <span className="mt-0.5 shrink-0 text-primary">
            {KIND_ICON[ev.kind || ""] || KIND_ICON.profile}
          </span>
          <span className="min-w-0">
            {ev.claim_ru}
            {ev.date ? <span className="text-muted-foreground/70"> · {ev.date}</span> : null}
            {ev.study_url ? (
              <a
                className="ml-1 inline-flex items-center gap-0.5 text-primary underline-offset-2 hover:underline"
                href={ev.study_url}
                rel="noopener noreferrer"
                target="_blank"
              >
                {ev.source_label || "источник"}
                <ExternalLinkIcon className="size-3" />
              </a>
            ) : ev.source_label ? (
              <span className="text-muted-foreground/70"> · {ev.source_label}</span>
            ) : null}
          </span>
        </li>
      ))}
    </ul>
  );
}
