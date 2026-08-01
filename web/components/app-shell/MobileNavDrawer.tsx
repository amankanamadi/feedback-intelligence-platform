"use client";

import { useEffect } from "react";
import { Home, X } from "lucide-react";
import { SidebarNav } from "@/components/app-shell/SidebarNav";
import { Button } from "@/components/ui/button";

// Below md, AppSidebar is `hidden` - without this, mobile visitors would
// have zero way to navigate the app at all. Rendered only while open, on
// top of everything, with a backdrop click and Escape both closing it.
export function MobileNavDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 md:hidden">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-label="Navigation" className="absolute inset-y-0 left-0 flex w-64 flex-col bg-card">
        <div className="flex items-center justify-between px-4 py-5">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <Home className="size-6 text-primary" aria-hidden="true" />
            <span className="leading-tight">
              Airbnb
              <span className="block text-xs font-medium text-muted-foreground">Guest Experience Intelligence</span>
            </span>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close navigation">
            <X className="size-4" />
          </Button>
        </div>
        <SidebarNav onNavigate={onClose} />
      </div>
    </div>
  );
}
