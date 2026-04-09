"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

const WS_URL = process.env.NEXT_PUBLIC_BACKEND_WS_URL || "ws://localhost:8000/ws";

interface WSEvent {
  event: string;
  data: any;
}

interface WSContextValue {
  events: WSEvent[];
  isConnected: boolean;
  lastEvent: WSEvent | null;
}

const WSContext = createContext<WSContextValue>({ events: [], isConnected: false, lastEvent: null });

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryDelay = useRef(1000);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      retryDelay.current = 1000;
    };

    ws.onmessage = (e) => {
      try {
        const parsed: WSEvent = JSON.parse(e.data);
        if (parsed.event === "replay" && Array.isArray(parsed.data)) {
          setEvents(parsed.data);
        } else {
          setEvents((prev) => [...prev.slice(-200), parsed]);
          setLastEvent(parsed);
        }
      } catch {}
    };

    ws.onclose = () => {
      setIsConnected(false);
      const delay = retryDelay.current;
      retryDelay.current = Math.min(delay * 2, 30000);
      retryRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return (
    <WSContext.Provider value={{ events, isConnected, lastEvent }}>
      {children}
    </WSContext.Provider>
  );
}

export const useWebSocket = () => useContext(WSContext);
