export function JsonBlock({ data, className }: { data: unknown; className?: string }) {
  return (
    <pre className={`overflow-x-auto rounded-lg border border-border bg-muted/40 p-3.5 font-mono text-xs leading-relaxed text-foreground ${className ?? ""}`}>
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
