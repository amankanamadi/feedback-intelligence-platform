import { FileClock } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function AuditLogsPage() {
  return (
    <EmptyState
      icon={<FileClock className="size-10" aria-hidden="true" />}
      title="Audit logs coming soon"
      description="This page will show a history of admin actions on feedback (status/priority/notes/response changes)."
    />
  );
}
