import { UserCog } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function ProfilePage() {
  return (
    <EmptyState
      icon={<UserCog className="size-10" aria-hidden="true" />}
      title="Profile settings coming soon"
      description="This page will let you update your profile and change your password."
      className="flex-1"
    />
  );
}
