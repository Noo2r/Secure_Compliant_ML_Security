import { useQuery } from "@tanstack/react-query";
import { Archive, Wrench, FileLock2, KeyRound } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { StatCard } from "@/components/shared/StatCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { getAuditEvents, getWormStatus, CANDIDATE_AUDIT_FILES } from "@/services/audit-service";
import { formatDateTime } from "@/lib/format";

export default function AuditStoragePage() {
  const { data: events, isLoading: loadingEvents } = useQuery({ queryKey: ["audit-events"], queryFn: getAuditEvents });
  const { data: worm, isLoading: loadingWorm } = useQuery({ queryKey: ["worm-status"], queryFn: getWormStatus });
  const isLoading = loadingEvents || loadingWorm;

  return (
    <div>
      <PageHeader
        title="Audit Storage"
        description="WORM (write-once-read-many) immutable audit trail for compliance evidence"
        badge={<VerificationBadge status="dry_run" />}
      />

      {isLoading || !events || !worm ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : (
        <div className="space-y-6">
          <Alert>
            <Wrench className="size-4" />
            <AlertTitle>Dry-run verified only — no live immutable storage exists</AlertTitle>
            <AlertDescription>
              worm_storage.py's file-discovery and hashing logic has been exercised with --dry-run, which lists real audit files
              without uploading. Six Azure Storage/identity secrets are required for a live upload and none are configured in
              this repository.
            </AlertDescription>
          </Alert>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard index={0} label="Storage Mode" value="Dry-Run" icon={FileLock2} hint="Never uploaded to Azure Blob" accent="warning" />
            <StatCard index={1} label="Candidate Files" value={String(worm.filesListed)} icon={Archive} hint="Discovered by --dry-run" accent="primary" />
            <StatCard index={2} label="Secrets Configured" value={`${worm.secretsConfigured}/${worm.secretsRequired}`} icon={KeyRound} hint="Azure Storage / identity credentials" accent="destructive" />
          </div>

          <Section title="Candidate Audit Files" description="Would be uploaded to immutable storage in a live run" noPadding>
            <div className="divide-y divide-border">
              {CANDIDATE_AUDIT_FILES.map((f) => (
                <div key={f.path} className="flex items-center justify-between px-5 py-3">
                  <span className="font-mono text-xs text-foreground">{f.path}</span>
                  <Badge variant="secondary" className="text-[10px]">
                    {f.category}
                  </Badge>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Event Timeline" description="Recent dry-run and pipeline events" noPadding>
            <div className="space-y-0 divide-y divide-border">
              {events.map((e) => (
                <div key={e.id} className="flex items-start gap-3 px-5 py-3.5">
                  <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-warning/10">
                    <Archive className="size-4 text-warning" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{e.action}</p>
                    <p className="text-xs text-muted-foreground">{e.actor}</p>
                    <p className="mt-1 font-mono text-[11px] text-muted-foreground/70">sha256: {e.sha256}</p>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">{formatDateTime(e.timestamp)}</span>
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}
