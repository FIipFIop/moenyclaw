"use client";
import { api } from "@/lib/api";
import { useState, useRef, useEffect } from "react";
import { useWebSocket } from "@/components/providers/WebSocketProvider";

// Collect master STATUS_UPDATE replies from the WS feed
function useLastReply(lastEvent: any) {
  const [reply, setReply] = useState<string | null>(null);

  useEffect(() => {
    if (
      lastEvent?.event === "agent_message" &&
      lastEvent.data?.message_type === "STATUS_UPDATE" &&
      lastEvent.data?.payload?.reply_to_user
    ) {
      setReply(lastEvent.data.payload.text);
    }
  }, [lastEvent]);

  return { reply, clearReply: () => setReply(null) };
}

const SUGGESTIONS = [
  "Scan markets for opportunities",
  "What are the agents doing?",
  "Show me your best trade idea",
  "What is the current risk level?",
];

export function PromptBar() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<{ role: "user" | "agent"; text: string }[]>([]);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { lastEvent } = useWebSocket();
  const { reply, clearReply } = useLastReply(lastEvent);

  // Auto-append agent replies to history
  useEffect(() => {
    if (reply) {
      setHistory((h) => [...h, { role: "agent", text: reply }]);
      clearReply();
    }
  }, [reply]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, open]);

  async function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;

    setInput("");
    setLoading(true);
    setOpen(true);
    setHistory((h) => [...h, { role: "user", text: msg }]);

    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000"}/api/prompt`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msg }),
        }
      );
      // Response comes back via WebSocket — useLastReply handles it
    } catch {
      setHistory((h) => [...h, { role: "agent", text: "⚠️ Could not reach backend." }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 bg-[#0a0e1a]/95 border-t border-slate-700/50 backdrop-blur">
      {/* Chat history — shown when open */}
      {open && history.length > 0 && (
        <div className="max-w-4xl mx-auto px-4 pt-3 max-h-64 overflow-y-auto scrollbar-thin flex flex-col gap-2">
          {history.map((m, i) => (
            <div
              key={i}
              className={`flex gap-2 text-sm ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.role === "agent" && (
                <span className="h-5 w-5 flex-shrink-0 text-xs bg-green-500 rounded-full flex items-center justify-center mt-0.5">M</span>
              )}
              <div
                className={`rounded-xl px-3 py-2 max-w-[80%] leading-snug ${
                  m.role === "user"
                    ? "bg-cyan-500/20 text-cyan-100 border border-cyan-500/30"
                    : "bg-slate-700/60 text-slate-200 border border-slate-600/30"
                }`}
              >
                {m.text}
              </div>
              {m.role === "user" && (
                <span className="h-5 w-5 flex-shrink-0 text-xs bg-slate-600 rounded-full flex items-center justify-center mt-0.5">Y</span>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex gap-2 justify-start">
              <span className="h-5 w-5 flex-shrink-0 text-xs bg-green-500 rounded-full flex items-center justify-center">M</span>
              <div className="rounded-xl px-3 py-2 bg-slate-700/60 border border-slate-600/30 text-slate-400 text-sm">
                <span className="animate-pulse">thinking…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Suggestion chips — only when no history */}
      {!history.length && !open && (
        <div className="max-w-4xl mx-auto px-4 pt-2 flex gap-2 flex-wrap">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="text-[11px] px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-400 hover:border-cyan-500/50 hover:text-cyan-400 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input row */}
      <div className="max-w-4xl mx-auto px-4 py-3 flex gap-2 items-center">
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-slate-500 hover:text-slate-300 transition-colors text-lg leading-none flex-shrink-0"
          title={open ? "Hide chat" : "Show chat"}
        >
          {open ? "▼" : "▲"}
        </button>

        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          onFocus={() => setOpen(true)}
          placeholder="Ask the agent network anything… (Enter to send)"
          className="flex-1 bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/20 transition-colors"
          disabled={loading}
        />

        <button
          onClick={() => send()}
          disabled={!input.trim() || loading}
          className="px-4 py-2.5 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 hover:bg-cyan-500/30 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-medium transition-colors flex-shrink-0"
        >
          {loading ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
