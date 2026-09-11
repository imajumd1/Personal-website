# NOMAD Trigger Console — Scope Document

**Product:** NOMAD Trigger Console MVP  
**Version:** 0.1.0  
**Date:** August 27, 2026  
**Source:** [NOMAD Trigger Console MVP PRD](../uploads/NOMAD_Trigger_Console_MVP_PRD_b79f.pdf)

---

## 1. Scope Summary

This MVP delivers a **marketer-facing trigger authoring and test harness** for NOMAD's Next Best Action (NBA) decisioning engine. It proves that lifecycle marketers can view, create, and test event-driven triggers against Customer 360 golden records — without engineering involvement — and see real personalized message copy in a simulated outbox.

**In one sentence:** Replace "write a Jira ticket and wait" with "type a trigger, test it, see the message."

---

## 2. In Scope (MVP)

### 2.1 Data Foundation

| Item | Detail | Status |
|------|--------|--------|
| Golden Record Store | 100 seeded synthetic traveler profiles | ✅ Implemented |
| Field dictionary | Identity, behavioral, transactional, contextual, ML features | ✅ Implemented |
| Privacy | Hashed email, masked phone — no raw PII in UI | ✅ Implemented |
| Baseline triggers | 7 lifecycle triggers (TRG-101 through TRG-107) | ✅ Implemented |

### 2.2 Trigger Visibility (PRD Section 11.1)

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| A1 | Trigger Explorer lists all triggers with filters | Must | ✅ |
| A2 | Detail view: human-readable + structured conditions | Must | ✅ |
| A3 | Detail view: arbitration rules | Must | ✅ |
| A4 | Last tested timestamp and outcome | Should | ✅ |
| A5 | Status toggle (Draft / Active / Inactive) | Should | ✅ |

### 2.3 Dynamic Trigger Creation (PRD Section 11.2)

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| B1 | Free-text trigger description input | Must | ✅ |
| B2 | Parse into structured conditions + channel + NBA | Must | ✅ |
| B3 | Editable preview before save | Must | ✅ |
| B4 | Save as Draft until explicit Activate | Must | ✅ |
| B5 | Ambiguity flagging for unmapped terms | Should | ✅ |
| B6 | @ field autocomplete | Could | ✅ |

### 2.4 Trigger Testing (PRD Section 11.3)

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| C1 | Test action from Explorer and Detail | Must | ✅ |
| C2 | Profile picker + random qualifying profile | Must | ✅ |
| C3 | Pass/Fail with field-by-field breakdown | Must | ✅ |
| C4 | Arbitration engine runs on Pass | Must | ✅ |
| C5 | Generated SMS and/or Email copy | Must | ✅ |
| C6 | Result appended to Message Queue | Must | ✅ |
| C7 | Blocked entries with guardrail reason | Must | ✅ |
| C8 | Batch test against all 100 profiles | Should | ✅ |
| C9 | Queue persists for session | Should | ✅ |

### 2.5 Message Queue (PRD Section 11.4)

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| D1 | Clearly labeled simulation outbox | Must | ✅ |
| D2 | Filter by trigger, channel, profile | Should | ✅ |
| D3 | CSV export | Could | ⬜ Deferred |

### 2.6 Decisioning Engine (PRD Section 10)

| Rule | Description | Status |
|------|-------------|--------|
| Rule 1 | Operational > Commercial priority | ✅ |
| Rule 2 | Expected Value = Propensity × Offer Value | ✅ |
| Rule 3 | Frequency caps + quiet hours | ✅ |
| Rule 4 | Channel routing + SMS→Email fallback | ✅ |

### 2.7 Channels

| Channel | MVP Scope |
|---------|-----------|
| SMS | ✅ Simulated preview only |
| Email | ✅ Simulated preview only |
| In-app | ❌ Out of scope |
| Paid/Retargeting | ❌ Out of scope |

---

## 3. Out of Scope (MVP)

