import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import type { DIFFERENTIAL_PRIVACY } from "@/data/real-facts";

export function DpComparisonChart({ metrics }: { metrics: typeof DIFFERENTIAL_PRIVACY.metrics }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={metrics} margin={{ top: 4, right: 12, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="metric" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={{ stroke: "var(--border)" }} />
        <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} domain={[0, 1]} />
        <Tooltip
          contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
          formatter={(value) => Number(value).toFixed(4)}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="normal" name="Without DP" fill="var(--success)" radius={[4, 4, 0, 0]} maxBarSize={28} />
        <Bar dataKey="dp" name="With DP-SGD" fill="var(--destructive)" radius={[4, 4, 0, 0]} maxBarSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}
