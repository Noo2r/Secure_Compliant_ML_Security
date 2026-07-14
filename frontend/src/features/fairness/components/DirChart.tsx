import { Bar, BarChart, CartesianGrid, ErrorBar, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from "recharts";
import type { FAIRNESS_METRICS } from "@/data/real-facts";

export function DirChart({ metrics }: { metrics: typeof FAIRNESS_METRICS }) {
  const data = metrics.map((m) => ({
    label: `${m.attribute}: ${m.group}`,
    dir: m.dir,
    errorLow: m.dir - m.dirCi[0],
    errorHigh: m.dirCi[1] - m.dir,
    significant: m.dirSignificant,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={{ stroke: "var(--border)" }} angle={-25} textAnchor="end" interval={0} height={60} />
        <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} />
        <ReferenceLine y={1} stroke="var(--muted-foreground)" strokeDasharray="4 4" label={{ value: "No disparity (DIR=1)", fontSize: 10, fill: "var(--muted-foreground)", position: "insideTopRight" }} />
        <Tooltip
          contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
          formatter={(value) => Number(value).toFixed(3)}
        />
        <Bar dataKey="dir" radius={[6, 6, 0, 0]} maxBarSize={40}>
          <ErrorBar dataKey="errorHigh" width={4} strokeWidth={1.5} stroke="var(--muted-foreground)" direction="y" />
          {data.map((entry) => (
            <Cell key={entry.label} fill={entry.significant ? "var(--warning)" : "var(--muted-foreground)"} fillOpacity={entry.significant ? 1 : 0.4} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
