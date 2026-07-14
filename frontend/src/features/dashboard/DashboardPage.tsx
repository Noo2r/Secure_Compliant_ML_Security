import {
  Activity,
  Boxes,
  ShieldCheck,
  Lock,
  Scale,
  Percent,
  Gauge,
  FileCheck2,
  TestTube2,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatCard } from "@/components/shared/StatCard";
import { Section } from "@/components/shared/Section";
import { HealthBadge } from "@/components/shared/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboard } from "./use-dashboard";
import { PipelineTimeline } from "./components/PipelineTimeline";
import { ActivityFeed } from "./components/ActivityFeed";
import { LeaderboardMiniChart } from "./components/LeaderboardMiniChart";
import { formatPercent, formatDecimal, formatNumber } from "@/lib/format";

export default function DashboardPage() {
  const { data, isLoading } = useDashboard();

  return (
    <div>
      <PageHeader
        title="System Overview"
        description="Live status across all five milestones of the secure fraud-detection pipeline"
        badge={!isLoading && data && <HealthBadge status={data.systemStatus} />}
      />

      {isLoading || !data ? (
        <DashboardSkeleton />
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard index={0} label="Latest Model" value={data.latestModel} icon={Boxes} hint={data.modelVersion} accent="primary" />
            <StatCard index={1} label="Holdout PR-AUC" value={formatDecimal(data.prAuc, 4)} icon={Gauge} hint={`ROC-AUC ${formatDecimal(data.rocAuc, 4)}`} accent="success" />
            <StatCard index={2} label="Selected Features" value={formatNumber(data.featureCount)} icon={ShieldCheck} hint="from 466 candidates" accent="primary" />
            <StatCard index={3} label="Fraud Rate" value={formatPercent(data.fraudRate, 2)} icon={Percent} hint="590,540 transactions" accent="warning" />
            <StatCard index={4} label="Privacy Budget (ε)" value={formatDecimal(data.privacyEpsilon, 3)} icon={Lock} hint="δ = 1e-5, DP-SGD" accent="warning" />
            <StatCard
              index={5}
              label="Fairness Findings"
              value={`${data.significantFairnessFindings}/${data.fairnessFindingsCount}`}
              icon={Scale}
              hint="statistically significant"
              accent="warning"
            />
            <StatCard index={6} label="Compliance Score" value={`${data.complianceScorePct}%`} icon={FileCheck2} hint="GDPR + ISO 27001 controls" accent="primary" />
            <StatCard index={7} label="Test Suite" value={data.testsPassing} icon={TestTube2} hint="35 files, pytest --collect-only" accent="success" />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Section title="Pipeline Timeline" description="Real status per milestone module" className="lg:col-span-2">
              <PipelineTimeline stages={data.timeline} />
            </Section>

            <Section title="Live Status" description="Component-level health">
              <div className="space-y-3">
                <StatusRow label="Inference API" status={data.apiStatus} />
                <StatusRow label="Container Runtime" status={data.containerStatus} />
                <StatusRow label="Drift Monitor" status={data.driftStatus} />
                <StatusRow label="Pipeline" status={data.pipelineStatus} />
              </div>
            </Section>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Section title="Model Leaderboard" description="Holdout PR-AUC across 5 model families" className="lg:col-span-2">
              <LeaderboardMiniChart />
            </Section>

            <Section title="Recent Activity" description="Latest pipeline & platform events" noPadding>
              <div className="px-5 py-2">
                <ActivityFeed items={data.activity} />
              </div>
            </Section>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusRow({ label, status }: { label: string; status: Parameters<typeof HealthBadge>[0]["status"] }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-3 py-2.5">
      <div className="flex items-center gap-2 text-sm text-foreground">
        <Activity className="size-3.5 text-muted-foreground" />
        {label}
      </div>
      <HealthBadge status={status} />
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-[104px] rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Skeleton className="h-64 rounded-xl lg:col-span-2" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    </div>
  );
}
