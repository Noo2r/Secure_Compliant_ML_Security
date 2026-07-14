import { useQuery } from "@tanstack/react-query";
import { Lock, TrendingDown, ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { MetricRow, MetricGrid } from "@/components/shared/MetricRow";
import { getDpReport } from "@/services/dp-service";
import { DpComparisonChart } from "./components/DpComparisonChart";
import { formatDecimal, formatDuration } from "@/lib/format";

const PIPELINE = ["Normal Model", "DP-SGD Training", "Privacy Accountant (RDP)", "ε Computation", "Performance Comparison"];

export default function DifferentialPrivacyPage() {
  const { data, isLoading } = useQuery({ queryKey: ["dp-report"], queryFn: getDpReport });

  return (
    <div>
      <PageHeader
        title="Differential Privacy"
        description="Module 4 — DP-SGD training with a formal (ε, δ)-privacy guarantee, and its honest utility cost"
        badge={<VerificationBadge status="verified" />}
      />

      {isLoading || !data ? (
        <div className="space-y-6">
          <Skeleton className="h-16 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      ) : (
        <div className="space-y-6">
          <Section title="DP Training Pipeline">
            <div className="flex flex-wrap items-center gap-2">
              {PIPELINE.map((step, i) => (
                <div key={step} className="flex items-center gap-2">
                  <div className="rounded-lg border border-border bg-muted/40 px-3.5 py-2 text-sm font-medium text-foreground">{step}</div>
                  {i < PIPELINE.length - 1 && <ArrowRight className="size-4 shrink-0 text-muted-foreground" />}
                </div>
              ))}
            </div>
          </Section>

          <Alert variant="destructive">
            <TrendingDown className="size-4" />
            <AlertTitle>Significant utility cost — reported honestly, not minimized</AlertTitle>
            <AlertDescription>
              PR-AUC dropped from {formatDecimal(data.metrics.find((m) => m.metric === "PR-AUC")!.normal, 4)} (normal) to{" "}
              {formatDecimal(data.metrics.find((m) => m.metric === "PR-AUC")!.dp, 4)} (DP), a {data.prAucRelativeDropPct}% relative
              change, at privacy budget ε={formatDecimal(data.epsilon, 3)}. This configuration is not yet suitable as the primary
              production fraud-detection model — the gap is driven by per-example gradient clipping and calibrated Gaussian noise,
              both required for the formal privacy guarantee.
            </AlertDescription>
          </Alert>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Section title="Privacy Parameters" className="lg:col-span-1">
              <MetricRow label="Epsilon (ε)" value={formatDecimal(data.epsilon, 3)} hint="Shuffled-epoch RDP accounting" />
              <MetricRow label="Delta (δ)" value={data.delta.toExponential(0)} />
              <MetricRow label="Noise multiplier" value={data.noiseMultiplier} />
              <MetricRow label="L2 clipping norm" value={data.clippingNorm} />
              <MetricRow label="Microbatches" value={data.microbatches} hint="= batch size → true per-example clipping" />
              <MetricRow label="Batch size" value={data.batchSize} />
              <MetricRow label="Epochs" value={data.epochs} />
              <MetricRow label="Training time (Normal)" value={formatDuration(data.trainingTimeNormalSec)} />
              <MetricRow label="Training time (DP)" value={formatDuration(data.trainingTimeDpSec)} hint="~17.8x the normal run" />
            </Section>

            <Section title="Normal vs. DP-SGD Performance" className="lg:col-span-2">
              <DpComparisonChart metrics={data.metrics} />
            </Section>
          </div>

          <Section title="Detailed Metric Comparison" noPadding>
            <div className="p-5">
              <MetricGrid cols={3}>
                {data.metrics.map((m) => (
                  <div key={m.metric} className="rounded-lg border border-border p-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">{m.metric}</p>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-success">{formatDecimal(m.normal, 4)}</span>
                      <ArrowRight className="size-3 text-muted-foreground" />
                      <span className="text-destructive">{formatDecimal(m.dp, 4)}</span>
                    </div>
                  </div>
                ))}
              </MetricGrid>
            </div>
          </Section>

          <Alert>
            <Lock className="size-4" />
            <AlertTitle>Recommended future work (not implemented)</AlertTitle>
            <AlertDescription>
              Larger effective batch sizes, alternative clipping strategies, better privacy-budget tuning, class-balancing
              adjustments, and architecture changes are documented recommendations — none have been built or verified yet.
            </AlertDescription>
          </Alert>
        </div>
      )}
    </div>
  );
}
