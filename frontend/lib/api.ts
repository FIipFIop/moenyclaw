const API = process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  agents: () => apiFetch<Agent[]>("/api/agents"),
  agentMessages: (name: string) => apiFetch<AgentMsg[]>(`/api/agents/${name}/messages`),
  trades: (params?: string) => apiFetch<Trade[]>(`/api/trades${params ? "?" + params : ""}`),
  portfolioCurrent: () => apiFetch<Portfolio>("/api/portfolio/current"),
  portfolioHistory: (days = 7) => apiFetch<PortfolioPoint[]>(`/api/portfolio/history?days=${days}`),
  systemConfig: () => apiFetch<{ trading_enabled: boolean }>("/api/system/config"),
  toggleTrading: () => apiFetch<{ trading_enabled: boolean }>("/api/system/toggle-trading", { method: "POST" }),
  validateToken: (token: string) => apiFetch<{ valid: boolean; expires_at: string }>(`/api/tokens/${token}/validate`),
};

export interface Agent {
  name: string;
  model: string;
  status: "idle" | "thinking" | "waiting" | "error";
  last_message: string | null;
  last_active: string | null;
}

export interface AgentMsg {
  id: string;
  round_id: string;
  from_agent: string;
  to_agent: string;
  message_type: string;
  content: string;
  created_at: string;
}

export interface Trade {
  id: number;
  round_id: string;
  exchange: string;
  market: string;
  direction: string | null;
  size: number | null;
  entry_price: number | null;
  exit_price: number | null;
  pnl: number | null;
  status: string;
  rejection_reason: string | null;
  created_at: string;
}

export interface Portfolio {
  total_usd: number;
  hyperliquid_balance: number;
  polymarket_balance: number;
  unrealized_pnl: number;
  realized_pnl_today: number;
  snapshot_at: string | null;
}

export interface PortfolioPoint {
  total_usd: number;
  unrealized_pnl: number;
  realized_pnl_today: number;
  snapshot_at: string;
}
