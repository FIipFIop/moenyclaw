"use client";
import { api } from "@/lib/api";
import { fmtPnl } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export function StatusBar() {
  const qc = useQueryClient();

  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: api.portfolioCurrent,
    refetchInterval: 30_000,
  });

  const { data: sys } = useQuery({
    queryKey: ["system"],
    queryFn: api.systemConfig,
    refetchInterval: 15_000,
  });

  const toggle = useMutation({
    mutationFn: api.toggleTrading,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["system"] }),
  });

  const tradingEnabled = sys?.trading_enabled ?? false;
  const pnl = portfolio?.unrealized_pnl ?? 0;
  const total = portfolio?.total_usd ?? 0;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-700/50 backdrop-blur sticky top-0 z-10">
      <div className="flex items-center gap-2">
        <span className="text-lg font-bold text-cyan-400">🐾 MoneyClaw</span>
        <span className="text-slate-600 text-xs">Agent Network</span>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div className="text-center">
          <p className="text-slate-500 text-[10px] uppercase tracking-wide">Total</p>
          <p className="font-semibold">${total.toLocaleString("en-US", { minimumFractionDigits: 2 })}</p>
        </div>
        <div className="text-center">
          <p className="text-slate-500 text-[10px] uppercase tracking-wide">Unrealized</p>
          <p className={`font-semibold ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{fmtPnl(pnl)}</p>
        </div>
        <button
          onClick={() => toggle.mutate()}
          disabled={toggle.isPending}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            tradingEnabled
              ? "bg-green-500/20 text-green-400 border border-green-500/40 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/40"
              : "bg-slate-700 text-slate-400 border border-slate-600 hover:bg-green-500/20 hover:text-green-400 hover:border-green-500/40"
          }`}
        >
          {tradingEnabled ? "🟢 LIVE" : "🔴 Paper"}
        </button>
      </div>
    </div>
  );
}
