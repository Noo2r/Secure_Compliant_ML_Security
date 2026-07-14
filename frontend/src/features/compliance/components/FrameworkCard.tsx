import { cn } from "@/lib/utils";

interface FrameworkCardProps {
  title: string;
  implemented: number;
  partial: number;
  notImplemented: number;
  note?: string;
}

export function FrameworkCard({ title, implemented, partial, notImplemented, note }: FrameworkCardProps) {
  const total = implemented + partial + notImplemented;
  const pct = Math.round((implemented / total) * 100);

  return (
    <div className="rounded-xl border border-border p-5">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-semibold text-foreground">{title}</p>
        <span className="text-lg font-semibold text-primary">{pct}%</span>
      </div>
      <div className="mb-3 flex h-2 overflow-hidden rounded-full bg-muted">
        <div className="bg-success" style={{ width: `${(implemented / total) * 100}%` }} />
        <div className="bg-warning" style={{ width: `${(partial / total) * 100}%` }} />
        <div className="bg-destructive/60" style={{ width: `${(notImplemented / total) * 100}%` }} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <Legend color="bg-success" label="Implemented" value={implemented} />
        <Legend color="bg-warning" label="Partial" value={partial} />
        <Legend color="bg-destructive/60" label="Not implemented" value={notImplemented} />
      </div>
      {note && <p className="mt-3 text-xs text-muted-foreground">{note}</p>}
    </div>
  );
}

function Legend({ color, label, value }: { color: string; label: string; value: number }) {
  return (
    <div>
      <div className="flex items-center justify-center gap-1">
        <span className={cn("size-1.5 rounded-full", color)} />
        <span className="font-medium text-foreground">{value}</span>
      </div>
      <span className="text-muted-foreground">{label}</span>
    </div>
  );
}
