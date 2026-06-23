"use client";

import { HeartPulseIcon } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { footerNavLinks, navGroups } from "@/components/app-shared";
import { NavUser } from "@/components/nav-user";
import { useI18n } from "@/lib/i18n";
import { useRoute } from "@/lib/store";
import { SERVER_BASE } from "@/lib/api";

export function AppSidebar() {
  const { t } = useI18n();
  const route = useRoute();

  return (
    <Sidebar
      className="static min-h-full *:data-[slot=sidebar-inner]:bg-background"
      collapsible="offcanvas"
      variant="sidebar"
    >
      <SidebarHeader className="relative h-14 justify-center px-2 py-0">
        <a
          className="flex h-10 w-max items-center justify-center gap-2 rounded-lg px-3 hover:bg-muted dark:hover:bg-muted/50"
          href="#/today"
        >
          <HeartPulseIcon className="size-4 text-primary" />
          <span className="font-semibold text-sm tracking-tight">{t("appName")}</span>
        </a>
      </SidebarHeader>
      <SidebarContent>
        {navGroups.map((group, index) => (
          <SidebarGroup key={`sidebar-group-${index}`}>
            <SidebarMenu>
              {group.items.map((item) => (
                <SidebarMenuItem key={item.route}>
                  <SidebarMenuButton
                    asChild
                    isActive={route === item.route}
                    tooltip={t(item.key)}
                  >
                    <a href={`#/${item.route}`}>
                      {item.icon}
                      <span>{t(item.key)}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter className="gap-0 p-0">
        <SidebarMenu className="border-t p-2">
          {footerNavLinks.map((item) => (
            <SidebarMenuItem key={item.route}>
              <SidebarMenuButton asChild className="text-muted-foreground" size="sm">
                <a
                  href={`${SERVER_BASE}/reports/visit-pack`}
                  rel="noopener"
                  target="_blank"
                >
                  {item.icon}
                  <span>{t(item.key)}</span>
                </a>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  );
}
