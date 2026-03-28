# Signal Hunter V2 — Master Plan (Council Revision)

> *"Taste on top of cutting edge. Quality → Trust → Usefulness."*

---

## Preamble: What Changed After Council Review

The first plan was ambitious and architecturally sound but sequenced wrong. The council's critique identified real problems:

1. **The backbone was wrong.** Making Unusual Whales the day-one foundation means spending $125/mo before proving the core thesis works. The existing prediction market + price data wedge is already functional and free. UW should be a gated expansion, not the starting point.

2. **Claude shouldn't own the world model.** If an LLM writes the state variables, you can't debug why a bad alert fired. Deterministic scoring first, Claude narration second. This is a trust-critical distinction.

3. **Calendar-based phases are fake.** "Days 1-3" means nothing. Phase gates should be measurable: shadow mode beats V1, false-positive rate is under budget, calibration error is below threshold.

4. **The alert budget was missing.** Without a concrete quality gate (≤3 push alerts/day, ≤1 false positive/day), the system optimizes for volume over trust.

5. **Falsifiers were absent.** Every implication card must include what would prove it wrong. This is the single highest-leverage trust feature.

However, the council was wrong about one thing: **the strangler upgrade pattern.** The memory file is explicit — *"Better to build something from scratch than fix buggy old code in a Frankenstein manner."* The V1 codebase has solid algorithms (forecast_engine.py, forecast_evaluator.py are production-grade) but the architecture (Flask, inline CSS, no type safety, 3,562-line monolithic database.py) is not the foundation for a production product. The correct approach: **fresh repo, ported algorithms, V1 runs as the control group.**

This plan synthesizes both perspectives.

---

## First Principles

1. **Don't build what you can rent.** We build the synthesis layer. Everything else — data infrastructure, real-time delivery, background jobs, UI components — we rent.

2. **Quality → Trust → Usefulness.** False positives destroy trust faster than missed signals. Every card must earn the user's attention. Alert budget: **≤3 push alerts/day, ≤1 false positive/day.**

3. **Taste is the moat.** The curated sources, the investment theses, the feedback history — these encode a specific worldview that no generic product approximates. Claude synthesizes; Evan curates.

4. **Design for replacement.** Code is ephemeral. What compounds across rewrites: evaluation history, curation graph, signal weights, user feedback, world state log. These are the durable assets.

5. **Deterministic core, LLM narration.** Scoring, state transitions, and alert gating are deterministic and debuggable. Claude explains *why* something matters — it never originates scores or state transitions. You must be able to trace any alert back to deterministic evidence without touching an LLM.

6. **Prove the wedge before expanding scope.** Prediction markets + prices + curated macro sources are the initial edge. Options flow, dark pool, and congressional trades expand the sensor grid only after the core proves itself.

7. **End-to-end before depth.** A crude pipeline that works is more valuable than a perfect signal detector with no synthesis layer. Get the full loop running, then improve each stage.

8. **One operator, zero ops burden.** If it requires a pager, it's wrong.

---

## The Product

### Core Job

*"Tell me what changed in macro/politics/geopolitics, why it matters, what it touches in my thesis/watchlist, and what I should watch next — with evidence and falsifiers."*

### Surfaces

| Surface | Purpose |
|---|---|
| **Briefing** | Top 3 regime changes since last visit. The "10-second world model update." |
| **Implication Feed** | High-signal cards with evidence chains, falsifiers, affected assets/theses. The main view. |
| **Thesis Board** | Active investment theses with confidence, invalidation levels, next catalysts. |
| **World Model Strip** | Compact regime bar — deterministic fields, recent deltas, always visible. |
| **Decision Journal** | Acted / ignored / useful / not useful + short notes. The feedback loop. |
| **Source Monitor** | Curated sources, performance scores, recent output. |
| **Forecast Tracker** | Active predictions, historical accuracy, calibration curves, weight transparency. |

### The Implication Card

Every card answers five questions:

