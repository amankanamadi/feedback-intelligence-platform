"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { useLogoutMutation } from "@/hooks/use-logout";

export function AdminTopbar() {
  const router = useRouter();
  const { user } = useAuth();
  const logoutMutation = useLogoutMutation();

  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSuccess: () => router.push("/admin-login"),
    });
  };

  return (
    <header className="flex items-center justify-between border-b border-border bg-card px-6 py-4">
      <div />
      <div className="flex items-center gap-3">
        {user && (
          <div className="text-right">
            <p className="text-sm font-medium text-foreground">{user.full_name ?? user.email}</p>
            <p className="text-xs text-muted-foreground">Administrator</p>
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
