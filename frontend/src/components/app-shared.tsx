import {
  SunIcon,
  StethoscopeIcon,
  LineChartIcon,
  FlaskConicalIcon,
  ListChecksIcon,
  PillIcon,
  PlugIcon,
  FileTextIcon,
  ClipboardListIcon,
} from "lucide-react";
import type { StringKey } from "@/lib/i18n";

export type SidebarNavItem = {
  key: StringKey;
  route: string;
  icon: React.ReactNode;
};

export type SidebarNavGroup = {
  labelKey?: StringKey;
  items: SidebarNavItem[];
};

export const navGroups: SidebarNavGroup[] = [
  {
    items: [
      { key: "navToday", route: "today", icon: <SunIcon /> },
      { key: "navConsilium", route: "consilium", icon: <StethoscopeIcon /> },
      { key: "navCharts", route: "charts", icon: <LineChartIcon /> },
      { key: "navLabs", route: "labs", icon: <FlaskConicalIcon /> },
      { key: "navTasks", route: "tasks", icon: <ListChecksIcon /> },
      { key: "navMeds", route: "meds", icon: <PillIcon /> },
      { key: "navProfile", route: "profile", icon: <ClipboardListIcon /> },
    ],
  },
  {
    items: [{ key: "navConnect", route: "connect", icon: <PlugIcon /> }],
  },
];

export const footerNavLinks: SidebarNavItem[] = [
  { key: "navDoctor", route: "visit-pack", icon: <FileTextIcon /> },
];

export const navLinks: SidebarNavItem[] = [
  ...navGroups.flatMap((group) => group.items),
  ...footerNavLinks,
];
