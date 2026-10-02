# NOMAD Trigger Console — Design Document

**Product:** NOMAD Trigger Console MVP  
**Version:** 0.1.0  
**Date:** August 27, 2026  
**Status:** MVP Implementation

---

## 1. Design Philosophy

The Trigger Console is a **marketer-facing decisioning proof point**, not a production send pipeline. Every design choice prioritizes:

1. **Explainability** — marketers must see *why* a trigger fires, *why* a channel was chosen, and *why* a message was blocked.
2. **Trust before activation** — no trigger goes live without a visible, editable parsed condition and a successful test run.
3. **Simulation safety** — the Message Queue is clearly labeled as a simulated outbox; no live SMS or email delivery occurs in MVP.

The visual language follows a **dark console aesthetic** suited to extended review sessions, with color-coded badges for verdicts, channels, and priority tiers.

---

## 2. Information Architecture

```
NOMAD Trigger Console
├── Trigger Explorer (landing)
│   ├── Filterable trigger catalog
│   ├── Row actions: Detail | Test
│   └── + New Trigger CTA
├── Trigger Builder
│   ├── Free-text input with @ field autocomplete
│   ├── Parsed structured preview (editable)
│   └── Save as Draft | Activate
├── Trigger Detail
│   ├── Plain-English + structured conditions
│   ├── Arbitration rules panel
│   ├── Status toggle (Draft / Active / Inactive)
│   └── Test history
├── Test / Simulate Panel
│   ├── Profile picker (search, tier filter)
│   ├── Random qualifying profile
│   ├── Single-test results (Pass / Fail / Blocked)
│   ├── SMS bubble + Email preview
│   └── Batch test (all 100 profiles)
└── Message Queue (simulated outbox)
    ├── Chronological test results
    ├── Filters by trigger, channel
    └── Expandable message previews
```

---

## 3. Screen Specifications

### 3.1 Trigger Explorer

| Element | Behavior |
|---------|----------|
| Trigger table | One row per trigger; columns: ID, Name, Lifecycle, Condition summary, Channel, Priority, Status |
| Filters | Status, Channel, Lifecycle phase |
| Sort | Default by trigger ID |
| Actions | Detail → Trigger Detail; Test → Test Panel |

**Acceptance:** All 7 seeded triggers visible on load with accurate plain-English conditions (PRD A1).

### 3.2 Trigger Builder

| Element | Behavior |
|---------|----------|
| Text area | Free-form natural language input |
| @ autocomplete | Surfaces golden-record field dictionary (PRD B6 — Could, implemented) |
| Parse button | Calls NL parser; shows structured preview |
| Ambiguity warnings | Flags unmapped terms; blocks Activate until resolved |
| Save | Draft (default) or Activate (explicit) |

**Example input:** *"When a Gold or Platinum member's flight is delayed more than 60 minutes, text them a lounge-access offer"*

**Parsed output:**
- Lifecycle: Day of Travel (Disruption)
- Conditions: `one_key_tier in [Gold, Platinum]`, `delay_minutes > 60`, `flight_status == Delayed`
- Priority: Operational
- Channel: SMS
- NBA: Instant lounge-access pass

### 3.3 Trigger Detail

| Element | Behavior |
|---------|----------|
| Condition display | Human-readable sentence + structured field/operator/threshold list |
| Arbitration rules | Priority tier, frequency cap bucket, EV formula, channel routing |
| Status toggle | Draft ↔ Active ↔ Inactive without deletion |
| Test history | Last 10 runs with profile, verdict, timestamp |

### 3.4 Test / Simulate Panel

| Element | Behavior |
|---------|----------|
| Profile picker | Searchable list of 100 golden records; tier filter |
| Random qualifying | Picks a profile that passes trigger conditions |
| Single test | Pass/Fail/Blocked verdict with field-by-field breakdown |
| Channel selection | Shows chosen channel + one-line reason |
| Message preview | SMS bubble or Email subject/body with merge fields |
| Batch test | Pass / Fail / Blocked counts across all 100 profiles |

### 3.5 Message Queue

| Element | Behavior |
|---------|----------|
| Simulation banner | Persistent "SIMULATION ONLY" notice (PRD D1) |
| Entry feed | Timestamp, trigger, profile (first name + masked ID), verdict, channel, preview, explanation |
| Blocked entries | Shows specific guardrail reason (quiet hours, frequency cap, consent) |
| Filters | By trigger ID, channel |

