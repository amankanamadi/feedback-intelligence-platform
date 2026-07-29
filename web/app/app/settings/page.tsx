import { Settings } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function SettingsPage() {
  return (
    <EmptyState
      icon={<Settings className="size-10" aria-hidden="true" />}
      title="System settings coming soon"
      description="This page will hold platform-wide configuration."
    />
  );
}
