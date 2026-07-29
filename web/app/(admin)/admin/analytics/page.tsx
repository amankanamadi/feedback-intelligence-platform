import { BarChart3 } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function AdminAnalyticsPage() {
  return (
    <EmptyState
      icon={<BarChart3 className="size-10" aria-hidden="true" />}
      title="Analytics dashboard coming soon"
      description="This page will show KPI cards and charts for sentiment, category, and trend distribution."
    />
  );
}
