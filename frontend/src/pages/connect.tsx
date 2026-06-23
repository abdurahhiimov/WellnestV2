import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { api, SERVER_BASE } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useStore } from "@/lib/store";
import { BrainIcon, CheckCircle2Icon, ExternalLinkIcon, WatchIcon, HeartIcon } from "lucide-react";

const MODELS = [
  { value: "openai/gpt-oss-120b:free", label: "GPT-OSS 120B (free) — рекомендуем, быстрый" },
  { value: "openrouter/free", label: "Авто (любая свободная)" },
  { value: "meta-llama/llama-3.3-70b-instruct:free", label: "Llama 3.3 70B (free)" },
];

export function ConnectPage() {
  const { t } = useI18n();
  const { data, engine, setEngine } = useStore();
  const [key, setKey] = React.useState("");
  const [model, setModel] = React.useState(engine?.model || MODELS[0].value);
  const [saving, setSaving] = React.useState(false);
  const [saved, setSaved] = React.useState(false);

  React.useEffect(() => {
    if (engine?.model) setModel(engine.model);
  }, [engine?.model]);

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const st = await api.engineConfigure(key.trim(), model);
      setEngine(st);
      setKey("");
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  const sources = engine?.evidence_sources || {};
  const sourceNames = [
    sources.europepmc !== false && "Europe PMC",
    sources.pubmed !== false && "PubMed",
    sources.openevidence && "OpenEvidence",
  ].filter(Boolean) as string[];

  const oura = data?.integrations?.oura;

  return (
    <div className="flex flex-1 flex-col gap-6 py-6">
      <h1 className="zh-rise font-semibold text-xl leading-tight">{t("navConnect")}</h1>

      {/* Engine */}
      <Card className="zh-rise zh-rise-1 border-primary/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BrainIcon className="size-4 text-primary" />
            {t("engineTitle")}
            {engine?.enabled ? (
              <Badge className="ml-1" variant="secondary">
                <CheckCircle2Icon /> {t("engineOn")}
              </Badge>
            ) : (
              <Badge className="ml-1" variant="outline">
                {t("engineOff")}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>{t("engineDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="flex max-w-xl flex-col gap-3">
          <Input
            autoComplete="off"
            onChange={(e) => setKey(e.target.value)}
            placeholder="sk-or-v1-…"
            type="password"
            value={key}
          />
          <Select onValueChange={setModel} value={model}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Model" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {MODELS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <div className="flex flex-wrap items-center gap-2">
            <Button disabled={saving || !key.trim()} onClick={save}>
              {saving && <Spinner data-icon="inline-start" />}
              {t("engineSave")}
            </Button>
            <Button
              onClick={() => window.open("https://openrouter.ai/keys", "_blank")}
              variant="outline"
            >
              {t("engineGetKey")}
              <ExternalLinkIcon data-icon="inline-end" />
            </Button>
            {saved && (
              <span className="text-sm text-status-good">
                {t("engineSaved")} ✓
              </span>
            )}
          </div>
          <p className="text-muted-foreground text-xs">
            {t("engineNote")}
            {sourceNames.length ? ` · ${t("engineSources")}: ${sourceNames.join(" · ")}` : ""}
          </p>
        </CardContent>
      </Card>

      <div className="zh-rise zh-rise-2 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Oura */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <WatchIcon className="size-4 text-primary" />
              {t("ouraTitle")}
              {oura?.connected && (
                <Badge variant="secondary">
                  <CheckCircle2Icon /> {t("ouraConnected")}
                </Badge>
              )}
            </CardTitle>
            <CardDescription>{t("ouraDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => window.open(`${SERVER_BASE}/oura/setup`, "_blank")}
              variant="outline"
            >
              {t("ouraConnect")}
            </Button>
          </CardContent>
        </Card>

        {/* Apple Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <HeartIcon className="size-4 text-primary" />
              {t("appleTitle")}
            </CardTitle>
            <CardDescription>{t("appleDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <SyncButton />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function SyncButton() {
  const { t } = useI18n();
  const { reload } = useStore();
  const [syncing, setSyncing] = React.useState(false);
  return (
    <Button
      disabled={syncing}
      onClick={async () => {
        setSyncing(true);
        try {
          await api.syncAppleHealth();
          await reload();
        } finally {
          setSyncing(false);
        }
      }}
      variant="outline"
    >
      {syncing && <Spinner data-icon="inline-start" />}
      {t("syncNow")}
    </Button>
  );
}