```
┌─────────────────────────────────────────────────────────┐
│ ⚡ HIGH URGENCY                              2 min ago  │
│                                                         │
│ WHAT CHANGED                                            │
│ Polymarket "Fed cuts by June" surged from 52% to 71%    │
│ while gold futures jumped 2.1% in 45 minutes.           │
│                                                         │
│ WHY NOW                                                 │
│ Weak jobs report pre-leak signals + dovish Waller        │
│ comments yesterday. Two independent evidence families.   │
│                                                         │
│ WHAT IT TOUCHES                                         │
│ ◆ TLT (your watchlist) — rallies on rate cuts           │
│ ◆ GLD (your watchlist) — already moving                 │
│ ◆ "Fed pivot" thesis — confidence: 52% → 68%            │
│                                                         │
│ WHAT COULD PROVE THIS WRONG                             │
│ • Hot CPI print next Tuesday reverses the narrative     │
│ • Fed speakers this week push back on cut expectations  │
│ • Gold move is positioning ahead of FOMC, not signal    │
│                                                         │
│ WHY THIS MATTERS TO YOU                                 │
│ Your TLT position benefits. Consider: if CPI confirms   │
│ softness, the "Fed pivot" thesis upgrades to high       │
│ confidence. Watch Tuesday's print closely.              │
│                                                         │
│ Evidence: [3 signals] [2 sources]  Confidence: 68%      │
│ 👍 Useful  👎 Not useful  ✅ Acted on  📝 Note          │
└─────────────────────────────────────────────────────────┘
```

---

## Three Layers

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: SYNTHESIS + NARRATION                              │
│  Claude Opus explains what signals mean and why they matter  │
│                                                             │
│  Inputs: scored signal clusters + expert context + user      │
│          theses/watchlist                                    │
│  Outputs: implication cards, world model narration,          │
│           forecast framing                                   │
│  Rules: Claude NEVER originates scores, state transitions,   │
│         or alert decisions. Deterministic core decides;      │
│         Claude explains.                                     │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: DETERMINISTIC SIGNAL SCORING                      │
│  "Is this noise, or does it matter?"                        │
│                                                             │
│  score = evidence_strength × novelty × relevance ×          │
│          timeliness × source_reliability                     │
│                                                             │
│  Detectors: price velocity, volume shock, cross-platform    │
│  divergence, basket moves, catalyst proximity, no-news      │
│  move, lead-lag mapping, expert consensus                   │
│                                                             │
│  Novelty suppression: repeated signals within cooling       │
│  window are downweighted, not re-alerted.                   │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1: SENSOR GRID                                       │
│                                                             │
│  Phase 1 (Day 1):                                           │
│    Polymarket ─── Prediction market prices + volume         │
│    Kalshi ─────── Prediction market prices + volume         │
│    Price feeds ── SPY QQQ VIX TLT GLD WTI BTC ETH         │
│    News RSS ──── Existing news monitor                      │
│                                                             │
│  Phase 3 (Earned):                                          │
│    Curated X ─── 10-15 expert accounts (~$5/mo)             │
│    Curated YT ── Podcasts + video transcripts (free)        │
│                                                             │
│  Phase 7 (Gated Pilot):                                     │
│    Unusual Whales ── Options flow, dark pool, congress,     │
│         ($125/mo)     institutions, calendar                │
│         Only if: ≥15% lift in lead time or precision        │
│         over 30 days on tracked assets.                     │
└─────────────────────────────────────────────────────────────┘
```

---

## The World Model: Deterministic State, LLM Narration

This is the biggest design change from the first plan. The world model is **deterministic** — Claude doesn't decide what the risk regime is. Signals do. Claude explains *why* it shifted and *what it means*.

### State Variables

```python
class WorldState(BaseModel):
    as_of: datetime
    risk_appetite: RegimeField       # Risk-on / risk-off / transitioning
    growth_pressure: RegimeField     # Expansion / contraction / stalling
    inflation_pressure: RegimeField  # Hot / cooling / anchored
    policy_pressure: RegimeField     # Hawkish / dovish / neutral
    geopolitical_risk: RegimeField   # Elevated / baseline / de-escalating
    crypto_regime: RegimeField       # Risk-on / regulatory fear / accumulation
    next_catalyst: CatalystField     # Event, date, expected impact

