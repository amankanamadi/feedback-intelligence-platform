import { OperationsQueue } from "@/components/operations/OperationsQueue";

export default function OperationsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Operations Queue</h1>
        <p className="text-muted-foreground">Escalations, SLA breaches, and unresolved cases across every team.</p>
      </div>
      <OperationsQueue />
    </div>
  );
}
