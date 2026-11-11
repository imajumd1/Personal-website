# NOMAD Trigger Console — MVP

A marketer-facing **Next Best Action (NBA) trigger authoring and test harness** for the NOMAD Customer Comms Platform. View lifecycle triggers, create new ones in plain language, test them against 100 seeded traveler profiles, and preview personalized SMS/Email copy in a simulated Message Queue — no live sends.

Built from the [NOMAD Trigger Console MVP PRD](../uploads/NOMAD_Trigger_Console_MVP_PRD_b79f.pdf).

## What It Does

| Capability | Description |
|------------|-------------|
| **Trigger Explorer** | Browse 7 seeded lifecycle triggers + marketer-authored ones; filter by status, channel, lifecycle phase |
| **Trigger Builder** | Type a trigger in plain English → parsed structured conditions → save as Draft or Activate |
| **Test / Simulate** | Run any trigger against any of 100 golden records; see Pass/Fail/Blocked, channel selection, and message preview |
| **Message Queue** | Simulated outbox showing every test result with explainability and guardrail block reasons |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### 1. Start the backend

```bash
cd nomad-trigger-console/backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

API runs at **http://localhost:8000** — verify with `GET /api/health`.

### 2. Start the frontend

```bash
cd nomad-trigger-console/frontend
npm install
npm run dev
```

Console opens at **http://localhost:5173** (proxies `/api` to the backend).

## Demo Walkthrough

### 1. Explore seeded triggers

Open the **Trigger Explorer**. You'll see 7 baseline triggers (TRG-101 through TRG-107) spanning inspiration, abandonment, pre-trip, disruption, arrival, and post-trip lifecycle phases.

### 2. Test a trigger

1. Click **Test** on **TRG-105** (Flight Delay — Lounge Access)
2. Select **Priya** (Gold tier) or click **Random qualifying**
3. See **Pass** → SMS selected → lounge-access message preview
4. Check the **Message Queue** for the queued result

### 3. See a guardrail block

1. Test **TRG-104** (24-Hour Pre-Departure) against **Marcus** (in quiet hours, email unsubscribed)
2. See **Blocked** with reason: *"Quiet hours: Marketing SMS blocked during 21:00–08:00"*
3. Or test **TRG-102** against **Elena** for frequency cap block

### 4. Create a new trigger

1. Go to **New Trigger**
2. Type: *"When a Gold or Platinum member's flight is delayed more than 60 minutes, text them a lounge-access offer"*
3. Click **Parse Trigger** → review structured conditions
4. **Save as Draft** or **Activate**

### 5. Batch test

From any trigger's Test panel, click **Test all 100 profiles** for Pass/Fail/Blocked counts.

## Architecture

```
React Console  →  FastAPI Backend  →  In-Memory Store
                      ├── NL Parser (pattern-based)
                      ├── Condition Evaluator
                      ├── Arbitration Engine (Section 10 rules)
                      └── Content Personalization Engine
```

See [design.md](./design.md) for full UI/UX specifications and [scope.md](./scope.md) for in/out-of-scope details.

## Seeded Data

- **100 golden records** — synthetic traveler profiles with identity, loyalty, behavioral, transactional, contextual, and ML fields
- **7 baseline triggers** — TRG-101 (search repetition) through TRG-107 (post-trip review)
- **3 curated demo profiles** — Priya (search match), quiet-hours block, frequency-cap block

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health + profile/trigger counts |
| `/api/triggers` | GET | List triggers (filter: status, channel, lifecycle) |
| `/api/triggers/{id}` | GET | Trigger detail + arbitration rules |
| `/api/triggers/parse` | POST | Parse NL text → structured draft |
| `/api/triggers` | POST | Create trigger from draft |
| `/api/triggers/{id}/test?account_id=` | POST | Run single test |
| `/api/triggers/{id}/test/batch` | POST | Batch test all 100 profiles |
| `/api/profiles` | GET | List golden records |
| `/api/queue` | GET | Message queue entries |

## Decisioning Rules

| Rule | Behavior |
|------|----------|
| Priority | Operational triggers outrank Commercial |
| Expected Value | Propensity × Offer Value ranks competing commercial offers |
| Frequency Caps | SMS promo 1/72h, SMS total 3/24h, Email 1/24h |
| Quiet Hours | No marketing SMS 21:00–08:00 local time |
| Channel Routing | Urgency → SMS; complexity → Email; affinity tiebreak; SMS→Email fallback |

## Privacy

- No raw email or phone numbers in the UI
- Profiles use hashed email identifiers and masked phone numbers
- Email previews include CAN-SPAM unsubscribe footer

## Limitations (MVP)

- **Simulation only** — no live SMS or email delivery
- **In-memory store** — data resets on server restart
- **Pattern-based parser** — handles common phrases; LLM integration ready for Phase 1
- **No authentication** — single marketer role assumed

## Documentation

| Document | Purpose |
|----------|---------|
| [design.md](./design.md) | UI/UX specs, visual system, architecture diagrams |
| [scope.md](./scope.md) | In/out of scope, acceptance criteria, roadmap alignment |
| [README.md](./README.md) | This file — setup and demo guide |

## License

Internal NOMAD Customer Comms Platform — MVP proof of concept.