class RegimeField(BaseModel):
    value: float                     # 0-1 normalized
    direction: Direction             # RISING | FALLING | STABLE
    confidence: float                # 0-1
    driver_signal_ids: list[str]     # Traceable evidence
    narrative: str                   # Claude-written (populated AFTER state is set)
```

### How State Transitions Work

1. New events arrive from sensors → normalized into ObservedEvents
2. **Deterministic detectors** score signals
3. Signals that clear threshold are clustered by thesis/asset
4. **Deterministic state reducer** updates world model fields based on signal types, directions, and weights — no LLM involved
5. **After** state is updated, Claude Opus writes the narrative
6. State + narrative logged to `world_state_log`
7. If alert criteria met (novel + time-sensitive + relevant + 2+ evidence families), push notification fires

The critical property: you can trace any alert → implication → signal cluster → individual events → raw data. No black box.

### Deterministic Scoring Formula

```python
def composite_score(signal: Signal) -> float:
    return (
        signal.evidence_strength    # Move size, liquidity, confirmation count
        * signal.novelty            # Downweight if similar signal fired recently
        * signal.relevance          # Touches active thesis, watchlist, or asset basket?
        * signal.timeliness         # Leads a known catalyst or downstream move?
        * signal.source_reliability # Learned from outcome tracking + explicit feedback
    )
```

Each factor is 0-1. Product gives composite 0-1. Threshold for Claude synthesis: starts conservative (~0.3). Threshold for push alert: higher (~0.6) + requires 2+ evidence families.

---

## Unusual Whales: Gated Expansion, Not Foundation

### Why Defer (Not Kill)

UW's data is genuinely unique — options flow, dark pool prints, congressional trades. But:
- The prediction market + price + curated sources wedge is already functional in V1
- $125/mo should be justified by measured lift
- The core thesis (synthesis + taste = edge) can be proven without UW
- Sensor abstraction means UW slots in cleanly when ready

### When UW Enters (Phase 7 Gate)

**Prerequisites:**
- Core system running stably for 30+ days
- Evaluation loop producing reliable accuracy metrics
- At least 100 resolved forecasts for calibration
- Daily user engagement established

**Pilot Protocol:**
- Subscribe to UW trial ($40/week)
- Ingest options flow + dark pool for small asset set (SPY, QQQ, AAPL, NVDA, TSLA)
- 30-day comparison: does adding UW signals produce ≥15% lift in lead time or precision?
- If yes → commit to Standard tier ($125/mo), expand to full watchlist
- If no → save $125/mo, revisit later

### Architecture Preparation

The sensor layer accepts UW from day one:

```python
class Sensor(Protocol):
    """Every data source implements this interface."""
    source: Source
    async def poll(self) -> list[ObservedEvent]: ...
    async def health_check(self) -> bool: ...

# Phase 1 sensors:
class PolymarketSensor(Sensor): ...
class KalshiSensor(Sensor): ...
class PriceFeedSensor(Sensor): ...
class NewsSensor(Sensor): ...

# Phase 3 sensors:
class TwitterSensor(Sensor): ...
class YouTubeSensor(Sensor): ...

