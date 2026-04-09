"use client";
import { TradeTable } from "@/components/dashboard/TradeTable";

export default function TradesPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-slate-200">All Trades</h1>
      <TradeTable limit={100} />
    </div>
  );
}
