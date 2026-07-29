import { FileClock } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function WeeklyReportPage() {
  return (
    <EmptyState
      icon={<FileClock className="size-10" aria-hidden="true" />}
      title="Weekly executive summary coming soon"
      description="This page will generate an AI-written weekly narrative over your feedback metrics."
    />
  );
}
