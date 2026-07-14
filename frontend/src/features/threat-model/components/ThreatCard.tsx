import { cn } from "@/lib/utils";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { Badge } from "@/components/ui/badge";
import type { ThreatRow } from "@/types/domain";

const RISK_CLASS = {
  Low: "border-success/30 bg-success/10 text-success",
  Medium: "border-warning/30 bg-warning/10 text-warning",
  High: "border-destructive/30 bg-destructive/10 text-destructive",
};

export function ThreatCard({ threat }: { threat: ThreatRow }) {
  return (
    <div className="rounded-lg border border-border p-4">
      <div className="mb-2 flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{threat.asset}</p>
        <Badge variant="outline" className={cn("shrink-0 text-[10px]", RISK_CLASS[threat.residualRisk])}>
          {threat.residualRisk} risk
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground">
        <span className="font-medium text-foreground/80">Attack vector: </span>
        {threat.attackVector}
      </p>
      <p className="mt-1.5 text-xs text-muted-foreground">
        <span className="font-medium text-foreground/80">Existing control: </span>
        {threat.existingControl}
      </p>
      <div className="mt-3">
        <VerificationBadge status={threat.status} />
      </div>
    </div>
  );
}
