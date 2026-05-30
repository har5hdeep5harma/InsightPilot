import type { ReactNode } from "react";
import { SidebarNavigation } from "@/components/layout/sidebar-navigation";
import { TopCommandBar } from "@/components/layout/top-command-bar";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="studio-surface min-h-screen">
      <div className="flex min-h-screen">
        <SidebarNavigation />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopCommandBar />
          {children}
        </div>
      </div>
    </div>
  );
}
