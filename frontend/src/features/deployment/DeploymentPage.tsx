import { useQuery } from "@tanstack/react-query";
import { Server, Box } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { getTerraformResources, getK8sResources } from "@/services/deployment-service";
import { ArchitectureDiagram } from "./components/ArchitectureDiagram";

export default function DeploymentPage() {
  const { data: tf, isLoading: loadingTf } = useQuery({ queryKey: ["terraform-resources"], queryFn: getTerraformResources });
  const { data: k8s, isLoading: loadingK8s } = useQuery({ queryKey: ["k8s-resources"], queryFn: getK8sResources });
  const isLoading = loadingTf || loadingK8s;

  return (
    <div>
      <PageHeader
        title="Deployment"
        description="Azure infrastructure-as-code target architecture and Kubernetes manifests"
        badge={<VerificationBadge status="designed_not_deployed" />}
      />

      {isLoading || !tf || !k8s ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : (
        <div className="space-y-6">
          <Alert>
            <Server className="size-4" />
            <AlertTitle>Designed target architecture — not applied to a live subscription</AlertTitle>
            <AlertDescription>
              No live AKS deployment, live WAF blocking, live Key Vault secret retrieval, or production availability is claimed.
              Every resource below validates successfully but has never been deployed.
            </AlertDescription>
          </Alert>

          <Section title="Target Architecture">
            <ArchitectureDiagram />
          </Section>

          <Section title="Terraform Resource Inventory" description="5 modules: network, aks, keyvault, monitoring, waf" noPadding>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Module</TableHead>
                    <TableHead>Resource</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Security note</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tf.map((r) => (
                    <TableRow key={r.logicalName}>
                      <TableCell>
                        <Badge variant="secondary" className="text-[10px]">
                          {r.module}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{r.logicalName}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{r.resourceType}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{r.securityNote}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Section>

          <Section title="Kubernetes Manifests" description="Dry-run validated with kubectl apply --dry-run=client" noPadding>
            <div className="divide-y divide-border">
              {k8s.map((r) => (
                <div key={r.name} className="flex items-center gap-3 px-5 py-3">
                  <Box className="size-4 shrink-0 text-primary" />
                  <div className="min-w-0">
                    <span className="font-mono text-xs font-medium text-foreground">{r.kind}</span>
                    <span className="ml-2 font-mono text-xs text-muted-foreground">{r.name}</span>
                    <p className="text-xs text-muted-foreground">{r.purpose}</p>
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
