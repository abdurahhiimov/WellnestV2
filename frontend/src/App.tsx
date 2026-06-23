import { AppShell } from "@/components/app-shell";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useI18n } from "@/lib/i18n";
import { useRoute, useStore } from "@/lib/store";
import { TodayPage } from "@/pages/today";
import { ConsiliumPage } from "@/pages/consilium";
import { ChartsPage } from "@/pages/charts";
import { LabsPage } from "@/pages/labs";
import { TasksPage } from "@/pages/tasks";
import { MedsPage } from "@/pages/meds";
import { HealthProfilePage } from "@/pages/health-profile";
import { ConnectPage } from "@/pages/connect";
import { Onboarding } from "@/components/onboarding";
import { api } from "@/lib/api";
import { AlertTriangleIcon } from "lucide-react";
import * as React from "react";

function PageLoading() {
  return (
    <div className="flex flex-1 flex-col gap-4 py-6">
      <Skeleton className="h-7 w-56" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-5 w-40" />
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <Skeleton className="h-3.5 w-full" />
              <Skeleton className="h-3.5 w-3/4" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

const ROUTES: Record<string, React.ComponentType> = {
  today: TodayPage,
  consilium: ConsiliumPage,
  charts: ChartsPage,
  labs: LabsPage,
  tasks: TasksPage,
  meds: MedsPage,
  profile: HealthProfilePage,
  connect: ConnectPage,
};

export function App() {
  const route = useRoute();
  const { data, loading, error, reload } = useStore();
  const { t, setLang } = useI18n();
  const Page = ROUTES[route] || TodayPage;

  // First-run gate: undefined = checking, false = needs onboarding, true = ready.
  const [onboarded, setOnboarded] = React.useState<boolean | undefined>(undefined);
  React.useEffect(() => {
    api
      .getProfile()
      .then((p) => {
        // Sync UI language to the profile unless the user picked one this session.
        if (!localStorage.getItem("zh_lang") && (p.language_primary === "ru" || p.language_primary === "en")) {
          setLang(p.language_primary);
        }
        setOnboarded(p.onboarding_complete);
      })
      .catch(() => setOnboarded(true)); // on error, don't block the existing app
  }, [setLang]);

  if (onboarded === undefined) {
    return <PageLoading />;
  }
  if (onboarded === false) {
    return (
      <Onboarding
        onComplete={() => {
          setOnboarded(true);
          reload();
        }}
      />
    );
  }

  return (
    <AppShell>
      {loading ? (
        <PageLoading />
      ) : error && !data ? (
        <div className="py-6">
          <Alert variant="destructive">
            <AlertTriangleIcon />
            <AlertTitle>{t("loadError")}</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      ) : (
        <Page key={route} />
      )}
    </AppShell>
  );
}

export default App;
