import { Tags } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function CategoriesPage() {
  return (
    <EmptyState
      icon={<Tags className="size-10" aria-hidden="true" />}
      title="Category taxonomy management coming soon"
      description="This page will let operations staff manage the case category/sub-category taxonomy and the staff-assignable tag vocabulary used to organize guest and host feedback."
    />
  );
}
