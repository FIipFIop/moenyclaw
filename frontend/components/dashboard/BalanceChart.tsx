"use client";
import { api, PortfolioPoint } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function BalanceChart() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["portfolio-history"],
    queryFn: () => api.portfolioHistory(7),
    refetchInterval: 60_000,
  });

  const chartData = data.map((p: PortfolioPoint) => ({
    time: new Date(p.snapshot_at).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit" }),
    value: parseFloat(p.total_usd.toFixed(2)),
    pnl: parseFloat(p.unrealized_pnl.toFixed(2)),
  }));

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-4 h-48 flex items-center justify-center">
        <p className="text-slate-600 text-sm">Loading chart…</p>
      </div>
    );
  }

  if (chartData.length < 2) {
    return (
      <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-4 h-48 flex items-center justify-center">
        <p className="text-slate-600 text-sm">Not enough data yet (need 2+ snapshots)</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-4">
      <h2 className="text-sm font-semibold text-slate-200 mb-3">Portfolio Value (7d)</h2>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={chartData}>
          <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#94a3b8" }}
            formatter={(v: number) => [`$${v.toFixed(2)}`, "Portfolio"]}
          />
          <Line type="monotone" dataKey="value" stroke="#22d3ee" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
