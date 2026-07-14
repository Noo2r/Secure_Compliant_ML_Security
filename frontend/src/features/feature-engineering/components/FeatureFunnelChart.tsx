import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, LabelList } from "recharts";
import type { FeatureStage } from "@/services/feature-engineering-service";

export function FeatureFunnelChart({ funnel }: { funnel: FeatureStage[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={funnel} layout="vertical" margin={{ top: 4, right: 40, left: 8, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={{ stroke: "var(--border)" }} />
        <YAxis
          dataKey="stage"
          type="category"
          width={170}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
          formatter={(value) => [Number(value).toLocaleString(), "Columns"]}
        />
        <Bar dataKey="count" fill="var(--primary)" radius={[0, 6, 6, 0]} maxBarSize={26}>
          <LabelList dataKey="count" position="right" style={{ fill: "var(--foreground)", fontSize: 11 }} formatter={(v) => Number(v).toLocaleString()} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
