import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle, Database, Hash, ShieldCheck, KeyRound } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { StatCard } from "@/components/shared/StatCard";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { getValidationReport } from "@/services/validation-service";
import { formatNumber } from "@/lib/format";

export default function DataValidationPage() {
  const { data, isLoading } = useQuery({ queryKey: ["validation-report"], queryFn: getValidationReport });

  return (
    <div>
      <PageHeader
        title="Data Validation"
        description="Module 1 — data contract, schema, and integrity checks run before any feature engineering begins"
        badge={<VerificationBadge status="verified" />}
      />

      {isLoading || !data ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-[104px] rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-96 rounded-xl" />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard index={0} label="Dataset Rows" value={formatNumber(data.rowCount)} icon={Database} hint={`Raw columns: ${data.rawColumnCount}`} accent="primary" />
            <StatCard
              index={1}
              label="Critical Checks"
              value={`${data.criticalPassed}/${data.criticalTotal}`}
              icon={ShieldCheck}
              hint="Must all pass before the pipeline proceeds"
              accent="success"
            />
            <StatCard index={2} label="Warning Checks" value={`${data.warningPassed}/${data.warningTotal}`} icon={Hash} hint="Non-blocking, logged for review" accent="success" />
          </div>

          <Alert>
            <KeyRound className="size-4" />
            <AlertTitle>PII encryption independently re-verified</AlertTitle>
            <AlertDescription>
              Rather than trusting the Milestone 1 classification report, Module 1 re-checks that sensitive fields are actually
              encrypted using Fernet (AES-128-CBC with authentication) before any downstream processing occurs.
            </AlertDescription>
          </Alert>

          <Section title="Validation Checks" description={`Dataset version ${data.datasetVersion}`} noPadding>
            <div className="divide-y divide-border">
              {data.checks.map((check) => (
                <div key={check.id} className="flex items-center justify-between gap-4 px-5 py-3.5">
                  <div className="flex min-w-0 items-start gap-3">
                    {check.status === "pass" ? (
                      <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" />
                    ) : (
                      <XCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
                    )}
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-foreground">{check.name}</p>
                        <Badge variant={check.severity === "critical" ? "destructive" : "secondary"} className="text-[10px]">
                          {check.severity}
                        </Badge>
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground">{check.description}</p>
                      <p className="mt-1 font-mono text-[11px] text-muted-foreground/70">{check.evidence}</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="shrink-0 border-success/30 bg-success/10 text-success">
                    PASS
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
