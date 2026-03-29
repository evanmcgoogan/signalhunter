"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { EventResponse, EventsListResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const sourceColors: Record<string, string> = {
  polymarket: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  kalshi: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  price_feed: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  news: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  curated_x: "bg-sky-500/20 text-sky-400 border-sky-500/30",
  curated_yt: "bg-red-500/20 text-red-400 border-red-500/30",
};

const directionIcon: Record<string, string> = {
  bullish: "\u2191",
  bearish: "\u2193",
  neutral: "\u2194",
};

function EventRow({ event }: { event: EventResponse }) {
  const age = getTimeAgo(event.occurred_at);

  return (
    <div className="flex items-start gap-3 py-3 px-4 border-b border-border/20 hover:bg-card/30 transition-colors">
      {/* Magnitude bar */}
      <div className="flex flex-col items-center gap-1 pt-0.5 w-10 shrink-0">
        <span className="text-xs font-mono font-bold text-foreground">
          {event.magnitude.toFixed(0)}
        </span>
        <div className="w-6 h-1 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500/70 rounded-full"
            style={{ width: `${Math.min(event.magnitude, 100)}%` }}
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <Badge
            variant="outline"
            className={`text-[10px] ${sourceColors[event.source] || "bg-zinc-500/20 text-zinc-400"}`}
          >
            {event.source.toUpperCase()}
          </Badge>
          <span className="text-xs font-mono text-muted-foreground">
            {event.category}
          </span>
          {event.direction && (
            <span
              className={`text-xs font-mono font-bold ${
                event.direction === "bullish"
                  ? "text-emerald-400"
                  : event.direction === "bearish"
                    ? "text-red-400"
                    : "text-zinc-400"
              }`}
            >
              {directionIcon[event.direction] || ""} {event.direction}
            </span>
          )}
        </div>
        <p className="text-sm text-foreground/90 leading-snug">{event.summary}</p>
        {event.entities.length > 0 && (
          <div className="flex gap-1 mt-1 flex-wrap">
            {event.entities.map((e) => (
              <span
                key={e}
                className="text-[10px] font-mono px-1.5 py-0.5 bg-zinc-800/50 rounded text-muted-foreground"
              >
                {e}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Time */}
      <span className="text-xs font-mono text-muted-foreground whitespace-nowrap shrink-0">
        {age}
      </span>
    </div>
  );
}

export default function EventsPage() {
  const [data, setData] = useState<EventsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState("24");

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(
          `${API_BASE}/api/events?hours=${hours}&page_size=100`
        );
        const json = await res.json();
        setData(json);
      } catch {
        // silently fail
      } finally {
        setLoading(false);
      }
    }
    setLoading(true);
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [hours]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-mono font-bold">Event Stream</h1>
        <div className="flex items-center gap-2">
          {["1", "6", "24", "48"].map((h) => (
            <button
              key={h}
              onClick={() => setHours(h)}
              className={`px-2 py-1 text-xs font-mono rounded transition-colors ${
                hours === h
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {h}h
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex gap-3 py-3 px-4">
              <Skeleton className="w-10 h-6" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-4 w-full" />
              </div>
            </div>
          ))}
        </div>
      ) : data && data.events.length > 0 ? (
        <Card className="bg-card/50 border-border/30 overflow-hidden">
          <CardContent className="p-0">
            {data.events.map((event) => (
              <EventRow key={event.id} event={event} />
            ))}
          </CardContent>
          <div className="px-4 py-2 border-t border-border/20 text-xs font-mono text-muted-foreground">
            Showing {data.events.length} of {data.total} events
          </div>
        </Card>
      ) : (
        <div className="text-center py-20">
          <p className="text-sm text-muted-foreground font-mono">
            No events in the last {hours} hours.
          </p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            Events appear when sensors detect prediction market movements.
          </p>
        </div>
      )}
    </div>
  );
}

function getTimeAgo(isoString: string): string {
  const now = new Date();
  const then = new Date(isoString);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "now";
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h`;
  return `${Math.floor(diffHr / 24)}d`;
}
