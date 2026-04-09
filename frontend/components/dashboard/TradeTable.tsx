"use client";
import { api, Trade } from "@/lib/api";
import { fmtPnl } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";

const statusColors: Record<string, string> = {
  open: "text-green-400",
  closed: "text-slate-400",
  failed: "text-red-400",
  rejected: "text-orange-400",
  dry_run: "text-blue-400",
  pending: "text-yellow-400",
};

export function TradeTable({ limit = 10 }: { limit?: number }) {
  const { data: trades = [], isLoading } = useQuery({
    queryKey: ["trades"],
    queryFn: () => api.trades(`limit=${limit}`),
    refetchInterval: 30_000,
  });

  if (isLoading) return <p className="text-slate-600 text-sm p-4">Loading trades…</p>;
  if (trades.length === 0) return <p className="text-slate-600 text-sm p-4">No trades yet.</p>;

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/50">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-700/50 text-slate-500 text-left">
            <th className="px-3 py-2">Market</th>
            <th className="px-3 py-2">Exchange</th>
            <th className="px-3 py-2">Dir</th>
            <th className="px-3 py-2">Entry</th>
            <th className="px-3 py-2">Exit</th>
            <th className="px-3 py-2">PnL</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Date</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t: Trade) => (
            <tr key={t.id} className="border-b border-slate-800/60 hover:bg-slate-800/40">
              <td className="px-3 py-2 font-medium max-w-[200px] truncate" title={t.market}>{t.market}</td>
              <td className="px-3 py-2 capitalize">{t.exchange}</td>
              <td className="px-3 py-2">{t.direction || "—"}</td>
              <td className="px-3 py-2">{t.entry_price ? `$${t.entry_price}` : "—"}</td>
              <td className="px-3 py-2">{t.exit_price ? `$${t.exit_price}` : "—"}</td>
              <td className={`px-3 py-2 font-semibold ${(t.pnl ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                {t.pnl != null ? fmtPnl(t.pnl) : "—"}
              </td>
              <td className={`px-3 py-2 capitalize ${statusColors[t.status] || "text-slate-400"}`}>{t.status}</td>
              <td className="px-3 py-2 text-slate-500">
                {new Date(t.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
