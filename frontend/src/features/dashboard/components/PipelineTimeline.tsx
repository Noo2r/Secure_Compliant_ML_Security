import { Check, AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HealthState } from "@/types/domain";

interface TimelineStage {
  label: string;
  status: HealthState;
  detail: string;
}

const ICON_MAP: Record<HealthState, typeof Check> = {
  healthy: Check,
  warning: AlertTriangle,
  critical: X,
  unknown: AlertTriangle,
};

const DOT_MAP: Record<HealthState, string> = {
  healthy: "bg-success text-success-foreground",
  warning: "bg-warning text-warning-foreground",
  critical: "bg-destructive text-destructive-foreground",
  unknown: "bg-muted text-muted-foreground",
};

export function PipelineTimeline({ stages }: { stages: TimelineStage[] }) {
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
      {stages.map((stage, i) => {
        const Icon = ICON_MAP[stage.status];
        return (
          <div key={stage.label} className="relative flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <div className={cn("flex size-6 shrink-0 items-center justify-center rounded-full", DOT_MAP[stage.status])}>
                <Icon className="size-3.5" />
              </div>
              {i < stages.length - 1 && <div className="hidden h-px flex-1 bg-border sm:block" />}
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">{stage.label}</p>
              <p className="text-xs text-muted-foreground">{stage.detail}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
