"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { HealthResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function StatusPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/health`);
        const json = await res.json();
        setHealth(json);
        setLastUpdated(new Date());
      } catch {
        // silently fail
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const statusColor =
    health?.status === "ok"
      ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
      : health?.status === "degraded"
        ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
        : "bg-red-500/20 text-red-400 border-red-500/30";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-mono font-bold">System Status</h1>
        {health && (
          <Badge variant="outline" className={statusColor}>
            {health.status.toUpperCase()}
          </Badge>
        )}
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="bg-card/70">
              <CardHeader>
                <Skeleton className="h-5 w-32" />
              </CardHeader>
            </Card>
          ))}
        </div>
      ) : health ? (
        <div className="space-y-4">
          {/* System info */}
          <Card className="bg-card/50 border-border/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono text-muted-foreground">
                System
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm font-mono">
                <div>
                  <div className="text-muted-foreground text-xs">Version</div>
                  <div className="font-semibold">v{health.version}</div>
                </div>
                <div>
                  <div className="text-muted-foreground text-xs">
                    Environment
                  </div>
                  <div className="font-semibold">{health.environment}</div>
                </div>
                <div>
                  <div className="text-muted-foreground text-xs">
                    Last Check
                  </div>
                  <div className="font-semibold">
                    {lastUpdated
                      ? lastUpdated.toLocaleTimeString()
                      : "\u2014"}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground text-xs">
                    Services
                  </div>
                  <div className="font-semibold">
                    {health.services.filter((s) => s.healthy).length}/
                    {health.services.length} healthy
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Individual services */}
          <div className="grid gap-3">
            {health.services.map((service) => (
              <Card
                key={service.name}
                className={`border-border/30 ${
                  service.healthy ? "bg-card/50" : "bg-red-500/5"
                }`}
              >
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2.5 h-2.5 rounded-full ${
                          service.healthy
                            ? "bg-emerald-500 shadow-emerald-500/50 shadow-sm"
                            : "bg-red-500 shadow-red-500/50 shadow-sm"
                        }`}
                      />
                      <div>
                        <div className="text-sm font-mono font-semibold capitalize">
                          {service.name}
                        </div>
                        {service.error && (
                          <div className="text-xs text-red-400 font-mono mt-0.5">
                            {service.error}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {service.latency_ms !== null && (
                        <span className="text-xs font-mono text-muted-foreground">
                          {service.latency_ms.toFixed(0)}ms
                        </span>
                      )}
                      <Badge
                        variant="outline"
                        className={
                          service.healthy
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-red-500/10 text-red-400 border-red-500/20"
                        }
                      >
                        {service.healthy ? "HEALTHY" : "DOWN"}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Architecture */}
          <Card className="bg-card/50 border-border/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono text-muted-foreground">
                Architecture
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xs font-mono text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>Layer 1: Sensor Grid</span>
                  <span className="text-emerald-400">Polymarket, Kalshi</span>
                </div>
                <div className="flex justify-between">
                  <span>Layer 2: Signal Detection</span>
                  <span className="text-emerald-400">
                    PredictionMarketDetector
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Layer 3: Synthesis</span>
                  <span className="text-emerald-400">Claude Opus</span>
                </div>
                <div className="flex justify-between border-t border-border/20 pt-1 mt-1">
                  <span>Database</span>
                  <span>Supabase PostgreSQL 17.6</span>
                </div>
                <div className="flex justify-between">
                  <span>Cache</span>
                  <span>Upstash Redis</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card className="bg-red-500/10 border-red-500/30">
          <CardContent className="py-6 text-center">
            <p className="text-sm text-red-400 font-mono">
              Cannot reach Signal Hunter API.
            </p>
            <p className="text-xs text-red-400/60 mt-1 font-mono">
              Start the backend: cd backend &amp;&amp; uv run uvicorn
              app.main:app --port 8000
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
