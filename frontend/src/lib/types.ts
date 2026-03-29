// Signal Hunter — Shared TypeScript types
// These mirror the backend Pydantic models.

export interface EventResponse {
  id: string;
  occurred_at: string;
  ingested_at: string;
  source: string;
  source_ref: string;
  category: string;
  entities: string[];
  thesis_key: string | null;
  direction: string | null;
  magnitude: float;
  reliability: float;
  summary: string;
}

export interface EventsListResponse {
  events: EventResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface SignalResponse {
  id: string;
  detected_at: string;
  signal_type: string;
  entities: string[];
  direction: string | null;
  score_raw: number;
  score_calibrated: number;
  urgency: string;
  confidence: number;
  evidence_event_ids: string[];
  summary: string;
}

export interface SignalsListResponse {
  signals: SignalResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ImplicationResponse {
  id: string;
  created_at: string;
  headline: string;
  summary: string;
  implications: string[];
  urgency: string;
  stance: string;
  confidence: number;
  entities: string[];
  signal_ids: string[];
  event_ids: string[];
  world_model_updates: Record<string, unknown>;
  feedback: string | null;
}

export interface FeedResponse {
  items: ImplicationResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ServiceStatus {
  name: string;
  healthy: boolean;
  latency_ms: number | null;
  error: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
  services: ServiceStatus[];
}

// Type alias for readability
type float = number;