# Phase 7 sensors (gated):
class UWOptionsSensor(Sensor): ...
class UWDarkPoolSensor(Sensor): ...
class UWCongressSensor(Sensor): ...
```

Adding UW = implementing sensor classes + migration. No architectural changes.

### What UW Would Unlock

| UW Endpoint | What It Adds | Signal Hunter Use |
|---|---|---|
| Options Flow | Every options order, NBBO-inferred direction | The Hormuz trade: detect unusual positioning |
| Dark Pool | Institutional block trades | Smart money invisible on lit exchanges |
| Congressional Trades | Politician stock transactions | Insider-adjacent signal |
| Economic Calendar | FOMC, CPI, NFP dates | Catalyst proximity (partially built with free data) |
| Institution Holdings | 13F filings | Smart money positioning |
| Stock Technicals | 14 built-in indicators | Rent, don't build |

---

## Curated Intelligence Sources: Taste as Data

### Concept

Evan curates 10-15 high-signal sources to start:
- **X accounts**: Financial analysts, macro thinkers, breaking news
- **YouTube channels**: Dwarkesh Patel, All-In, SemiAnalysis, sector-specific
- **Podcasts**: Via YouTube or direct RSS

If Claude is synthesizing what's happening and what'll happen next, it should have access to the same expert perspectives that inform Evan's thinking. Dylan Patel's semiconductor analysis meeting an unusual prediction market move in AI regulation — no existing product connects those dots.

### Discipline

- **10-15 sources max** to start. Weekly review. Prune aggressively.
- Every source gets: tier (1-3), domain tags, lead/lag profile, reliability score
- **Long-form content = context, not triggers.** Podcasts inform Claude's synthesis of signals that already cleared the deterministic threshold. They don't generate alerts on their own.
- Source reliability learned from outcomes: sources whose claims lead to accurate forecasts gain score; noise sources lose it.

### Implementation

**X/Twitter**: TwitterAPI.io ($0.15/1K tweets, ~$5/mo). Poll every 5 min. Haiku categorizes.

**YouTube/Podcasts**: RSS feeds (free) + youtube-transcript-api (free). Haiku summarizes.

**Integration rule**: Curated context fed into synthesis AFTER signals clear deterministic threshold — never as primary triggers.

---

## Data Pipeline: End-to-End Flow

```
T+0s    Polymarket "Fed cuts by June" moves from 52% → 71%
T+1s    Sensor picks it up
T+1s    ObservedEvent normalized → INSERT to database

T+2s    Deterministic detectors:
        → price_velocity: "19pp prediction market move in 5 min"
        → cross_platform: GLD +2.1%, TLT +0.8% same window
        → basket_move: 3 rate-sensitive assets moving together
        → Cluster formed: composite score 0.72

T+2s    Deterministic state reducer:
        → policy_pressure: 0.4 → 0.6 (RISING, dovish)
        → driver_signal_ids updated

T+3s    Score 0.72 > synthesis threshold 0.3
        → Retrieve curated context: @FedWatcher tweeted about Waller 2h ago
        → Claude Opus: signals + world state delta + context + Evan's theses

T+8s    Structured implication returned
        → INSERT → Supabase Realtime → dashboard
        → Urgency HIGH + 2 evidence families → push notification

