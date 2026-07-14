import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SectionProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  noPadding?: boolean;
}

export function Section({ title, description, actions, children, className, noPadding }: SectionProps) {
  return (
    <Card className={cn("gap-0 overflow-hidden py-0", className)}>
      {(title || actions) && (
        <div className="flex items-center justify-between gap-4 border-b border-border px-5 py-4">
          <div>
            {title && <h3 className="text-sm font-semibold text-foreground">{title}</h3>}
            {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
          </div>
          {actions}
        </div>
      )}
      <div className={cn(!noPadding && "p-5")}>{children}</div>
    </Card>
  );
}