---

## 4. Visual Design System

### 4.1 Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `--bg` | `#0f1419` | Page background |
| `--surface` | `#1a2332` | Cards, sidebar |
| `--accent` | `#3b82f6` | Primary actions, links |
| `--success` | `#22c55e` | Pass verdict, Active status |
| `--warning` | `#f59e0b` | Blocked verdict, simulation banner |
| `--danger` | `#ef4444` | Fail verdict, Inactive status |
| `--operational` | `#f97316` | Operational priority tier |
| `--commercial` | `#8b5cf6` | Commercial priority tier |
| `--sms` | `#06b6d4` | SMS channel badge |
| `--email` | `#a78bfa` | Email channel badge |

### 4.2 Typography

- **Font:** Inter (Google Fonts), system-ui fallback
- **Headings:** 600 weight, negative letter-spacing
- **Body:** 0.875rem (14px) base
- **Labels:** 0.75rem uppercase with letter-spacing

### 4.3 Components

| Component | Description |
|-----------|-------------|
| Badge | Pill-shaped status/channel/priority indicator |
| SMS Preview | Dark rounded bubble mimicking iOS message |
| Email Preview | White card with subject line and CAN-SPAM footer |
| Clause List | Left-accent-bordered condition blocks |
| Stat Card | Pass/Fail/Blocked count for batch tests |
| Profile Picker | Scrollable selectable list with tier metadata |

---

## 5. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  React Frontend (Vite)                   │
│  Explorer │ Builder │ Detail │ Test Panel │ Queue       │
└────────────────────────┬────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐│
│  │  Parser  │ │Evaluator │ │Arbitration│ │  Content  ││
│  └──────────┘ └──────────┘ └───────────┘ └───────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │              In-Memory Store (MVP)                   ││
│  │  100 Golden Records │ Triggers │ Message Queue       ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘

Phase 2+ (not built): Kafka/Kinesis ingestion, ESP, SMS gateway
```

### 5.1 Backend Services

| Service | Responsibility |
|---------|----------------|
| **Seed** | Generates 100 synthetic golden records + 7 baseline triggers |
| **Parser** | NL → structured conditions (pattern-based; LLM-ready interface) |
| **Evaluator** | Field-by-field condition matching against profiles |
| **Arbitration** | Priority matrix, guardrails, channel routing (Section 10 rules) |
| **Content** | Personalized SMS/Email copy with merge fields |

### 5.2 Data Flow — Test Click

```
Marketer clicks Test
    → Evaluator: condition match? → Pass/Fail
    → Arbitration: channel selection + guardrail check
    → Content: generate SMS/Email copy
    → Message Queue: append result with explanation
    → Trigger: update test_history
```

---

## 6. Decisioning Rules (Implemented)

| Rule | Implementation |
|------|----------------|
| **Rule 1 — Priority Matrix** | Operational > Commercial; not configurable by marketer |
| **Rule 2 — Expected Value** | `Propensity × Offer Value` for competing commercial triggers |
| **Rule 3 — Frequency Caps** | SMS promo 1/72h, SMS total 3/24h, Email 1/24h, Quiet hours 21:00–08:00 |
| **Rule 4 — Channel Routing** | Urgency → SMS; complexity → Email; affinity tiebreak; SMS→Email fallback |

---

## 7. Privacy & Compliance (UI)

- **No raw PII** in console — only `display_first_name`, masked phone, hashed email
- **Blocked state** surfaces TCPA, CAN-SPAM, and quiet-hours reasons explicitly
- **Email previews** include unsubscribe affordance and sender identity (CAN-SPAM)
- **Simulation banner** on every queue view

---

## 8. Demo Profiles (Curated)

| Profile | Purpose |
|---------|---------|
| **Priya (Gold)** | Matches TRG-101 search repetition; high SMS affinity |
| **Marcus** | Quiet hours demo — TRG-104 blocked (commercial SMS during quiet hours, email unsubscribed) |
| **Elena** | Frequency cap demo — TRG-102 blocked (promotional SMS cap, email unsubscribed) |

---

## 9. Future Design Considerations

| Phase | Design Impact |
|-------|---------------|
| Phase 1 | Real ingestion indicators, live profile refresh |
| Phase 2 | Send status tracking, delivery confirmation |
| Phase 3 | Performance dashboards, latency metrics |
| Phase 4+ | In-app/push channel previews, multi-channel arbitration UI |
