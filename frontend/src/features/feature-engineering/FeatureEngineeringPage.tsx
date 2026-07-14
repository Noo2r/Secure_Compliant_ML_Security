import { useQuery } from "@tanstack/react-query";
import { Wand2 } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { getFeatureEngineeringSummary } from "@/services/feature-engineering-service";
import { PipelineFlow } from "./components/PipelineFlow";
import { FeatureFunnelChart } from "./components/FeatureFunnelChart";

export default function FeatureEngineeringPage() {
  const { data, isLoading } = useQuery({ queryKey: ["feature-engineering"], queryFn: getFeatureEngineeringSummary });

  return (
    <div>
      <PageHeader
        title="Feature Engineering"
        description="Module 2 — deterministic transformers followed by a four-method statistical selection funnel"
        badge={<VerificationBadge status="verified" />}
      />

      {isLoading || !data ? (
        <div className="space-y-6">
          <Skeleton className="h-16 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      ) : (
        <div className="space-y-6">
          <Section title="Pipeline Flow" description="End-to-end path from raw tables to the model-ready dataset">
            <PipelineFlow steps={data.pipelineSteps} />
          </Section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Section title="Feature Selection Funnel" description="466 candidates reduced to 150 via a two-stage cheap filter">
              <FeatureFunnelChart funnel={data.funnel} />
            </Section>

            <Section title="Selected Feature Composition" description={`${data.categoryBreakdown[0].value} numeric, ${data.categoryBreakdown[1].value} categorical`}>
              <div className="flex h-[280px] flex-col justify-center gap-6">
                {data.categoryBreakdown.map((cat) => {
                  const total = data.categoryBreakdown.reduce((s, c) => s + c.value, 0);
                  const pct = Math.round((cat.value / total) * 100);
                  return (
                    <div key={cat.name}>
                      <div className="mb-1.5 flex items-center justify-between text-sm">
                        <span className="font-medium text-foreground">{cat.name}</span>
                        <span className="text-muted-foreground">
                          {cat.value} ({pct}%)
                        </span>
                      </div>
                      <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${pct}%`, opacity: cat.name === "Numeric" ? 1 : 0.6 }}
                        />
                      </div>
                    </div>
                  );
                })}
                <p className="text-xs text-muted-foreground">
                  Consensus selection averages normalized rank across mutual information and embedded Random Forest importance,
                  scored on a systematically time-ordered 50,000-row sample.
                </p>
              </div>
            </Section>
          </div>

          <Section title="Engineering Transformers" description="Six deterministic transformers applied in sequence, no target leakage" noPadding>
            <div className="divide-y divide-border">
              {data.transformers.map((t) => (
                <div key={t.name} className="flex items-start gap-3 px-5 py-3.5">
                  <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <Wand2 className="size-4 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-mono text-sm font-medium text-foreground">{t.name}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{t.description}</p>
                    <p className="mt-1 font-mono text-[11px] text-primary/80">→ {t.outputExample}</p>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}
