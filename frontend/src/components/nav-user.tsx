"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar";
import { useStore } from "@/lib/store";
import { useI18n } from "@/lib/i18n";

export function NavUser() {
  const { data } = useStore();
  const { t } = useI18n();
  const name = data?.profile?.display_name || "—";
  const meta = data
    ? `${data.profile.diagnoses?.length || 0} ${t("diagnoses")} · ${data.lab_results?.length || 0} ${t("labs")}`
    : "";

  return (
    <SidebarMenu className="border-t p-2">
      <SidebarMenuItem>
        <SidebarMenuButton className="h-auto py-2 text-muted-foreground" size="lg">
          <Avatar className="size-7">
            <AvatarFallback className="bg-primary/15 text-primary text-xs">
              {name.charAt(0)}
            </AvatarFallback>
          </Avatar>
          <span className="flex min-w-0 flex-col">
            <span className="truncate font-medium text-foreground text-sm">{name}</span>
            <span className="truncate text-xs">{meta}</span>
          </span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
