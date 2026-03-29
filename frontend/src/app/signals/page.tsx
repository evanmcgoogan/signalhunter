"use client";

import { useEffect, useState, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { SignalResponse, SignalsListResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const urgencyColor: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  low: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

function ScoreBar({ score, label }: { score: number; label: string }) {
  const color =
    score >= 0.6
      ? "bg-emerald-500"
      : score >= 0.3
        ? "bg-yellow-500"
        : "bg-zinc-600";
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-mono text-muted-foreground w-20">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all`}
          style={{ width: `${score * 100}%` }}
        />
      </div>
      <span className="text-xs font-mono text-foreground w-10 text-right">
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  );
}

function SignalCard({ signal }: { signal: SignalResponse }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card
      className="bg-card/70 border-border/40 hover:border-border/70 transition-colors cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={urgencyColor[signal.urgency] || urgencyColor.low}
            >
              {signal.urgency.toUpperCase()}
            </Badge>
            <span className="text-xs font-mono text-muted-foreground">
              {signal.signal_type}
            </span>
            {signal.direction && (
              <span
                className={`text-xs font-mono font-bold ${
                  signal.direction === "bullish"
                    ? "text-emerald-400"
                    : signal.direction === "bearish"
                      ? "text-red-400"
                      : "text-zinc-400"
                }`}
              >
                {signal.direction.toUpperCase()}
              </span>
            )}
          </div>
          <span className="text-lg font-mono font-bold text-foreground">
            {(signal.score_calibrated * 100).toFixed(0)}
          </span>
        </div>
        <CardTitle className="text-sm mt-1 leading-snug font-normal">
          {signal.summary}
        </CardTitle>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0 space-y-2">
          <ScoreBar score={signal.score_calibrated} label="Score" />
          <ScoreBar score={signal.confidence} label="Confidence" />

          <div className="flex items-center gap-3 mt-3 text-xs font-mono text-muted-foreground">
            <span>{signal.evidence_event_ids.length} evidence events</span>
            {signal.entities.length > 0 && (
              <span>{signal.entities.join(", ")}</span>
            )}
            <span>{getTimeAgo(signal.detected_at)}</span>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

export default function SignalsPage() {
  const [data, setData] = useState<SignalsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_BASE}/api/signals?hours=24&page_size=50`
      );
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Cannot reach Signal Hunter API"
      );
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
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-mono font-bold">Signal Stream</h1>
        <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground">
          {error ? (
            <span className="text-red-400">API error</span>
          ) : (
            <>
              {data && <span>{data.total} signals (24h)</span>}
              {lastUpdated && (
                <span>Updated {lastUpdated.toLocaleTimeString()}</span>
              )}
              {data && (
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              )}
            </>
          )}
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="bg-card/70 border-border/40">
              <CardHeader>
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-3/4 mt-2" />
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
      ) : data && data.signals.length > 0 ? (
        <div className="space-y-3">
          {data.signals.map((signal) => (
            <SignalCard key={signal.id} signal={signal} />
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <p className="text-sm text-muted-foreground font-mono">
            No signals detected in the last 24 hours.
          </p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            This means no prediction market movements crossed the detection
            threshold. This is not an error.
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
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}
