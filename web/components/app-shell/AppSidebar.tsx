import { MessageSquareHeart } from "lucide-react";
import { SidebarNav } from "@/components/app-shell/SidebarNav";

export function AppSidebar() {
  return (
    <aside className="hidden w-64 flex-col border-r border-border bg-card md:flex">
      <div className="flex items-center gap-2 px-6 py-5 font-semibold text-foreground">
        <MessageSquareHeart className="size-6 text-primary" aria-hidden="true" />
        Feedback Intelligence
      </div>
      <SidebarNav />
    </aside>
  );
}
