"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Building2,
  FileClock,
  Heart,
  Home,
  Inbox,
  MessageSquarePlus,
  Settings,
  ShieldAlert,
  Sliders,
  Tags,
  User,
  Users,
} from "lucide-react";
import { useIsGuest } from "@/hooks/use-is-guest";
import { useIsHost } from "@/hooks/use-is-host";
import { useIsManager } from "@/hooks/use-is-manager";
import { useIsStaff } from "@/hooks/use-is-staff";
import { useIsTrustSafety } from "@/hooks/use-is-trust-safety";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
};

type NavGroup = {
  label?: string;
  staffOnly?: boolean;
  hostOnly?: boolean;
  guestOnly?: boolean;
  manageOnly?: boolean;
  trustSafetyOnly?: boolean;
  items: NavItem[];
};

// One nav list for everyone - staff-only groups simply don't render for a
// Guest/Host, rather than living in a separate portal/route tree.
const NAV_GROUPS: NavGroup[] = [
  {
    items: [
      { href: "/app/feedback/new", label: "Submit Feedback", icon: MessageSquarePlus },
      { href: "/app/feedback", label: "Feedback", icon: Inbox },
      { href: "/app/properties", label: "Properties", icon: Building2 },
      { href: "/app/profile", label: "Profile", icon: User },
    ],
  },
  {
    label: "Guest",
    guestOnly: true,
    items: [{ href: "/app/wishlist", label: "My Wishlist", icon: Heart }],
  },
  {
    label: "Host",
    hostOnly: true,
    items: [{ href: "/app/host", label: "Host Dashboard", icon: Home }],
  },
  {
    label: "Analytics",
    staffOnly: true,
    items: [
      { href: "/app/analytics", label: "Dashboard", icon: BarChart3 },
      { href: "/app/reports/weekly", label: "Weekly Report", icon: FileClock },
    ],
  },
  {
    label: "Operations Queue",
    manageOnly: true,
    items: [{ href: "/app/operations", label: "Operations Queue", icon: Inbox }],
  },
  {
    label: "Trust & Safety",
    trustSafetyOnly: true,
    items: [{ href: "/app/trust-safety", label: "Trust & Safety Queue", icon: ShieldAlert }],
  },
  {
    label: "Operations",
    staffOnly: true,
    items: [
      { href: "/app/users", label: "Users", icon: Users },
      { href: "/app/categories", label: "Category Taxonomy", icon: Tags },
      { href: "/app/ai-config", label: "AI Configuration", icon: Sliders },
      { href: "/app/settings", label: "System Settings", icon: Settings },
      { href: "/app/audit-logs", label: "Audit Logs", icon: FileClock },
    ],
  },
];

// Picks the single longest matching href across all nav items, so a page
// like /app/feedback/new only lights up "Submit Feedback" - not also
// "Feedback", which would otherwise match via a plain startsWith("/app/feedback/").
function findActiveHref(pathname: string): string | null {
  const allHrefs = NAV_GROUPS.flatMap((group) => group.items.map((item) => item.href));
  const matches = allHrefs.filter((href) => pathname === href || pathname.startsWith(`${href}/`));
  if (matches.length === 0) return null;
  return matches.reduce((longest, href) => (href.length > longest.length ? href : longest));
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const isStaff = useIsStaff();
  const isHost = useIsHost();
  const isGuest = useIsGuest();
  const isManager = useIsManager();
  const isTrustSafety = useIsTrustSafety();
  const activeHref = findActiveHref(pathname);

  return (
    <nav className="flex flex-1 flex-col gap-6 overflow-y-auto px-3 pb-6">
      {NAV_GROUPS.filter(
        (group) =>
          (!group.staffOnly || isStaff) &&
          (!group.hostOnly || isHost) &&
          (!group.guestOnly || isGuest) &&
          (!group.manageOnly || isManager) &&
          (!group.trustSafetyOnly || isTrustSafety)
      ).map((group, index) => (
        <div key={group.label ?? index} className="flex flex-col gap-1">
          {group.label && (
            <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{group.label}</p>
          )}
          {group.items.map((item) => {
            const active = item.href === activeHref;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
