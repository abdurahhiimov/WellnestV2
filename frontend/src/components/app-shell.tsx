import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { FullWidthDivider } from "@/components/full-width-divider";
import { AppHeader } from "@/components/app-header";
import { AppSidebar } from "@/components/app-sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
	return (
		<div className="overflow-x-hidden">
			<SidebarProvider className="relative h-svh w-full">
				<FullWidthDivider className="top-14 z-60 -translate-y-px" />
				<AppSidebar />
				<SidebarInset className="min-w-0">
					<AppHeader />
					<div className="min-w-0 flex flex-1 flex-col gap-4 overflow-y-auto p-4 md:px-8 md:py-6">
						{children}
					</div>
				</SidebarInset>
			</SidebarProvider>
		</div>
	);
}
