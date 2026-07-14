import { useQuery } from "@tanstack/react-query";
import { GitBranch, TestTube2 } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { StatCard } from "@/components/shared/StatCard";
import { Skeleton } from "@/components/ui/skeleton";
import { getCiRuns } from "@/services/cicd-service";
import { TEST_SUITE } from "@/data/real-facts";
import { PipelineRunCard } from "./components/PipelineRunCard";

export default function CicdPage() {
  const { data, isLoading } = useQuery({ queryKey: ["ci-runs"], queryFn: getCiRuns });

  return (
    <div>
      <PageHeader title="CI/CD" description="GitHub Actions pipeline — .github/workflows/mlops-pipeline.yml" />

      {isLoading || !data ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard index={0} label="Latest Run" value={`#${data[0].id}`} icon={GitBranch} hint={data[0].status} accent={data[0].status === "success" ? "success" : "destructive"} />
            <StatCard index={1} label="Test Suite" value={`${TEST_SUITE.totalTests}/${TEST_SUITE.totalTests}`} icon={TestTube2} hint={`${TEST_SUITE.totalFiles} files`} accent="success" />
            <StatCard index={2} label="Success Rate (last 3)" value={`${Math.round((data.filter((r) => r.status === "success").length / data.length) * 100)}%`} icon={GitBranch} accent="primary" />
          </div>

          <Section title="Pipeline Runs" description="drift-monitor → alert-on-drift → worm-upload, with real fallback branches for a fresh checkout">
            <div className="space-y-4">
              {data.map((run, i) => (
                <PipelineRunCard key={run.id} run={run} defaultExpanded={i === 0} />
              ))}
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}
