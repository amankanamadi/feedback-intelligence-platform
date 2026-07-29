"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, MessageSquareHeart, MessageSquarePlus, User as UserIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { useLogoutMutation } from "@/hooks/use-logout";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/portal/feedback/new", label: "Submit Feedback", icon: MessageSquarePlus },
  { href: "/portal/feedback/history", label: "My Feedback", icon: MessageSquareHeart },
  { href: "/portal/profile", label: "Profile", icon: UserIcon },
];

export function UserTopbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuth();
  const logoutMutation = useLogoutMutation();

  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSuccess: () => router.push("/login"),
    });
  };

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/portal" className="flex items-center gap-2 font-semibold text-foreground">
          <MessageSquareHeart className="size-6 text-primary" aria-hidden="true" />
          Feedback Intelligence
        </Link>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="size-4" aria-hidden="true" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-3">
          {user && <span className="hidden text-sm text-muted-foreground md:inline">{user.full_name ?? user.email}</span>}
          <Button variant="outline" size="sm" onClick={handleLogout} isLoading={logoutMutation.isPending}>
            <LogOut className="size-4" aria-hidden="true" />
            Log out
          </Button>
        </div>
      </div>
    </header>
  );
}
