import { Construction } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";

export function ComingSoonPage({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <PageHeader title={title} description={description} />
      <EmptyState icon={Construction} title="Module scaffold in progress" description="This page is being built next in the incremental rollout." />
    </div>
  );
}
