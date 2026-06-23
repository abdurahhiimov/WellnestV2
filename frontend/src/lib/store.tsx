/* eslint-disable react-refresh/only-export-components */
import * as React from "react";
import { api, type SymptomProgress } from "@/lib/api";
import type { EngineStatus, Snapshot } from "@/lib/types";

type StoreValue = {
  data: Snapshot | null;
  engine: EngineStatus | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  reloadEngine: () => Promise<void>;
  setEngine: (e: EngineStatus) => void;
  symptomJob: SymptomProgress | null;
  symptomAsking: boolean;
  symptomSavePromptPending: boolean;
  clearSymptomSavePrompt: () => void;
  startSymptomAsk: (mode: "quick" | "consilium", question: string, attachments: string[]) => Promise<void>;
};

const StoreContext = React.createContext<StoreValue | undefined>(undefined);

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = React.useState<Snapshot | null>(null);
  const [engine, setEngineState] = React.useState<EngineStatus | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [symptomJob, setSymptomJob] = React.useState<SymptomProgress | null>(null);
  const [symptomSavePromptPending, setSymptomSavePromptPending] = React.useState(false);
  const pollRef = React.useRef<number | null>(null);

  const reload = React.useCallback(async () => {
    try {
      const snap = await api.snapshot();
      setData(snap);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const reloadEngine = React.useCallback(async () => {
    try {
      setEngineState(await api.engineStatus());
    } catch {
      /* engine endpoint unavailable: leave null */
    }
  }, []);

  const stopSymptomPolling = React.useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startSymptomPolling = React.useCallback(() => {
    stopSymptomPolling();
    pollRef.current = window.setInterval(async () => {
      try {
        const p = await api.symptomProgress();
        setSymptomJob(p);
        if (p.state === "done" || p.state === "error" || p.state === "idle") {
          stopSymptomPolling();
          if (p.state === "done") {
            await reload();
            setSymptomSavePromptPending(true);
          }
        }
      } catch {
        /* keep polling on transient failure */
      }
    }, 2000);
  }, [reload, stopSymptomPolling]);

  const startSymptomAsk = React.useCallback(
    async (mode: "quick" | "consilium", question: string, attachments: string[]) => {
      setSymptomSavePromptPending(false);
      if (mode === "consilium") {
        await api.askSymptomConsilium(question, attachments, true);
      } else {
        await api.askSymptom(question, attachments);
      }
      const p = await api.symptomProgress();
      setSymptomJob(p);
      if (p.state === "running") startSymptomPolling();
      else if (p.state === "done") {
        await reload();
        setSymptomSavePromptPending(true);
      }
    },
    [reload, startSymptomPolling],
  );

  React.useEffect(() => {
    let cancelled = false;
    api.symptomProgress().then((p) => {
      if (cancelled) return;
      setSymptomJob(p);
      if (p.state === "running") startSymptomPolling();
    }).catch(() => {});
    return () => {
      cancelled = true;
      stopSymptomPolling();
    };
  }, [startSymptomPolling, stopSymptomPolling]);

  React.useEffect(() => {
    void reload();
    void reloadEngine();
  }, [reload, reloadEngine]);

  const symptomAsking = symptomJob?.state === "running";

  const value = React.useMemo(
    () => ({
      data,
      engine,
      loading,
      error,
      reload,
      reloadEngine,
      setEngine: setEngineState,
      symptomJob,
      symptomAsking,
      symptomSavePromptPending,
      clearSymptomSavePrompt: () => setSymptomSavePromptPending(false),
      startSymptomAsk,
    }),
    [
      data,
      engine,
      loading,
      error,
      reload,
      reloadEngine,
      symptomJob,
      symptomAsking,
      symptomSavePromptPending,
      startSymptomAsk,
    ],
  );
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const ctx = React.useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used within StoreProvider");
  return ctx;
}

/** Tiny hash router: "#/today" -> "today". */
export function useRoute(defaultRoute = "today") {
  const parse = () => {
    const h = location.hash.replace(/^#\/?/, "") || defaultRoute;
    return h.split("?")[0] || defaultRoute;
  };
  const [route, setRoute] = React.useState<string>(parse);
  React.useEffect(() => {
    const onHash = () => setRoute(parse());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return route;
}

export function useHashQuery(): URLSearchParams {
  const [tick, setTick] = React.useState(0);
  React.useEffect(() => {
    const onHash = () => setTick((x) => x + 1);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  void tick;
  const h = location.hash.replace(/^#\/?/, "");
  const qs = h.includes("?") ? h.split("?").slice(1).join("?") : "";
  return new URLSearchParams(qs);
}

/** route may include query, e.g. `charts?highlight=tsh,ft4` */
export function navigate(route: string) {
  location.hash = route.startsWith("/") ? route : `/${route}`;
}
