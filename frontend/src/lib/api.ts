// Signal Hunter — API Client
// Typed fetch wrapper for the FastAPI backend.

import type {
  EventsListResponse,
  FeedResponse,
  HealthResponse,
  SignalsListResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        url.searchParams.set(k, v);
      }
    });
  }

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return fetchAPI<HealthResponse>("/health");
}

export async function getEvents(params?: {
  source?: string;
  category?: string;
  hours?: string;
  page?: string;
}): Promise<EventsListResponse> {
  return fetchAPI<EventsListResponse>("/api/events", params);
}

export async function getSignals(params?: {
  signal_type?: string;
  min_score?: string;
  urgency?: string;
  hours?: string;
  page?: string;
}): Promise<SignalsListResponse> {
  return fetchAPI<SignalsListResponse>("/api/signals", params);
}

export async function getFeed(params?: {
  urgency?: string;
  hours?: string;
  page?: string;
}): Promise<FeedResponse> {
  return fetchAPI<FeedResponse>("/api/feed", params);
}
