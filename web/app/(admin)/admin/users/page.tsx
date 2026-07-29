import { Users } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function AdminUsersPage() {
  return (
    <EmptyState
      icon={<Users className="size-10" aria-hidden="true" />}
      title="User management coming soon"
      description="This page will let you view, deactivate, and manage roles for USER and ADMIN accounts."
    />
  );
}
