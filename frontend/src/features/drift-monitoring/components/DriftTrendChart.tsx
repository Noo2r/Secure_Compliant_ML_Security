import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DriftReport } from "@/services/drift-service";

export function DriftTrendChart({ trend }: { trend: DriftReport["trend"] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={trend} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="run" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={{ stroke: "var(--border)" }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="driftedCount"
          name="Drifted features"
          stroke="var(--warning)"
          strokeWidth={2}
          dot={{ r: 3.5, fill: "var(--warning)", strokeWidth: 0 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
