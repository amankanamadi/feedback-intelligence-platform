"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  FileClock,
  Inbox,
  Settings,
  ShieldCheck,
  Sliders,
  Tags,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
};

type NavGroup = {
  label: string;
  items: NavItem[];
};

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Feedback Management",
    items: [{ href: "/admin/feedback", label: "All Feedback", icon: Inbox }],
  },
  {
    label: "Analytics",
    items: [
      { href: "/admin/analytics", label: "Dashboard", icon: BarChart3 },
      { href: "/admin/reports/weekly", label: "Weekly Report", icon: FileClock },
    ],
  },
  {
    label: "Administration",
    items: [
      { href: "/admin/users", label: "Users", icon: Users },
      { href: "/admin/categories", label: "Categories", icon: Tags },
      { href: "/admin/ai-config", label: "AI Configuration", icon: Sliders },
      { href: "/admin/settings", label: "System Settings", icon: Settings },
      { href: "/admin/audit-logs", label: "Audit Logs", icon: FileClock },
    ],
  },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-64 flex-col border-r border-border bg-card md:flex">
      <div className="flex items-center gap-2 px-6 py-5 font-semibold text-foreground">
        <ShieldCheck className="size-6 text-primary" aria-hidden="true" />
        Admin Console
      </div>
      <nav className="flex flex-1 flex-col gap-6 overflow-y-auto px-3 pb-6">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="flex flex-col gap-1">
            <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{group.label}</p>
            {group.items.map((item) => {
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
                  <item.icon className="size-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
