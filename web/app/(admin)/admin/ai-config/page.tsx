import { Sliders } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function AiConfigPage() {
  return (
    <EmptyState
      icon={<Sliders className="size-10" aria-hidden="true" />}
      title="AI configuration coming soon"
      description="This page will expose classification model and retrieval settings currently managed via environment variables."
    />
  );
}
