/** Shared flag rendering helpers used across Labs, Charts, and Detail Sheet. */

export type LabFlag = string | null | undefined;

export type FlagInfo = {
  label: string;
  variant: "secondary" | "destructive" | "outline";
  className: string;
  /** Whether this flag represents an actionable abnormality worth drilling into */
  concerning: boolean;
};

const FLAG_MAP: Record<string, Omit<FlagInfo, "concerning">> = {
  normal:     { label: "normal",       variant: "secondary", className: "" },
  high:       { label: "↑ high",       variant: "destructive", className: "" },
  low:        { label: "↓ low",        variant: "destructive", className: "" },
  pos:        { label: "Positive",     variant: "outline", className: "border-orange-500/60 bg-orange-500/15 text-orange-600 dark:text-orange-400" },
  neg:        { label: "Negative ✓",   variant: "outline", className: "border-green-500/60 bg-green-500/10 text-green-600 dark:text-green-400" },
  immune:     { label: "Immune ✓",     variant: "outline", className: "border-green-500/60 bg-green-500/10 text-green-600 dark:text-green-400" },
  not_immune: { label: "Not immune",   variant: "outline", className: "border-orange-500/60 bg-orange-500/15 text-orange-600 dark:text-orange-400" },
  equivocal:  { label: "Equivocal",    variant: "outline", className: "border-yellow-500/60 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400" },
};

const CONCERNING = new Set(["high", "low", "pos", "not_immune"]);

export function flagInfo(flag: LabFlag): FlagInfo {
  const entry = flag ? FLAG_MAP[flag] : undefined;
  if (!entry) {
    return { label: "", variant: "outline", className: "", concerning: false };
  }
  return { ...entry, concerning: CONCERNING.has(flag!) };
}

export function isConcerningFlag(flag: LabFlag): boolean {
  return CONCERNING.has(flag ?? "");
}
