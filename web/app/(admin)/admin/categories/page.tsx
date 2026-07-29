import { Tags } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function AdminCategoriesPage() {
  return (
    <EmptyState
      icon={<Tags className="size-10" aria-hidden="true" />}
      title="Category management coming soon"
      description="This page will let you manage the admin-assignable tag vocabulary used to organize feedback."
    />
  );
}
