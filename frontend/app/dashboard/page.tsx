"use client";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { AgentCard } from "@/components/dashboard/AgentCard";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { BalanceChart } from "@/components/dashboard/BalanceChart";
import { TradeTable } from "@/components/dashboard/TradeTable";
import { PaperPortfolio } from "@/components/dashboard/PaperPortfolio";

export default function DashboardPage() {
  const { data: agents = [], isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: api.agents,
    refetchInterval: 5_000,
  });

  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: api.portfolioCurrent,
    refetchInterval: 30_000,
  });

  return (
    <div className="space-y-6">
      {/* Portfolio summary row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Total Portfolio", value: `$${(portfolio?.total_usd ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}` },
          { label: "Hyperliquid", value: `$${(portfolio?.hyperliquid_balance ?? 0).toFixed(2)}` },
          { label: "Polymarket", value: `$${(portfolio?.polymarket_balance ?? 0).toFixed(2)}` },
          { label: "Unrealized PnL", value: `${(portfolio?.unrealized_pnl ?? 0) >= 0 ? "+" : ""}$${(portfolio?.unrealized_pnl ?? 0).toFixed(2)}`, positive: (portfolio?.unrealized_pnl ?? 0) >= 0 },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-4">
            <p className="text-[10px] text-slate-500 uppercase tracking-wide">{s.label}</p>
            <p className={`text-xl font-bold mt-1 ${"positive" in s ? (s.positive ? "text-green-400" : "text-red-400") : "text-slate-100"}`}>
              {s.value}
            </p>
          </div>
        ))}
      </div>

      {/* Agent cards */}
      <div>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">Agents</h2>
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-4 h-28 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {agents.map((a) => <AgentCard key={a.name} agent={a} />)}
          </div>
        )}
      </div>

      {/* Chart + Feed */}
      <div className="grid md:grid-cols-2 gap-4">
        <BalanceChart />
        <ActivityFeed />
      </div>

      {/* Paper portfolio */}
      <PaperPortfolio />

      {/* Recent trades */}
      <div>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">Recent Trades</h2>
        <TradeTable limit={10} />
      </div>
    </div>
  );
}
