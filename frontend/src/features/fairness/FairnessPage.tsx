import { useQuery } from "@tanstack/react-query";
import { Scale, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { StatCard } from "@/components/shared/StatCard";
import { getFairnessMetrics, BIAS_FINDINGS } from "@/services/fairness-service";
import { DirChart } from "./components/DirChart";
import { FairnessTable } from "./components/FairnessTable";

const SEVERITY_CLASS = {
  high: "border-destructive/30 bg-destructive/10 text-destructive",
  medium: "border-warning/30 bg-warning/10 text-warning",
  low: "border-muted-foreground/20 bg-muted text-muted-foreground",
};

export default function FairnessPage() {
  const { data, isLoading } = useQuery({ queryKey: ["fairness-metrics"], queryFn: getFairnessMetrics });
  const significantCount = data?.filter((m) => m.dirSignificant || m.eodSignificant || m.spdSignificant).length ?? 0;

  return (
    <div>
      <PageHeader
        title="Fairness Analysis"
        description="Module 5 — bias metrics across three proxy attributes (card6, card4, DeviceType); the IEEE-CIS dataset has no genuine demographic field"
        badge={<VerificationBadge status="verified" />}
      />

      {isLoading || !data ? (
        <div className="space-y-6">
          <Skeleton className="h-16 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard index={0} label="Groups Analyzed" value={String(data.length)} icon={Scale} hint="across card6, card4, DeviceType" accent="primary" />
            <StatCard index={1} label="Significant Findings" value={`${significantCount}/${data.length}`} icon={AlertTriangle} hint="at least one metric CI excludes no-disparity" accent="warning" />
            <StatCard index={2} label="Cross-Validation" value="0.0 diff" icon={Scale} hint="vs. Fairlearn on every compared metric" accent="success" />
          </div>

          <Alert>
            <Scale className="size-4" />
            <AlertTitle>Fairness assessment identifies risk — it does not eliminate it</AlertTitle>
            <AlertDescription>
              These proxy attributes (card type, network, device) are the closest available signals in a dataset with no genuine
              demographic field. Findings are reported honestly, including disparities that reflect unfavorably on the model.
            </AlertDescription>
          </Alert>

          <Section title="Disparate Impact Ratio (DIR) by Group" description="Bars show 95% bootstrap CI upper bound; highlighted bars are statistically significant">
            <DirChart metrics={data} />
          </Section>

          <Section title="Full Metric Table" description="SPD, DIR, EOD, AOD with 95% bootstrap confidence intervals" noPadding>
            <FairnessTable metrics={data} />
          </Section>

          <Section title="Bias Findings" description="Narrative summary, consistent with reports_m5/bias_findings.md" noPadding>
            <div className="divide-y divide-border">
              {BIAS_FINDINGS.map((f) => (
                <div key={f.id} className="flex items-start gap-3 px-5 py-3.5">
                  <Badge variant="outline" className={SEVERITY_CLASS[f.severity]}>
                    {f.severity}
                  </Badge>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">{f.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{f.detail}</p>
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
