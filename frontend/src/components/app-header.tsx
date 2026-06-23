import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Spinner } from "@/components/ui/spinner";
import { MoonIcon, RefreshCwIcon, SunIcon } from "lucide-react";
import { navLinks } from "@/components/app-shared";
import { useI18n } from "@/lib/i18n";
import { useRoute, useStore } from "@/lib/store";
import { useTheme } from "@/components/theme-provider";
import { api } from "@/lib/api";

export function AppHeader() {
  const { t, lang, setLang } = useI18n();
  const route = useRoute();
  const { reload, data, symptomAsking } = useStore();
  const { theme, setTheme } = useTheme();
  const [refreshing, setRefreshing] = React.useState(false);

  const active = navLinks.find((item) => item.route === route);
  const updatedAt = (data?.generated_at || "").replace("T", " ").slice(0, 16);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await api.refresh();
      await reload();
    } catch {
      /* surfaced by store error state */
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <header
      className={cn(
        "sticky top-0 z-50 flex h-14 shrink-0 items-center justify-between gap-2 bg-background px-4 md:px-6",
      )}
    >
      <div className="flex min-w-0 items-center gap-2">
        <SidebarTrigger className="md:hidden" />
        <Separator
          className="mr-2 data-[orientation=vertical]:h-4 md:hidden"
          orientation="vertical"
        />
        <span className="truncate font-medium text-sm">{active ? t(active.key) : ""}</span>
        {symptomAsking && (
          <span className="hidden items-center gap-1.5 truncate text-primary text-xs sm:inline-flex">
            <Spinner className="size-3" />
            {t("symptomJobHeader")}
          </span>
        )}
        {updatedAt && (
          <span className="hidden truncate text-muted-foreground text-xs sm:inline">
            · {t("updated")} {updatedAt}
          </span>
        )}
      </div>
      <div className="flex items-center gap-1.5">
        <Button
          aria-label="Language"
          onClick={() => setLang(lang === "ru" ? "en" : "ru")}
          size="sm"
          variant="ghost"
        >
          {lang === "ru" ? "EN" : "RU"}
        </Button>
        <Button
          aria-label="Theme"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          size="icon"
          variant="ghost"
        >
          {theme === "dark" ? <SunIcon /> : <MoonIcon />}
        </Button>
        <Button disabled={refreshing} onClick={onRefresh} size="sm" variant="outline">
          {refreshing ? <Spinner data-icon="inline-start" /> : <RefreshCwIcon data-icon="inline-start" />}
          {t("refresh")}
        </Button>
      </div>
    </header>
  );
}