Total: ~8-10 seconds from market event to actionable insight.
```

### Market-Aware Scheduling

| Mode | When | Behavior |
|---|---|---|
| **Active** | Market hours (9:30-4:00 ET, Mon-Fri) | Full polling. All sensors max frequency. |
| **Watch** | Extended hours | Reduced price polling. Prediction markets + curated full speed. |
| **Sleep** | Overnight + weekends | Prediction markets + curated only. Synthesis batched. |

---

## Claude Strategy

### Cost Model

| Task | Model | Daily Calls | Daily Cost |
|---|---|---|---|
| Implication synthesis | Opus 4.6 | ~10-20 | $1.00-2.00 |
| World model narration | Opus 4.6 | ~10-20 | $0.75-1.50 |
| Tweet categorization | Haiku 4.5 | ~30-50 | $0.03-0.05 |
| Transcript summary | Haiku 4.5 | ~3-5 | $0.02-0.05 |
| Overnight digest | Opus 4.6 | 1 | $0.15 |

**Estimated: $2-4/day → $60-120/month**

Lower than V1 of this plan because deterministic pre-filtering is more aggressive and the alert budget constrains synthesis volume.

### Controls
1. Deterministic filter before Claude — most events never reach an LLM
2. Batch off-hours synthesis into single calls
3. Haiku for triage (60x cheaper than Opus)
4. Novelty suppression prevents redundant synthesis
5. Alert budget naturally constrains volume

### Structured Outputs
All calls use `output_config` with `strict: True`. Constrained decoding — the model cannot produce invalid JSON. Eliminates V1's markdown fence stripping.

---

## Infrastructure

| Component | Service | Cost |
|---|---|---|
| Database | Supabase (free → $25/mo Pro) | $0-25/mo |
| Cache | Upstash Redis (free tier) | $0/mo |
| Background Jobs | APScheduler (in-process) | $0/mo |
| Backend | Railway ($5/mo Hobby) | $5-15/mo |
| Frontend | Vercel (free tier) | $0/mo |
| X Monitoring | TwitterAPI.io | ~$5/mo |
| YouTube | RSS + youtube-transcript-api | $0/mo |

**Phase 1-6 total: $70-165/mo** (infra + Claude + TwitterAPI)
**Phase 7+ if UW passes pilot: $195-290/mo**

### Reversibility

Every choice has a clear exit path within hours to days. Supabase is just Postgres (`pg_dump`). Railway is just Docker. Vercel is just Next.js. Nothing is a trap.

---

## Tech Stack

**Backend**: FastAPI + Python 3.12, SQLAlchemy 2.0 async + Alembic, uv, APScheduler 4.x

**Frontend**: Next.js 15 + TypeScript + Tailwind + shadcn/ui, Supabase JS for real-time, Recharts/Tremor

**AI**: Claude Opus 4.6 (synthesis) + Haiku 4.5 (triage), structured outputs only

### Ported from V1

| V1 File | V2 Destination | What's Ported |
|---|---|---|
| forecast_engine.py (1,063 lines) | core/signal_aggregator.py | Signal weighting, regime detection, probability calculation |
| forecast_evaluator.py (875 lines) | core/evaluator.py | Brier scoring, weight learning (2% rate, 90% shrinkage), confidence cooldown |
| story_generator.py (2,827 lines) | core/clustering.py | Question-stem extraction, market clustering. Prose layer rewritten. |
| config.py (560 lines) | config.py | Dataclass-based config, all thresholds in one place |
| polymarket.py + kalshi.py | sensors/ | API clients, verified and updated |
| signals.py (793 lines) | signals/ directory | Individual detector classes |
| tests/ (~4,060 lines) | tests/ | Ported as specs, rewritten with pytest |

---

## Project Structure

```
signal-hunter/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI + APScheduler lifespan
│   │   ├── config.py                  # Pydantic Settings (ported from V1)
│   │   ├── deps.py                    # DI: db, claude, cache
│   │   │
│   │   ├── api/
│   │   │   ├── briefing.py            # GET /api/briefing
│   │   │   ├── implications.py        # GET /api/implications
│   │   │   ├── theses.py              # CRUD /api/theses
│   │   │   ├── world_state.py         # GET /api/world-state
│   │   │   ├── forecasts.py           # GET /api/forecasts
│   │   │   ├── feedback.py            # POST /api/feedback
│   │   │   ├── sources.py             # CRUD /api/sources
│   │   │   ├── replay.py              # GET /api/replay-runs/:id
│   │   │   └── health.py              # GET /health
│   │   │
│   │   ├── core/
│   │   │   ├── pipeline.py            # events → score → synthesize
│   │   │   ├── signal_aggregator.py   # Ported from forecast_engine
│   │   │   ├── state_reducer.py       # Deterministic world model
│   │   │   ├── synthesis.py           # Claude narration (AFTER state set)
│   │   │   ├── evaluator.py           # Ported from forecast_evaluator
│   │   │   ├── clustering.py          # Ported from story_generator
│   │   │   └── scorer.py              # Composite scoring formula
│   │   │
│   │   ├── signals/
│   │   │   ├── base.py                # Detector protocol
│   │   │   ├── price_velocity.py
│   │   │   ├── volume_shock.py
│   │   │   ├── cross_platform.py
│   │   │   ├── basket_move.py
│   │   │   ├── catalyst_proximity.py
│   │   │   ├── no_news_move.py
│   │   │   ├── lead_lag.py
│   │   │   ├── expert_consensus.py
│   │   │   ├── multi_signal.py
│   │   │   └── registry.py
│   │   │
│   │   ├── sensors/
│   │   │   ├── base.py                # Sensor protocol
│   │   │   ├── polymarket.py          # Ported
│   │   │   ├── kalshi.py              # Ported
│   │   │   ├── price_feed.py          # Ported
│   │   │   ├── news.py                # Ported
│   │   │   ├── twitter.py             # Phase 3
│   │   │   ├── youtube.py             # Phase 3
│   │   │   ├── uw_options.py          # Phase 7
│   │   │   ├── uw_darkpool.py         # Phase 7
│   │   │   ├── uw_congress.py         # Phase 7
│   │   │   └── scheduler.py           # APScheduler + market modes
│   │   │
│   │   ├── models/
│   │   │   ├── event.py
│   │   │   ├── signal.py
│   │   │   ├── implication.py
│   │   │   ├── world_state.py
│   │   │   ├── forecast.py
│   │   │   ├── thesis.py
│   │   │   ├── source.py
│   │   │   └── feedback.py
│   │   │
│   │   └── services/
│   │       ├── claude.py
│   │       └── cache.py
│   │
│   ├── alembic/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── scenarios/                 # Ceasefire, Fed cut, tariff, AI capex, oil shock
│   │   └── conftest.py
│   │
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── alembic.ini
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Briefing
│   │   ├── feed/page.tsx              # Implications
│   │   ├── theses/page.tsx
│   │   ├── world/page.tsx
│   │   ├── forecasts/page.tsx
│   │   ├── journal/page.tsx
│   │   └── settings/page.tsx
│   │
│   ├── components/
│   │   ├── ui/                        # shadcn/ui
│   │   ├── cards/
│   │   ├── charts/
│   │   ├── layout/
│   │   └── feed/
│   │
│   ├── lib/
│   │   ├── supabase.ts
│   │   ├── api.ts
│   │   └── types.ts
│   │
│   ├── package.json
│   ├── tailwind.config.ts
│   └── next.config.ts
│
├── v1-reference/                      # V1 source (read-only porting reference)
├── docker-compose.yml
└── README.md
```

---

## Key Types

```python
class ObservedEvent(BaseModel):
    id: str
    occurred_at: datetime
    ingested_at: datetime
    source: Source
    source_ref: str                    # Dedup key
    category: EventCategory
    entities: list[str]                # Tickers, markets, themes
    thesis_key: str | None
    direction: Direction | None
    magnitude: float                   # 0-100
    reliability: float                 # Learned
    novelty_hash: str                  # Cooling window dedup
    payload_ref: str                   # Hash to compressed raw (not in hot table)

