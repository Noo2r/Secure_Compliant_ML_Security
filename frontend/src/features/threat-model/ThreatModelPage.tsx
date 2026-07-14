import { useQuery } from "@tanstack/react-query";
import { Swords, ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getThreats, TRUST_BOUNDARIES } from "@/services/threat-model-service";
import { ThreatCard } from "./components/ThreatCard";
import type { ThreatRow } from "@/types/domain";

const CATEGORIES: ThreatRow["category"][] = [
  "Spoofing",
  "Tampering",
  "Repudiation",
  "Information Disclosure",
  "Denial of Service",
  "Elevation of Privilege",
];

export default function ThreatModelPage() {
  const { data, isLoading } = useQuery({ queryKey: ["threats"], queryFn: getThreats });

  return (
    <div>
      <PageHeader title="Threat Model" description="STRIDE analysis of assets, attack vectors, existing controls, and residual risk" />

      {isLoading || !data ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : (
        <div className="space-y-6">
          <Alert>
            <ShieldAlert className="size-4" />
            <AlertTitle>Analytical exercise, not a certified red-team assessment</AlertTitle>
            <AlertDescription>
              This threat model was conducted for the project's technical report. Controls marked "Designed, Not Deployed" have
              never been applied to a live Azure subscription.
            </AlertDescription>
          </Alert>

          <Section title="STRIDE Threats" noPadding>
            <Tabs defaultValue="Spoofing" className="w-full">
              <div className="border-b border-border px-5 pt-4">
                <TabsList className="flex-wrap">
                  {CATEGORIES.map((c) => (
                    <TabsTrigger key={c} value={c} className="text-xs">
                      {c}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </div>
              {CATEGORIES.map((c) => (
                <TabsContent key={c} value={c} className="p-5">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {data.filter((t) => t.category === c).map((t) => (
                      <ThreatCard key={t.id} threat={t} />
                    ))}
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </Section>

          <Section title="Trust Boundaries" description="Where privilege or network trust level changes across the target architecture" noPadding>
            <div className="divide-y divide-border">
              {TRUST_BOUNDARIES.map((b) => (
                <div key={b.name} className="flex items-start gap-3 px-5 py-3.5">
                  <Swords className="mt-0.5 size-4 shrink-0 text-primary" />
                  <div>
                    <p className="text-sm font-medium text-foreground">{b.name}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{b.description}</p>
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
