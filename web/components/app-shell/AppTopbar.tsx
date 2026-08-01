"use client";

import { useRouter } from "next/navigation";
import { LogOut, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { useLogoutMutation } from "@/hooks/use-logout";
import { ROLE_LABELS } from "@/types/auth";

export function AppTopbar({ onMenuClick }: { onMenuClick: () => void }) {
  const router = useRouter();
  const { user } = useAuth();
  const logoutMutation = useLogoutMutation();

  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSuccess: () => router.push("/login"),
    });
  };

  return (
    <header className="flex items-center justify-between border-b border-border bg-card px-4 py-4 md:px-6">
      {/* This wrapper has no `hidden` class of its own, so it stays a real
          (if zero-size) flex item on desktop too - putting md:hidden on
          the wrapper itself would remove it from layout entirely, and
          justify-between with only one remaining item left-aligns it
          instead of keeping the user-info/logout block on the right. */}
      <div>
        <Button variant="ghost" size="sm" className="md:hidden" onClick={onMenuClick} aria-label="Open navigation">
          <Menu className="size-5" />
        </Button>
      </div>
      <div className="flex items-center gap-3">
        {user && (
          <div className="text-right">
            <p className="text-sm font-medium text-foreground">{user.full_name ?? user.email}</p>
            <p className="text-xs text-muted-foreground">{ROLE_LABELS[user.role]}</p>
          </div>
        )}
        <Button variant="outline" size="sm" onClick={handleLogout} isLoading={logoutMutation.isPending}>
          <LogOut className="size-4" aria-hidden="true" />
          Log out
        </Button>
      </div>
    </header>
  );
}
