export function fmt(n: number | null | undefined, prefix = "$", decimals = 2): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "" : "-";
  return `${sign}${prefix}${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
}

export function fmtPnl(n: number | null | undefined): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

export function msgTypeColor(type: string): string {
  const map: Record<string, string> = {
    OPPORTUNITY: "text-yellow-400",
    ANALYSIS: "text-blue-400",
    RISK_REVIEW: "text-orange-400",
    DEBATE_CHALLENGE: "text-purple-400",
    MASTER_DECISION: "text-green-400",
    EXECUTION_REPORT: "text-cyan-400",
    SELF_CORRECTION: "text-red-400",
    STATUS_UPDATE: "text-slate-400",
    HOURLY_REPORT: "text-slate-400",
    USER_PROMPT: "text-pink-400",
  };
  return map[type] || "text-slate-400";
}

export function agentColor(name: string): string {
  const map: Record<string, string> = {
    master: "bg-green-500",
    research: "bg-yellow-500",
    analysis: "bg-blue-500",
    risk: "bg-orange-500",
    debate: "bg-purple-500",
    execution: "bg-cyan-500",
    user: "bg-pink-500",
  };
  return map[name] || "bg-slate-500";
}