| Item | Rationale | Future Phase |
|------|-----------|--------------|
| Live SMS delivery (Twilio/Sinch) | Proof point, not production pipeline | Phase 2 |
| Live ESP integration | Same | Phase 2 |
| Real-time event streaming (Kafka/Kinesis) | Seeded batch data sufficient for MVP | Phase 1–3 |
| Production latency targets (<500ms) | Single-marketer console, not production scale | Phase 3 |
| In-app / push / paid channels | Email + SMS only for Phase 1 | Phase 4+ |
| Compliance approval workflow | Open question in PRD Section 16 | TBD |
| Trigger deletion | Deactivate instead (PRD A5) | — |
| Persistent database | In-memory store for session-based MVP | Phase 1 |
| LLM-backed parser (live API) | Pattern-based parser with LLM-ready interface | Phase 1 |
| CSV export from Message Queue | Could-have, deferred | Post-MVP |
| Role-based access control | Marketer role assumed | Phase 1 |

---

## 4. MVP Acceptance Criteria

From PRD Section 3.2 — verification checklist:

- [x] **100 golden records** seeded and browsable in the console
- [x] **7 baseline triggers** pre-loaded with accurate human-readable conditions
- [x] **Marketer can free-type** a new trigger, see parsed conditions, edit, and activate
- [x] **Test against any profile** returns Pass/Fail, channel (on Pass), and message copy in Queue within seconds
- [x] **Guardrail demo case** — quiet hours or frequency cap blocks message with reason surfaced

---

## 5. Technical Scope

### 5.1 Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript + Vite |
| Backend | Python 3 + FastAPI |
| Data | In-memory store (session persistence) |
| Styling | Custom CSS design system (dark console theme) |

### 5.2 API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check + counts |
| GET | `/api/triggers` | List triggers (filterable) |
| GET | `/api/triggers/{id}` | Trigger detail + arbitration rules |
| POST | `/api/triggers/parse` | NL → structured draft |
| POST | `/api/triggers` | Create trigger |
| PATCH | `/api/triggers/{id}` | Update trigger (status, fields) |
| POST | `/api/triggers/{id}/test` | Run single test |
| POST | `/api/triggers/{id}/test/batch` | Batch test all profiles |
| GET | `/api/triggers/{id}/qualifying` | Profiles matching conditions |
| GET | `/api/profiles` | List golden records |
| GET | `/api/queue` | Message queue entries |
| GET | `/api/fields` | Field dictionary for autocomplete |

### 5.3 Repository Structure

```
nomad-trigger-console/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI routes
│   │   ├── models.py        # Pydantic schemas
│   │   ├── seed.py          # 100 profiles + 7 triggers
│   │   ├── parser.py        # NL trigger parser
│   │   ├── evaluator.py     # Condition evaluation
│   │   ├── arbitration.py   # Decisioning rules
│   │   ├── content.py       # Message generation
│   │   └── store.py         # In-memory data store
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   └── src/
│       ├── pages/           # Explorer, Builder, Detail, Test, Queue
│       ├── api.ts           # API client
│       └── types.ts
├── design.md
├── scope.md
└── README.md
```

---

## 6. Roadmap Alignment (PRD Section 17)

| Phase | Scope | This MVP |
|-------|-------|----------|
| **MVP** | Trigger visibility, text authoring, click-to-test, simulated queue | ✅ This deliverable |
| Phase 1 | Real ingestion, identity resolution, consent center | Future |
| Phase 2 | Live ESP + SMS gateway sends | Future |
| Phase 3 | Production NFRs (streaming, <500ms, 50K events/sec) | Future |
| Phase 4+ | In-app, push, paid/retargeting channels | Future |

---

## 7. Known Limitations

1. **In-memory storage** — data resets on server restart
2. **Pattern-based parser** — handles PRD example phrases; complex NL may need LLM tuning
3. **Synthetic profiles** — not connected to real CDP/MDM
4. **Session-scoped queue** — no cross-session persistence
5. **No authentication** — single marketer role assumed

---

## 8. Success Metrics (Post-MVP, PRD Section 3.3)

These KPIs apply to production rollout, not this MVP:

- +15% ancillary attachment rate on single-component bookings
- Lift ARPT vs. control group
- Reduced SMS opt-out and email unsubscribe rates
- Incremental booking/attach conversion vs. control
