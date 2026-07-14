import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface MetricRowProps {
  label: string;
  value: ReactNode;
  hint?: string;
  className?: string;
}

export function MetricRow({ label, value, hint, className }: MetricRowProps) {
  return (
    <div className={cn("flex items-center justify-between gap-4 py-2.5", className)}>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        {hint && <p className="text-xs text-muted-foreground/70">{hint}</p>}
      </div>
      <span className="font-mono text-sm font-medium text-foreground">{value}</span>
    </div>
  );
}

export function MetricGrid({ children, cols = 2 }: { children: ReactNode; cols?: 2 | 3 | 4 }) {
  const colsClass = cols === 2 ? "sm:grid-cols-2" : cols === 3 ? "sm:grid-cols-3" : "sm:grid-cols-4";
  return <div className={cn("grid grid-cols-1 gap-4", colsClass)}>{children}</div>;
}
