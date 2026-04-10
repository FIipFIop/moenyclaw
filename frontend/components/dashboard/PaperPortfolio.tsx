"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { fmtPnl, fmt } from "@/lib/utils";

interface PaperBalance {
  cash: number;
  starting_balance: number;
  positions_value: number;
  total_value: number;
  pnl: number;
}

interface PaperPosition {
  market_slug: string;
  market_question: string;
  outcome: string;
  shares: number;
  avg_entry_price: number;
  total_cost: number;
  live_price: number;
  current_value: number;
  unrealized_pnl: number;
  percent_pnl: number;
}

interface PaperTrade {
  id: number;
  market_slug: string;
  market_question: string;
  outcome: string;
  side: string;
  avg_price: number;
  amount_usd: number;
  shares: number;
  slippage_bps: number;
  levels_filled: number;
  created_at: string;
}

export function PaperPortfolio() {
  const { data: balance } = useQuery<PaperBalance>({
    queryKey: ["paper-balance"],
    queryFn: () => apiFetch("/api/paper/balance"),
    refetchInterval: 30_000,
  });

  const { data: portfolio = [] } = useQuery<PaperPosition[]>({
    queryKey: ["paper-portfolio"],
    queryFn: () => apiFetch("/api/paper/portfolio"),
    refetchInterval: 30_000,
  });

  const { data: history = [] } = useQuery<PaperTrade[]>({
    queryKey: ["paper-history"],
    queryFn: () => apiFetch("/api/paper/history?limit=20"),
    refetchInterval: 30_000,
  });

  const roi = balance
    ? ((balance.total_value - balance.starting_balance) / balance.starting_balance) * 100
    : 0;

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-4 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">
          📄 Paper Portfolio
          <span className="ml-2 text-[10px] font-normal text-slate-500">Polymarket · Real order books</span>
        </h2>
        <span className={`text-sm font-bold ${roi >= 0 ? "text-green-400" : "text-red-400"}`}>
          {roi >= 0 ? "+" : ""}{roi.toFixed(2)}% ROI
        </span>
      </div>

      {/* Balance summary */}
      {balance && (
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: "Cash", value: fmt(balance.cash) },
            { label: "Positions", value: fmt(balance.positions_value) },
            { label: "Total", value: fmt(balance.total_value) },
            { label: "P&L", value: fmtPnl(balance.pnl), pnl: balance.pnl },
          ].map(({ label, value, pnl }) => (
            <div key={label} className="bg-slate-900/50 rounded-lg p-2 text-center">
              <p className="text-[10px] text-slate-500 uppercase tracking-wide">{label}</p>
              <p className={`text-sm font-semibold ${pnl !== undefined ? (pnl >= 0 ? "text-green-400" : "text-red-400") : "text-slate-200"}`}>
                {value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Open positions */}
      {portfolio.length > 0 && (
        <div>
          <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-2">Open Positions</p>
          <div className="flex flex-col gap-1">
            {portfolio.map((pos) => (
              <div key={pos.market_slug + pos.outcome} className="flex items-center gap-2 text-xs bg-slate-900/40 rounded-lg px-3 py-2">
                <span className={`flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold ${pos.outcome === "yes" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                  {pos.outcome.toUpperCase()}
                </span>
                <span className="flex-1 truncate text-slate-300" title={pos.market_question}>
                  {pos.market_question}
                </span>
                <span className="text-slate-500 flex-shrink-0">{pos.shares.toFixed(1)} shares</span>
                <span className="text-slate-500 flex-shrink-0">@ {pos.live_price.toFixed(3)}</span>
                <span className={`flex-shrink-0 font-semibold ${pos.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {fmtPnl(pos.unrealized_pnl)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent trades */}
      {history.length > 0 && (
        <div>
          <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-2">Recent Trades</p>
          <div className="overflow-y-auto max-h-48 scrollbar-thin flex flex-col gap-1">
            {history.map((t) => (
              <div key={t.id} className="flex items-center gap-2 text-xs border-b border-slate-800/60 py-1.5">
                <span className={`flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold ${t.side === "buy" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                  {t.side.toUpperCase()}
                </span>
                <span className={`flex-shrink-0 text-[10px] px-1 rounded ${t.outcome === "yes" ? "text-green-300" : "text-red-300"}`}>
                  {t.outcome.toUpperCase()}
                </span>
                <span className="flex-1 truncate text-slate-400" title={t.market_question}>
                  {t.market_question}
                </span>
                <span className="text-slate-500 flex-shrink-0">{fmt(t.amount_usd, "$", 0)}</span>
                <span className="text-slate-600 flex-shrink-0">@ {t.avg_price.toFixed(3)}</span>
                <span className="text-[10px] text-slate-600 flex-shrink-0">{t.slippage_bps.toFixed(0)}bps slip</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {portfolio.length === 0 && history.length === 0 && (
        <p className="text-xs text-slate-600 text-center py-2">No paper trades yet — agents will trade automatically</p>
      )}
    </div>
  );
}
