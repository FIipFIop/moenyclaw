"use client";
import { api } from "@/lib/api";
import { fmtPnl } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useWebSocket } from "@/components/providers/WebSocketProvider";
import { useEffect } from "react";

export function StatusBar() {
  const qc = useQueryClient();
  const { lastEvent } = useWebSocket();

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

  // Sync config changes pushed via WebSocket
  useEffect(() => {
    if (lastEvent?.event === "config_changed") {
      qc.invalidateQueries({ queryKey: ["system"] });
    }
  }, [lastEvent]);

  const toggle = useMutation({
    mutationFn: api.toggleTrading,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["system"] }),
  });

  const togglePoly = useMutation({
    mutationFn: api.togglePolymarket,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["system"] }),
  });

  const toggleHl = useMutation({
    mutationFn: api.toggleHyperliquid,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["system"] }),
  });

  const tradingEnabled = sys?.trading_enabled ?? false;
  const polyEnabled = sys?.polymarket_enabled ?? true;
  const hlEnabled = sys?.hyperliquid_enabled ?? true;
  const pnl = portfolio?.unrealized_pnl ?? 0;
  const total = portfolio?.total_usd ?? 0;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-700/50 backdrop-blur sticky top-0 z-10">
      <div className="flex items-center gap-2">
        <span className="text-lg font-bold text-cyan-400">🐾 MoneyClaw</span>
        <span className="text-slate-600 text-xs">Agent Network</span>
      </div>

      <div className="flex items-center gap-4 text-sm">
        <div className="text-center">
          <p className="text-slate-500 text-[10px] uppercase tracking-wide">Total</p>
          <p className="font-semibold">${total.toLocaleString("en-US", { minimumFractionDigits: 2 })}</p>
        </div>
        <div className="text-center">
          <p className="text-slate-500 text-[10px] uppercase tracking-wide">Unrealized</p>
          <p className={`font-semibold ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{fmtPnl(pnl)}</p>
        </div>

        {/* Per-exchange toggles — only relevant when live trading is on */}
        <div className="flex items-center gap-1.5 border-l border-slate-700 pl-4">
          <span className="text-[10px] text-slate-500 mr-1">Exchanges</span>
          <button
            onClick={() => togglePoly.mutate()}
            disabled={togglePoly.isPending}
            title={polyEnabled ? "Polymarket LIVE — click to paper" : "Polymarket PAPER — click to enable live"}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-colors ${
              polyEnabled
                ? "bg-blue-500/20 text-blue-400 border border-blue-500/40 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30"
                : "bg-slate-800 text-slate-500 border border-slate-700 hover:border-blue-500/40 hover:text-blue-400"
            }`}
          >
            {polyEnabled ? "POLY ✓" : "POLY ✗"}
          </button>
          <button
            onClick={() => toggleHl.mutate()}
            disabled={toggleHl.isPending}
            title={hlEnabled ? "Hyperliquid LIVE — click to paper" : "Hyperliquid PAPER — click to enable live"}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-colors ${
              hlEnabled
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30"
                : "bg-slate-800 text-slate-500 border border-slate-700 hover:border-cyan-500/40 hover:text-cyan-400"
            }`}
          >
            {hlEnabled ? "HL ✓" : "HL ✗"}
          </button>
        </div>

        {/* Global live/paper master toggle */}
        <button
          onClick={() => toggle.mutate()}
          disabled={toggle.isPending}
          title={tradingEnabled ? "LIVE mode — click to switch to paper" : "Paper mode — click to go live"}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            tradingEnabled
              ? "bg-green-500/20 text-green-400 border border-green-500/40 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/40"
              : "bg-slate-700 text-slate-400 border border-slate-600 hover:bg-green-500/20 hover:text-green-400 hover:border-green-500/40"
          }`}
        >
          {tradingEnabled ? "🟢 LIVE" : "📄 Paper"}
        </button>
      </div>
    </div>
  );
}
