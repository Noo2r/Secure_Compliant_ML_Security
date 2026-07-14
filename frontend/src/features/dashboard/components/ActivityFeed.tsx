import { HealthBadge } from "@/components/shared/StatusBadge";
import { formatRelativeTime } from "@/lib/format";
import type { ActivityItem } from "@/types/domain";

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <div className="divide-y divide-border">
      {items.map((item) => (
        <div key={item.id} className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0">
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground">{item.title}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{item.description}</p>
            <div className="mt-1.5 flex items-center gap-2 text-[11px] text-muted-foreground">
              <span className="rounded bg-muted px-1.5 py-0.5 font-medium">{item.module}</span>
              <span>{formatRelativeTime(item.timestamp)}</span>
            </div>
          </div>
          <HealthBadge status={item.status} className="shrink-0" />
        </div>
      ))}
    </div>
  );
}