class Signal(BaseModel):
    id: str
    thesis_key: str | None
    signal_type: SignalType
    score_raw: float
    score_calibrated: float
    urgency: Urgency
    novelty: float
    relevance: float
    timeliness: float
    confidence: float
    evidence_event_ids: list[str]

class Implication(BaseModel):
    id: str
    signal_ids: list[str]
    headline: str
    what_changed: str
    why_now: str
    affected_assets: list[str]
    affected_theses: list[str]
    stance: Stance
    urgency: Urgency
    falsifiers: list[str]              # What would prove this wrong
    recommended_checks: list[str]      # What to watch next
    evidence_ids: list[str]
    confidence_calibrated: float
    curated_context_used: list[str]

class Forecast(BaseModel):
    id: str
    implication_id: str
    asset: str
    horizon_hours: int
    direction: Direction
    magnitude_bucket: str
    confidence_raw: float
    confidence_calibrated: float
    resolution_rule: str
    resolved_at: datetime | None
    outcome: Outcome | None

class Feedback(BaseModel):
    id: str
    implication_id: str
    action: FeedbackAction             # USEFUL | NOT_USEFUL | ACTED_ON | IGNORED
    note: str | None
    engagement_seconds: int | None
    created_at: datetime
```

### Data Retention

| Tier | What | Duration |
|---|---|---|
| Hot (Supabase) | Normalized events, signals, implications, world state | 30 days |
| Warm (Supabase) | Aggregated metrics, forecast outcomes, feedback | 180 days |
| Cold (compressed) | Raw payloads referenced by hash | Indefinite |

---

## Phase Roadmap (Gate-Based)

### Phase 0: Foundation + Replay Harness
**Est. 5-7 days**

- [ ] Create `signal-hunter` GitHub repo (fresh)
- [ ] Copy V1 source to `v1-reference/` (read-only porting reference)
- [ ] Export V1 database snapshot for replay testing
- [ ] Backend: FastAPI skeleton, `/health` confirming Supabase + Redis
- [ ] Database: Supabase project, V2 schema migration
- [ ] Frontend: Next.js + shadcn/ui skeleton, dark mode, placeholders
- [ ] Replay harness: feed V1 historical data through V2 pipeline
- [ ] CI: ruff, mypy, pytest, tsc + eslint

**Gate**: Health check passes. Replay harness runs end-to-end. V2 tables accept shadow writes.

### Phase 1: Sensor Grid + Crude Pipeline
**Est. 7-10 days**

- [ ] Port sensors: polymarket, kalshi, price_feed, news
- [ ] Event normalization → ObservedEvent → Supabase
- [ ] APScheduler: market-aware polling
- [ ] Crude pipeline: top signals by magnitude → Claude → dashboard
- [ ] API: `/api/briefing`, `/api/implications`
- [ ] Frontend: Briefing + crude implication feed
- [ ] V1 running in parallel as control

**Gate**: Dashboard shows live data. Claude summaries appear. V1 still running for comparison.

### Phase 2: Deterministic Scoring + Thesis Engine
**Est. 7-10 days**

- [ ] Port signal detectors as individual classes
- [ ] New detectors: cross_platform, basket_move, catalyst_proximity, lead_lag
- [ ] Composite scoring formula (5 factors)
- [ ] Novelty suppression
- [ ] Signal clustering by thesis/asset
- [ ] Deterministic state reducer (world model without LLM)
- [ ] Shadow comparison: V2 vs V1 daily
- [ ] Scenario tests: ceasefire, Fed cut, tariff, AI capex, oil shock, crypto regulation

**Gate**: V2 shadow beats V1 on replay OR failures are diagnosable and fixable.

### Phase 3: Curated Sources + Synthesis
**Est. 5-7 days**

- [ ] Source model (10-15 sources, tier/tag/reliability)
- [ ] Twitter sensor (TwitterAPI.io)
- [ ] YouTube sensor (RSS + transcripts)
- [ ] Haiku triage: categorize, extract claims
- [ ] Expert consensus detector
- [ ] Curated context fed into synthesis after threshold
- [ ] Source management UI

**Gate**: ≥70% of high-confidence implications have useful curated context. No context spam.

### Phase 4: Decision Cockpit
**Est. 7-10 days**

- [ ] Implication cards: 5-question format with falsifiers
- [ ] World model strip: deterministic fields + narration
- [ ] Thesis board: confidence, invalidation, catalysts
- [ ] Evidence drawer: card → signals → events → raw data
- [ ] Decision journal: feedback capture
- [ ] Briefing page: top 3 since last visit
- [ ] Real-time via Supabase
- [ ] Mobile responsive, polish

**Gate**: 10-second world update works. Every card has falsifiers + evidence chain.

### Phase 5: Evaluation + Alert Gating
**Est. 7-10 days**

- [ ] Forecast logging from implications
- [ ] Daily grading against outcomes
- [ ] Isotonic calibration
- [ ] Signal weight learning (ported from V1)
- [ ] Source reliability scoring
- [ ] Feedback: thumbs, acted/ignored, notes
- [ ] Push alert thresholds from measured performance
- [ ] Calibration + forecast dashboards

**Gate**:
- `precision@20` on high-urgency ≥ 60%
- Median push alerts ≤ 3/day
- ≥ 80% of cards intersect active thesis/watchlist
- 100% of cards have evidence chain + ≥1 falsifier
- Calibration error < 0.10 after 100 resolved forecasts

### Phase 6: Production Deploy
**Est. 3-5 days**

- [ ] Railway + Vercel deployment
- [ ] Supabase + Upstash production instances
- [ ] market-sentinel.com DNS
- [ ] Sentry error tracking
- [ ] V1 stays accessible until V2 has 30 stable days

**Gate**: Live on market-sentinel.com. Meets all Phase 5 quality gates in production.

### Phase 7: Unusual Whales Pilot (Gated)
**Prerequisites**: 30 stable days. 100+ resolved forecasts. Daily engagement.

- [ ] UW trial ($40/week)
- [ ] Implement UW sensor classes
- [ ] Shadow mode: scored but not surfaced
- [ ] 30-day A/B: ≥15% lift in lead time or precision?
- [ ] If yes → Standard tier, expand. If no → save $125/mo.

### Phase 8 (Future): Agentic Execution
Deliberately deferred until trust is earned through months of accurate implications.

---

## Risk Register

| Risk | Prob | Impact | Mitigation |
|---|---|---|---|
| Deterministic scoring misses nuance | Med | Med | Claude narration adds context. Scenario tests. Weight learning adapts. |
| Over-filtering (too few alerts) | Med | Med | Start conservative, loosen if <1/day. Monitor shadow signals. |
| Under-filtering (too many alerts) | Med | High | Alert budget is hard cap. Tighten + increase evidence family requirement. |
| Claude quality regresses | Low | High | Eval loop detects. Prompts are model-agnostic. |
| V1 → V2 port introduces bugs | Med | Med | Replay harness + scenario tests + V1 as control. |
| Prediction market data thin for some assets | Med | Med | Price feeds + curated sources compensate. Narrow universe. |
| UW pilot shows no lift | Med | Low | Save $125/mo. System works without it. |

---

## Success Metrics

| Milestone | Criteria |
|---|---|
| Foundation | Replay harness runs. Shadow writes stable. |
| Crude pipeline | Data flows. Claude summaries appear. |
| Signal detection | V2 shadow beats V1 or failures diagnosable. |
| Curated sources | 70%+ implications have useful context. |
| Decision cockpit | 10-second update. Falsifiers on every card. |
| Evaluation | Cal error < 0.10. Precision@20 ≥ 60%. ≤3 alerts/day. |
| Production | Live. 30 stable days. |
| UW pilot | ≥15% lift, or save $125/mo. |
| 3 months | ≥65% directional accuracy, high-confidence. |
| 6 months | ≥1 profitable decision attributed to Signal Hunter. |

---

## Long-Term North Star

1. **Now**: Evan curates, deterministic system scores, Claude explains, Evan decides.
2. **6 months**: Recommends with evidence. Evan approves/rejects. System learns.
3. **12 months**: Paper portfolio with guardrails. Evan sets strategy.
4. **24 months**: Multiple users. Each person's taste = unique intelligence layer.

What compounds across every rewrite:
- Evaluation history (what worked)
- Curation graph (which sources are high-signal)
- Signal weights (which detectors predict well)
- User feedback (taste, encoded as data)
- World state log (regime transitions, training data)

These are the assets. Everything else is infrastructure.
