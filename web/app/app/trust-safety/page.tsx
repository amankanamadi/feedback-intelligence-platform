import { OperationsQueue } from "@/components/operations/OperationsQueue";

export default function TrustSafetyPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Trust &amp; Safety Queue</h1>
        <p className="text-muted-foreground">Safety, misconduct, and emergency cases routed directly to your team.</p>
      </div>
      <OperationsQueue lockedResponsibleTeam="Trust & Safety" defaultUnresolved={false} />
    </div>
  );
}
