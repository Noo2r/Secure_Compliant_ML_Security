import { ArrowRight } from "lucide-react";

export function PipelineFlow({ steps }: { steps: string[] }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {steps.map((step, i) => (
        <div key={step} className="flex items-center gap-2">
          <div className="rounded-lg border border-border bg-muted/40 px-3.5 py-2 text-sm font-medium text-foreground">{step}</div>
          {i < steps.length - 1 && <ArrowRight className="size-4 shrink-0 text-muted-foreground" />}
        </div>
      ))}
    </div>
  );
}
