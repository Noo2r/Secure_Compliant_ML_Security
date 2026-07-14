import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from "recharts";
import { MODEL_LEADERBOARD } from "@/data/real-facts";

const data = MODEL_LEADERBOARD.map((m) => ({ name: m.name, prAuc: m.holdoutPrAuc, isWinner: m.isWinner }));

export function LeaderboardMiniChart() {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={{ stroke: "var(--border)" }} interval={0} angle={-12} textAnchor="end" height={40} />
        <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} domain={[0, 0.6]} />
        <Tooltip
          contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
          formatter={(value) => [Number(value).toFixed(4), "Holdout PR-AUC"]}
        />
        <Bar dataKey="prAuc" radius={[6, 6, 0, 0]} maxBarSize={40}>
          {data.map((entry) => (
            <Cell key={entry.name} fill={entry.isWinner ? "var(--primary)" : "var(--muted-foreground)"} fillOpacity={entry.isWinner ? 1 : 0.35} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
