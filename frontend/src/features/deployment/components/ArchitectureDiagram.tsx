import { Globe, ShieldAlert, Boxes, KeyRound, Server, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

function Node({ icon: Icon, label, sub, tone = "target" }: { icon: typeof Globe; label: string; sub: string; tone?: "target" | "public" }) {
  return (
    <div
      className={cn(
        "flex min-w-[150px] flex-col items-center gap-1 rounded-lg border px-3 py-2.5 text-center",
        tone === "target" ? "border-warning/30 bg-warning/10" : "border-border bg-muted/40",
      )}
    >
      <Icon className={cn("size-4", tone === "target" ? "text-warning" : "text-muted-foreground")} />
      <span className="text-xs font-medium text-foreground">{label}</span>
      <span className="text-[10px] text-muted-foreground">{sub}</span>
    </div>
  );
}

export function ArchitectureDiagram() {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Node icon={Globe} label="Internet" sub="public zone" tone="public" />
        <Arrow />
        <Node icon={ShieldAlert} label="Application Gateway WAF_v2" sub="OWASP CRS 3.2 · target" />
        <Arrow />
        <Node icon={Boxes} label="AKS private cluster" sub="RBAC + Workload Identity · target" />
        <Arrow />
        <Node icon={Server} label="fraud-inference-api pods" sub="3 replicas · target" />
      </div>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Node icon={KeyRound} label="Key Vault" sub="public access disabled · target" />
        <Node icon={FileText} label="Log Analytics" sub="audit + diagnostics · target" />
      </div>
      <p className="text-center text-xs text-muted-foreground">
        Every component above is defined in Terraform and passes <code className="rounded bg-muted px-1 py-0.5">terraform validate</code>,
        but none has been applied to a live Azure subscription.
      </p>
    </div>
  );
}

function Arrow() {
  return <div className="h-px w-6 bg-border sm:w-10" />;
}
