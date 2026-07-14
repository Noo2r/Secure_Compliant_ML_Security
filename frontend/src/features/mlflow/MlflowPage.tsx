import { useQuery } from "@tanstack/react-query";
import { FlaskConical, Database } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getMlflowRuns, getRegistry, MLFLOW_NOTE } from "@/services/mlflow-service";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { formatDecimal, formatDateTime, formatDuration } from "@/lib/format";

export default function MlflowPage() {
  const { data: runs, isLoading: loadingRuns } = useQuery({ queryKey: ["mlflow-runs"], queryFn: getMlflowRuns });
  const { data: registry, isLoading: loadingRegistry } = useQuery({ queryKey: ["mlflow-registry"], queryFn: getRegistry });
  const isLoading = loadingRuns || loadingRegistry;

  return (
    <div>
      <PageHeader
        title="MLflow"
        description="Local experiment tracking store — parameters, metrics, and artifacts for every training run"
        badge={<VerificationBadge status="locally_tested" />}
      />

      {isLoading || !runs || !registry ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : (
        <div className="space-y-6">
          <Alert>
            <Database className="size-4" />
            <AlertTitle>Local tracking store, not a deployed registry</AlertTitle>
            <AlertDescription>{MLFLOW_NOTE}</AlertDescription>
          </Alert>

          <Section title="Experiment Runs" noPadding>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run</TableHead>
                    <TableHead>Model</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">PR-AUC</TableHead>
                    <TableHead className="text-right">ROC-AUC</TableHead>
                    <TableHead className="text-right">Duration</TableHead>
                    <TableHead className="text-right">Started</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-mono text-xs">{r.runName}</TableCell>
                      <TableCell className="text-sm font-medium">{r.model}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="border-success/30 bg-success/10 text-[10px] text-success">
                          {r.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">{formatDecimal(r.prAuc, 4)}</TableCell>
                      <TableCell className="text-right font-mono text-xs">{formatDecimal(r.rocAuc, 4)}</TableCell>
                      <TableCell className="text-right font-mono text-xs">{formatDuration(r.durationSec)}</TableCell>
                      <TableCell className="text-right text-xs text-muted-foreground">{formatDateTime(r.startedAt)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Section>

          <Section title="Model Registry" description="Persisted inference bundles, no production stage transitions" noPadding>
            <div className="divide-y divide-border">
              {registry.map((r) => (
                <div key={r.name} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10">
                      <FlaskConical className="size-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {r.name} <span className="text-muted-foreground">v{r.version}</span>
                      </p>
                      <p className="font-mono text-[11px] text-muted-foreground/70">{r.artifactPath}</p>
                    </div>
                  </div>
                  <Badge variant="secondary" className="text-[10px]">
                    {r.stage}
                  </Badge>
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}
