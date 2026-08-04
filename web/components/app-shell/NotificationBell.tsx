"use client";

import { useRouter } from "next/navigation";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { useNotifications, useMarkNotificationReadMutation } from "@/hooks/use-notifications";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { NotificationRead } from "@/types/notification";

export function NotificationBell() {
  const router = useRouter();
  const { data: notifications } = useNotifications();
  const markRead = useMarkNotificationReadMutation();
  const unreadCount = notifications?.filter((n) => !n.read_at).length ?? 0;

  const handleSelect = (notification: NotificationRead) => {
    if (!notification.read_at) markRead.mutate(notification.id);
    if (notification.link) router.push(notification.link);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="relative" aria-label="Notifications">
          <Bell className="size-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -right-1 -top-1 h-5 min-w-5 justify-center rounded-full px-1 text-[10px]"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {(!notifications || notifications.length === 0) && (
          <p className="px-2 py-4 text-center text-sm text-muted-foreground">No notifications</p>
        )}
        {notifications?.map((notification) => (
          <DropdownMenuItem
            key={notification.id}
            onSelect={() => handleSelect(notification)}
            className={cn("flex-col items-start gap-0.5", !notification.read_at && "bg-primary/5")}
          >
            <p
              className={cn(
                "text-sm",
                !notification.read_at ? "font-medium text-foreground" : "text-muted-foreground"
              )}
            >
              {notification.message}
            </p>
            <p className="text-xs text-muted-foreground">{formatRelative(notification.created_at)}</p>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
