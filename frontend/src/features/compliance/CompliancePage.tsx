import { useQuery } from "@tanstack/react-query";
import { FileCheck2, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getComplianceControls, getComplianceSummary, INCONSISTENCIES } from "@/services/compliance-service";
import { FrameworkCard } from "./components/FrameworkCard";

const STATUS_LABEL = {
  implemented: { label: "Implemented", className: "border-success/30 bg-success/10 text-success" },
  partial: { label: "Partial", className: "border-warning/30 bg-warning/10 text-warning" },
  not_implemented: { label: "Not Implemented", className: "border-destructive/30 bg-destructive/10 text-destructive" },
};

const PRIORITY_CLASS = {
  High: "border-destructive/30 bg-destructive/10 text-destructive",
  Medium: "border-warning/30 bg-warning/10 text-warning",
  Low: "border-muted-foreground/20 bg-muted text-muted-foreground",
};

export default function CompliancePage() {
  const { data: controls, isLoading: loadingControls } = useQuery({ queryKey: ["compliance-controls"], queryFn: getComplianceControls });
  const { data: summary, isLoading: loadingSummary } = useQuery({ queryKey: ["compliance-summary"], queryFn: getComplianceSummary });

  const isLoading = loadingControls || loadingSummary;

  return (
    <div>
      <PageHeader title="Compliance" description="GDPR / HIPAA / ISO 27001 control mapping — no formal legal certification is claimed" />

      {isLoading || !controls || !summary ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : (
        <div className="space-y-6">
          <Alert>
            <FileCheck2 className="size-4" />
            <AlertTitle>Assessment results, not formal certification</AlertTitle>
            <AlertDescription>
              This mapping is an internal analytical exercise conducted for the project's technical report. No third-party audit
              or formal certification (GDPR, HIPAA, ISO 27001) has been obtained.
            </AlertDescription>
          </Alert>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FrameworkCard title="GDPR" {...summary.gdpr} />
            <FrameworkCard title="HIPAA" {...summary.hipaa} />
            <FrameworkCard title="ISO 27001" {...summary.iso27001} />
          </div>

          <Section title="Documentation Inconsistencies" description="Identified while reconciling Milestone 4 compliance materials with directly-verified repository evidence" noPadding>
            <div className="divide-y divide-border">
              {INCONSISTENCIES.map((inc) => (
                <div key={inc.id} className="flex items-start gap-3 px-5 py-3.5">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{inc.claim}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      <span className="font-medium text-foreground/80">Verified state: </span>
                      {inc.actualState}
                    </p>
                  </div>
                  <Badge variant="outline" className={PRIORITY_CLASS[inc.remediationPriority]}>
                    {inc.remediationPriority} priority
                  </Badge>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Control Mapping" noPadding>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Framework</TableHead>
                    <TableHead>Control</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Evidence</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {controls.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="font-mono text-xs">{c.framework}</TableCell>
                      <TableCell className="text-sm">{c.control}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={STATUS_LABEL[c.status].className}>
                          {STATUS_LABEL[c.status].label}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-md text-xs text-muted-foreground">{c.gap ?? c.evidence}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}
