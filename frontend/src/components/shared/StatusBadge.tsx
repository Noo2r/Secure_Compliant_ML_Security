import { cn } from "@/lib/utils";
import type { HealthState, VerificationStatus } from "@/types/domain";
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle, Beaker, FlaskConical, Wrench, Target, Circle } from "lucide-react";

const HEALTH_MAP: Record<HealthState, { label: string; className: string; icon: typeof CheckCircle2 }> = {
  healthy: { label: "Healthy", className: "bg-success/15 text-success border-success/30", icon: CheckCircle2 },
  warning: { label: "Warning", className: "bg-warning/15 text-warning border-warning/30", icon: AlertTriangle },
  critical: { label: "Critical", className: "bg-destructive/15 text-destructive border-destructive/30", icon: XCircle },
  unknown: { label: "Unknown", className: "bg-muted text-muted-foreground border-border", icon: HelpCircle },
};

export function HealthBadge({ status, className }: { status: HealthState; className?: string }) {
  const cfg = HEALTH_MAP[status];
  const Icon = cfg.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        cfg.className,
        className,
      )}
    >
      <Icon className="size-3.5" />
      {cfg.label}
    </span>
  );
}

const VERIFICATION_MAP: Record<VerificationStatus, { label: string; className: string; icon: typeof CheckCircle2 }> = {
  verified: { label: "Implemented & Verified", className: "bg-success/15 text-success border-success/30", icon: CheckCircle2 },
  locally_tested: { label: "Locally Tested", className: "bg-primary/15 text-primary border-primary/30", icon: Beaker },
  unit_tested: { label: "Unit Tested", className: "bg-primary/15 text-primary border-primary/30", icon: FlaskConical },
  dry_run: { label: "Dry-Run Verified", className: "bg-warning/15 text-warning border-warning/30", icon: Wrench },
  designed_not_deployed: { label: "Designed, Not Deployed", className: "bg-warning/15 text-warning border-warning/30", icon: Target },
  target_state: { label: "Target State", className: "bg-muted-foreground/15 text-muted-foreground border-border", icon: Circle },
  partial: { label: "Partially Implemented", className: "bg-warning/15 text-warning border-warning/30", icon: AlertTriangle },
  not_verified: { label: "Not Independently Verified", className: "bg-muted text-muted-foreground border-border", icon: HelpCircle },
  future_work: { label: "Recommended Future Work", className: "bg-muted text-muted-foreground border-border", icon: Circle },
};

export function VerificationBadge({ status, className }: { status: VerificationStatus; className?: string }) {
  const cfg = VERIFICATION_MAP[status];
  const Icon = cfg.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        cfg.className,
        className,
      )}
    >
      <Icon className="size-3.5 shrink-0" />
      {cfg.label}
    </span>
  );
}
