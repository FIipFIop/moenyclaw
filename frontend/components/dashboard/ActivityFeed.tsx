"use client";
import { useWebSocket } from "@/components/providers/WebSocketProvider";
import { agentColor, msgTypeColor } from "@/lib/utils";

interface FeedMsg {
  id: string;
  from_agent: string;
  to_agent: string;
  message_type: string;
  payload: any;
  timestamp: string;
}

function FeedItem({ msg }: { msg: FeedMsg }) {
  const dot = agentColor(msg.from_agent);
  const typeColor = msgTypeColor(msg.message_type);

  const preview = (() => {
    try {
      const p = typeof msg.payload === "string" ? JSON.parse(msg.payload) : msg.payload;
      const opp = p?.opportunity;
      const thesis = p?.thesis;
      const result = p?.result;
      const decision = p?.decision;
      if (opp?.market) return `${opp.direction?.toUpperCase()} ${opp.market} (${opp.exchange}) — conf: ${opp.confidence}`;
      if (thesis?.market) return `${thesis.market}: conf ${thesis.confidence_score} | entry ${thesis.suggested_entry}`;
      if (decision?.action) return `Decision: ${decision.action.toUpperCase()} — ${decision.reason?.slice(0, 80)}`;
      if (result?.status) return `Status: ${result.status} — ${result.message || result.error || ""}`;
      return JSON.stringify(p).slice(0, 100);
    } catch {
      return String(msg.payload).slice(0, 100);
    }
  })();

  return (
    <div className="flex gap-2 py-1.5 border-b border-slate-800/60 text-xs">
      <div className={`mt-0.5 h-2 w-2 flex-shrink-0 rounded-full ${dot}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1 flex-wrap">
          <span className="font-semibold capitalize text-slate-300">{msg.from_agent}</span>
          <span className="text-slate-600">→</span>
          <span className="text-slate-500 capitalize">{msg.to_agent}</span>
          <span className={`font-mono text-[10px] ${typeColor}`}>[{msg.message_type}]</span>
        </div>
        <p className="text-slate-400 truncate">{preview}</p>
      </div>
      <span className="text-[10px] text-slate-600 flex-shrink-0">
        {new Date(msg.timestamp).toLocaleTimeString()}
      </span>
    </div>
  );
}

export function ActivityFeed() {
  const { events, isConnected } = useWebSocket();

  const msgs = events
    .filter((e) => e.event === "agent_message")
    .map((e) => e.data as FeedMsg)
    .slice(-100)
    .reverse();

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-sm font-semibold text-slate-200">Agent Activity</h2>
        <div className="flex items-center gap-1.5">
          <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-green-400" : "bg-red-500 animate-pulse"}`} />
          <span className="text-[10px] text-slate-500">{isConnected ? "live" : "reconnecting"}</span>
        </div>
      </div>

      <div className="overflow-y-auto max-h-80 scrollbar-thin flex flex-col">
        {msgs.length === 0 ? (
          <p className="text-xs text-slate-600 py-4 text-center">Waiting for agent activity…</p>
        ) : (
          msgs.map((m, i) => <FeedItem key={m.id || i} msg={m} />)
        )}
      </div>
    </div>
  );
}
