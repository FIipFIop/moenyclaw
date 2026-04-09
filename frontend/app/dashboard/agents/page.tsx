"use client";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { AgentCard } from "@/components/dashboard/AgentCard";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";

export default function AgentsPage() {
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: api.agents,
    refetchInterval: 3_000,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-bold text-slate-200">Agent Network</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((a) => <AgentCard key={a.name} agent={a} />)}
      </div>
      <div>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">Full Activity Log</h2>
        <ActivityFeed />
      </div>
    </div>
  );
}
