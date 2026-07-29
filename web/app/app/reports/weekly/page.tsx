import { WeeklyReportPanel } from "@/components/admin/WeeklyReportPanel";

export default function WeeklyReportPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Weekly report</h1>
        <p className="text-muted-foreground">Generate an AI-written executive summary of the last 7 days.</p>
      </div>
      <WeeklyReportPanel />
    </div>
  );
}
