import { Home } from "lucide-react";
import { SidebarNav } from "@/components/app-shell/SidebarNav";

export function AppSidebar() {
  return (
    <aside className="hidden w-64 flex-col border-r border-border bg-card md:flex">
      <div className="flex items-center gap-2 px-6 py-5 font-semibold text-foreground">
        <Home className="size-6 text-primary" aria-hidden="true" />
        <span className="leading-tight">
          Airbnb
          <span className="block text-xs font-medium text-muted-foreground">Guest Experience Intelligence</span>
        </span>
      </div>
      <SidebarNav />
    </aside>
  );
}
