"use client";
import { Agent } from "@/lib/api";
import { agentColor, timeAgo } from "@/lib/utils";

const statusDot: Record<string, string> = {
  idle: "bg-slate-500",
  thinking: "bg-yellow-400 animate-pulse",
  waiting: "bg-blue-400",
  error: "bg-red-500 animate-pulse",
};

export function AgentCard({ agent }: { agent: Agent }) {
  const dot = statusDot[agent.status] || "bg-slate-500";
  const badge = agentColor(agent.name);

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-4 flex flex-col gap-2 hover:border-slate-600 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
          <span className="font-semibold capitalize text-sm">{agent.name}</span>
        </div>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${badge} text-white/90`}>
          {agent.status}
        </span>
      </div>

      <p className="text-[10px] text-slate-500 font-mono truncate">{agent.model}</p>

      <p className="text-xs text-slate-400 line-clamp-2 min-h-[2rem]">
        {agent.last_message || "No activity yet"}
      </p>

      <p className="text-[10px] text-slate-600 text-right">
        {timeAgo(agent.last_active)}
      </p>
    </div>
  );
}
