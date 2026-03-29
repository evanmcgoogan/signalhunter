"use client";

import { useEffect, useState, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { FeedResponse, ImplicationResponse, HealthResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const urgencyColor: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  low: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

const stanceColor: Record<string, string> = {
  bullish: "text-emerald-400",
  bearish: "text-red-400",
  cautious: "text-yellow-400",
  neutral: "text-zinc-400",
};

function WorldModelBar() {
  const variables = [
    { label: "Risk Regime", value: "NEUTRAL", level: 0.5 },
    { label: "Geo Risk", value: "MODERATE", level: 0.4 },
    { label: "Smart Money", value: "\u2014", level: 0.5 },
    { label: "Next Catalyst", value: "Awaiting data...", level: null },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      {variables.map((v) => (
        <div
          key={v.label}
          className="bg-card/50 border border-border/30 rounded-lg px-3 py-2"
        >
          <div className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
            {v.label}
          </div>
          <div className="flex items-center gap-2 mt-1">
            {v.level !== null && (
              <div className="w-12 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500/70 rounded-full transition-all"
                  style={{ width: `${v.level * 100}%` }}
                />
              </div>
            )}
            <span className="text-sm font-mono font-medium">{v.value}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function ImplicationCard({ item }: { item: ImplicationResponse }) {
  const [expanded, setExpanded] = useState(false);
  const age = getTimeAgo(item.created_at);

  return (
    <Card
      className="bg-card/70 border-border/40 hover:border-border/70 transition-colors cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge
              variant="outline"
              className={urgencyColor[item.urgency] || urgencyColor.low}
            >
              {item.urgency.toUpperCase()}
            </Badge>
            <span
              className={`text-sm font-mono font-semibold ${stanceColor[item.stance] || ""}`}
            >
              {item.stance.toUpperCase()}
            </span>
          </div>
          <span className="text-xs font-mono text-muted-foreground whitespace-nowrap">
            {age}
          </span>
        </div>
        <CardTitle className="text-base mt-2 leading-tight">
          {item.headline}
        </CardTitle>
        <CardDescription className="text-sm mt-1">
          {item.summary}
        </CardDescription>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0">
          {item.implications.length > 0 && (
            <div className="mt-2 space-y-1.5">
              <div className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Implications
              </div>
              {item.implications.map((imp, i) => (
                <div
                  key={i}
                  className="text-sm text-foreground/80 pl-3 border-l-2 border-emerald-500/30"
                >
                  {imp}
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center gap-4 mt-4 text-xs font-mono text-muted-foreground">
            <span>Confidence: {(item.confidence * 100).toFixed(0)}%</span>
            <span>{item.signal_ids.length} signals</span>
            <span>{item.event_ids.length} events</span>
            {item.entities.length > 0 && (
              <span>{item.entities.join(", ")}</span>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

function EmptyFeed({ systemStatus }: { systemStatus: string | null }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-full bg-zinc-800/50 flex items-center justify-center mb-4">
        <svg
          className="w-8 h-8 text-zinc-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9.348 14.651a3.75 3.75 0 010-5.303m5.304 0a3.75 3.75 0 010 5.303m-7.425 2.122a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.788m13.788 0c3.808 3.808 3.808 9.98 0 13.788M12 12h.008v.008H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-mono font-semibold text-foreground mb-1">
        Sensors Active — No Implications Yet
      </h3>
      <p className="text-sm text-muted-foreground max-w-md">
        Signal Hunter is polling prediction markets. Implication cards appear
        when significant signals are detected and synthesized by Claude.
        This is not an error — it means no signals have crossed the threshold.
      </p>
      {systemStatus && (
        <div className="mt-4">
          <Badge
            variant="outline"
            className={
              systemStatus === "ok"
                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                : systemStatus === "degraded"
                  ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
                  : "bg-red-500/20 text-red-400 border-red-500/30"
            }
          >
            System: {systemStatus.toUpperCase()}
          </Badge>
        </div>
      )}
    </div>
  );
}

function FreshnessBar({
  lastUpdated,
  total,
  error,
}: {
  lastUpdated: Date | null;
  total: number | null;
  error: string | null;
}) {
  return (
    <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground">
      {error ? (
        <span className="text-red-400">API error</span>
      ) : (
        <>
          {total !== null && <span>{total} items (48h)</span>}
          {lastUpdated && (
            <span>
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        </>
      )}
    </div>
  );
}

export default function FeedPage() {
  const [feed, setFeed] = useState<FeedResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const [feedRes, healthRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/feed?hours=48`).then((r) => {
          if (!r.ok) throw new Error(`Feed: ${r.status}`);
          return r.json();
        }),
        fetch(`${API_BASE}/health`).then((r) => {
          if (!r.ok) throw new Error(`Health: ${r.status}`);
          return r.json();
        }),
      ]);

      if (feedRes.status === "fulfilled") {
        setFeed(feedRes.value);
        setError(null);
      } else {
        setError(feedRes.reason?.message || "Feed fetch failed");
      }
      if (healthRes.status === "fulfilled") setHealth(healthRes.value);
      setLastUpdated(new Date());
    } catch {
      setError("Cannot reach Signal Hunter API. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  return (
    <div>
      <WorldModelBar />

      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-mono font-bold">Intelligence Feed</h1>
        <div className="flex items-center gap-4">
          <FreshnessBar
            lastUpdated={lastUpdated}
            total={feed?.total ?? null}
            error={error}
          />
          {health && (
            <div className="flex items-center gap-2">
              {health.services.map((s) => (
                <div key={s.name} className="flex items-center gap-1">
                  <div
                    className={`w-1.5 h-1.5 rounded-full ${
                      s.healthy ? "bg-emerald-500" : "bg-red-500"
                    }`}
                  />
                  <span className="text-xs font-mono text-muted-foreground">
                    {s.name}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="bg-card/70 border-border/40">
              <CardHeader>
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-5 w-3/4 mt-2" />
                <Skeleton className="h-4 w-full mt-1" />
              </CardHeader>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card className="bg-red-500/10 border-red-500/30">
          <CardContent className="py-6 text-center">
            <p className="text-sm text-red-400 font-mono">{error}</p>
            <p className="text-xs text-red-400/60 mt-2 font-mono">
              Check that the backend is running on {API_BASE}
            </p>
          </CardContent>
        </Card>
      ) : feed && feed.items.length > 0 ? (
        <div className="space-y-3">
          {feed.items.map((item) => (
            <ImplicationCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <EmptyFeed systemStatus={health?.status || null} />
      )}
    </div>
  );
}

function getTimeAgo(isoString: string): string {
  const now = new Date();
  const then = new Date(isoString);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays}d ago`;
}
