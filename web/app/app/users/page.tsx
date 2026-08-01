import { Users } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function UsersPage() {
  return (
    <EmptyState
      icon={<Users className="size-10" aria-hidden="true" />}
      title="User management coming soon"
      description="This page will let you view, deactivate, and manage roles for guest, host, and Airbnb operations staff accounts (Support Manager, Ops Manager, Product Manager, Executive Leadership)."
    />
  );
}
