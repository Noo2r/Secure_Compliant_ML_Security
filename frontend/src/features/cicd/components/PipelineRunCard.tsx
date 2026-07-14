import { CheckCircle2, XCircle, MinusCircle, Loader2, GitBranch, GitCommitHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatDuration, formatRelativeTime } from "@/lib/format";
import type { CiRun, CiPipelineStage } from "@/types/domain";

const STAGE_ICON: Record<CiPipelineStage["status"], typeof CheckCircle2> = {
  success: CheckCircle2,
  failed: XCircle,
  skipped: MinusCircle,
  running: Loader2,
};

const STAGE_COLOR: Record<CiPipelineStage["status"], string> = {
  success: "text-success",
  failed: "text-destructive",
  skipped: "text-muted-foreground",
  running: "text-primary",
};

export function PipelineRunCard({ run, defaultExpanded }: { run: CiRun; defaultExpanded?: boolean }) {
  return (
    <div className="rounded-xl border border-border p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <Badge
            variant="outline"
            className={cn(
              "text-[10px]",
              run.status === "success" && "border-success/30 bg-success/10 text-success",
              run.status === "failed" && "border-destructive/30 bg-destructive/10 text-destructive",
              run.status === "running" && "border-primary/30 bg-primary/10 text-primary",
            )}
          >
            {run.status}
          </Badge>
          <span className="font-mono text-sm font-medium text-foreground">#{run.id}</span>
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <GitBranch className="size-3" /> {run.branch}
          </span>
          <span className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
            <GitCommitHorizontal className="size-3" /> {run.commitSha}
          </span>
        </div>
        <span className="text-xs text-muted-foreground">{formatRelativeTime(run.startedAt)}</span>
      </div>

      <p className="mb-3 text-sm text-foreground">{run.commitMessage}</p>

      {defaultExpanded && (
        <div className="space-y-1.5 border-t border-border pt-3">
          {run.stages.map((stage) => {
            const Icon = STAGE_ICON[stage.status];
            return (
              <div key={stage.id} className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 hover:bg-muted/40">
                <div className="flex min-w-0 items-center gap-2">
                  <Icon className={cn("size-3.5 shrink-0", STAGE_COLOR[stage.status], stage.status === "running" && "animate-spin")} />
                  <span className="truncate text-sm text-foreground">{stage.name}</span>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="hidden text-xs text-muted-foreground sm:inline">{stage.detail}</span>
                  <span className="font-mono text-xs text-muted-foreground">{formatDuration(stage.durationSec)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
