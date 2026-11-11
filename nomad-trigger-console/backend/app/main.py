"""NOMAD Trigger Console — FastAPI backend."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .arbitration import get_arbitration_rules
from .models import Channel, ParsedTriggerDraft, PriorityTier, StructuredCondition, TriggerStatus
from .parser import get_field_dictionary, parse_trigger_text
from .store import store

app = FastAPI(title="NOMAD Trigger Console", version="0.1.0-mvp")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    store.initialize()


# --- Profiles ---

@app.get("/api/profiles")
def list_profiles(
    tier: Optional[str] = None,
    archetype: Optional[str] = None,
    search: Optional[str] = None,
):
    profiles = store.list_profiles(tier=tier, archetype=archetype, search=search)
    return {"count": len(profiles), "profiles": profiles}


@app.get("/api/profiles/{account_id}")
def get_profile(account_id: str):
    profile = store.get_profile(account_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile


# --- Triggers ---

@app.get("/api/triggers")
def list_triggers(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    lifecycle: Optional[str] = None,
):
    triggers = store.list_triggers(status=status, channel=channel, lifecycle=lifecycle)
    return {"count": len(triggers), "triggers": triggers}


@app.get("/api/triggers/{trigger_id}")
def get_trigger(trigger_id: str):
    trigger = store.get_trigger(trigger_id)
    if not trigger:
        raise HTTPException(404, "Trigger not found")
    rules = get_arbitration_rules(trigger)
    last_tested = trigger.test_history[0] if trigger.test_history else None
    return {"trigger": trigger, "arbitration_rules": rules, "last_tested": last_tested}


class TriggerUpdate(BaseModel):
    name: Optional[str] = None
    lifecycle_phase: Optional[str] = None
    condition_human: Optional[str] = None
    condition_structured: Optional[StructuredCondition] = None
    priority_tier: Optional[PriorityTier] = None
    suggested_channel: Optional[Channel] = None
    nba_offer: Optional[str] = None
    status: Optional[TriggerStatus] = None


@app.patch("/api/triggers/{trigger_id}")
def update_trigger(trigger_id: str, body: TriggerUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    trigger = store.update_trigger(trigger_id, updates)
    if not trigger:
        raise HTTPException(404, "Trigger not found")
    return trigger


class ParseRequest(BaseModel):
    text: str


@app.post("/api/triggers/parse")
def parse_trigger(body: ParseRequest) -> ParsedTriggerDraft:
    return parse_trigger_text(body.text)


class CreateTriggerRequest(BaseModel):
    draft: ParsedTriggerDraft
    activate: bool = False


@app.post("/api/triggers")
def create_trigger(body: CreateTriggerRequest):
    trigger = store.create_trigger(body.draft, activate=body.activate)
    return trigger


@app.get("/api/fields")
def list_fields():
    return {"fields": get_field_dictionary()}


# --- Testing ---

@app.post("/api/triggers/{trigger_id}/test")
def test_trigger(trigger_id: str, account_id: str):
    result = store.run_test(trigger_id, account_id)
    if not result:
        raise HTTPException(404, "Trigger or profile not found")
    return result


@app.post("/api/triggers/{trigger_id}/test/batch")
def batch_test_trigger(trigger_id: str):
    summary = store.run_batch_test(trigger_id)
    if not summary:
        raise HTTPException(404, "Trigger not found")
    return summary


@app.get("/api/triggers/{trigger_id}/qualifying")
def qualifying_profiles(trigger_id: str):
    trigger = store.get_trigger(trigger_id)
    if not trigger:
        raise HTTPException(404, "Trigger not found")
    from .evaluator import find_qualifying_profiles
    profiles = find_qualifying_profiles(list(store.profiles.values()), trigger)
    return {"count": len(profiles), "profiles": profiles}


# --- Message Queue ---

@app.get("/api/queue")
def get_queue(
    trigger_id: Optional[str] = None,
    channel: Optional[str] = None,
    account_id: Optional[str] = None,
):
    entries = store.get_queue(trigger_id=trigger_id, channel=channel, account_id=account_id)
    return {
        "simulation_notice": "SIMULATION ONLY — No messages are sent to real customers.",
        "count": len(entries),
        "entries": entries,
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "profiles": len(store.profiles),
        "triggers": len(store.triggers),
        "queue_size": len(store.message_queue),
        "timestamp": datetime.utcnow().isoformat(),
    }
