import { useQuery } from "@tanstack/react-query";
import { Activity, FlaskConical } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { StatCard } from "@/components/shared/StatCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { HealthBadge } from "@/components/shared/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getDriftReport } from "@/services/drift-service";
import { DriftTrendChart } from "./components/DriftTrendChart";
import { formatDecimal } from "@/lib/format";

export default function DriftMonitoringPage() {
  const { data, isLoading } = useQuery({ queryKey: ["drift-report"], queryFn: getDriftReport });

  return (
    <div>
      <PageHeader
        title="Drift Monitoring"
        description="Evidently-based data-drift detection comparing reference vs. current feature distributions"
        badge={!isLoading && data && <HealthBadge status={data.overallStatus} />}
      />

      {isLoading || !data ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard index={0} label="Dataset Drift" value={data.datasetDriftDetected ? "Detected" : "Not Detected"} icon={Activity} accent={data.datasetDriftDetected ? "warning" : "success"} />
            <StatCard index={1} label="Drifted Features" value={`${data.driftedFeatureCount}/${data.totalFeaturesChecked}`} icon={Activity} hint="PSI-based per-feature check" accent={data.driftedFeatureCount > 0 ? "warning" : "success"} />
            <StatCard index={2} label="Data Source" value={data.usedSyntheticFallback ? "Synthetic fallback" : "Real batch"} icon={FlaskConical} hint="No live production traffic exists" accent="warning" />
          </div>

          {data.usedSyntheticFallback && (
            <Alert>
              <FlaskConical className="size-4" />
              <AlertTitle>Synthetic fallback data, not production monitoring</AlertTitle>
              <AlertDescription>
                When reference/current batch files are absent from a fresh checkout, drift_monitor.py falls back to
                gitignored synthetic data rather than failing the CI job. This is not live production traffic.
              </AlertDescription>
            </Alert>
          )}

          <Section title="Drift Trend" description="Drifted feature count across recent monitoring runs">
            <DriftTrendChart trend={data.trend} />
          </Section>

          <Section title="Per-Feature PSI" description="Population Stability Index — reference vs. current distribution" noPadding>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Feature</TableHead>
                  <TableHead className="text-right">PSI</TableHead>
                  <TableHead className="text-right">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.features.map((f) => (
                  <TableRow key={f.feature}>
                    <TableCell className="font-mono text-xs">{f.feature}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{formatDecimal(f.psi, 3)}</TableCell>
                    <TableCell className="text-right">
                      <HealthBadge status={f.status} className="ml-auto" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Section>
        </div>
      )}
    </div>
  );
}
