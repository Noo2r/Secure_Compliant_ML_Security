import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface CurveChartProps {
  data: Array<Record<string, number>>;
  xKey: string;
  yKey: string;
  xLabel: string;
  yLabel: string;
}

export function CurveChart({ data, xKey, yKey, xLabel, yLabel }: CurveChartProps) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <defs>
          <linearGradient id={`curve-${yKey}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey={xKey}
          type="number"
          domain={[0, 1]}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
          label={{ value: xLabel, position: "insideBottom", offset: -2, fontSize: 11, fill: "var(--muted-foreground)" }}
        />
        <YAxis
          domain={[0, 1]}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={false}
          label={{ value: yLabel, angle: -90, position: "insideLeft", fontSize: 11, fill: "var(--muted-foreground)" }}
        />
        <Tooltip
          contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
          formatter={(value) => Number(value).toFixed(3)}
        />
        <Area type="monotone" dataKey={yKey} stroke="var(--primary)" strokeWidth={2} fill={`url(#curve-${yKey})`} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
