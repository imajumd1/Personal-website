"""In-memory data store for MVP session persistence."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from .arbitration import check_guardrails, get_arbitration_rules, select_channel
from .content import generate_email, generate_sms
from .evaluator import evaluate_condition, find_qualifying_profiles
from .models import (
    BatchTestSummary,
    GoldenRecord,
    TestResult,
    TestVerdict,
    TriggerDefinition,
    TriggerStatus,
)
from .parser import ParsedTriggerDraft
from .seed import generate_golden_records, get_baseline_triggers


class Store:
    def __init__(self) -> None:
        self.profiles: dict[str, GoldenRecord] = {}
        self.triggers: dict[str, TriggerDefinition] = {}
        self.message_queue: list[TestResult] = []
        self._next_trigger_num = 200

    def initialize(self) -> None:
        for record in generate_golden_records(100):
            self.profiles[record.account_id] = record
        for trigger in get_baseline_triggers():
            self.triggers[trigger.trigger_id] = trigger

    def list_profiles(
        self,
        tier: Optional[str] = None,
        archetype: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[GoldenRecord]:
        results = list(self.profiles.values())
        if tier:
            results = [r for r in results if r.one_key_tier == tier]
        if archetype:
            results = [r for r in results if r.travel_archetype == archetype]
        if search:
            q = search.lower()
            results = [
                r for r in results
                if q in r.display_first_name.lower()
                or q in r.account_id[:8].lower()
                or q in (r.last_search_destination or "").lower()
            ]
        return results

    def get_profile(self, account_id: str) -> Optional[GoldenRecord]:
        return self.profiles.get(account_id)

    def list_triggers(
        self,
        status: Optional[str] = None,
        channel: Optional[str] = None,
        lifecycle: Optional[str] = None,
    ) -> list[TriggerDefinition]:
        results = list(self.triggers.values())
        if status:
            results = [t for t in results if t.status.value == status]
        if channel:
            results = [t for t in results if channel.lower() in t.suggested_channel.value.lower()]
        if lifecycle:
            results = [t for t in results if lifecycle.lower() in t.lifecycle_phase.lower()]
        return sorted(results, key=lambda t: t.trigger_id)

    def get_trigger(self, trigger_id: str) -> Optional[TriggerDefinition]:
        return self.triggers.get(trigger_id)

    def create_trigger(self, draft: ParsedTriggerDraft, activate: bool = False) -> TriggerDefinition:
        self._next_trigger_num += 1
        trigger_id = f"TRG-{self._next_trigger_num}"
        trigger = TriggerDefinition(
            trigger_id=trigger_id,
            name=draft.name,
            lifecycle_phase=draft.lifecycle_phase,
            condition_human=draft.condition_human,
            condition_structured=draft.condition_structured,
            priority_tier=draft.priority_tier,
            suggested_channel=draft.suggested_channel,
            nba_offer=draft.nba_offer,
            status=TriggerStatus.ACTIVE if activate else TriggerStatus.DRAFT,
            created_by="Marketer",
            last_modified=datetime.utcnow(),
        )
        self.triggers[trigger_id] = trigger
        return trigger

    def update_trigger(self, trigger_id: str, updates: dict) -> Optional[TriggerDefinition]:
        trigger = self.triggers.get(trigger_id)
        if not trigger:
            return None
        data = trigger.model_dump()
        data.update(updates)
        data["last_modified"] = datetime.utcnow()
        updated = TriggerDefinition(**data)
        self.triggers[trigger_id] = updated
        return updated

    def run_test(self, trigger_id: str, account_id: str) -> Optional[TestResult]:
        trigger = self.triggers.get(trigger_id)
        record = self.profiles.get(account_id)
        if not trigger or not record:
            return None

        passed, evaluations = evaluate_condition(record, trigger)
        result_id = str(uuid.uuid4())[:8]

        if not passed:
            result = TestResult(
                id=result_id,
                trigger_id=trigger_id,
                trigger_name=trigger.name,
                account_id=account_id,
                profile_first_name=record.display_first_name,
                verdict=TestVerdict.FAIL,
                field_evaluations=evaluations,
                explanation="Trigger conditions not met for this profile.",
            )
        else:
            channel, channel_reason = select_channel(record, trigger)
            allowed, block_reason = check_guardrails(record, trigger, channel)

            if not allowed:
                # Try email fallback if SMS blocked
                if channel == "SMS" and record.email_subscription_status == "Subscribed":
                    channel = "Email"
                    allowed, block_reason = check_guardrails(record, trigger, channel)
                    if allowed:
                        channel_reason = f"SMS blocked ({block_reason}); Email fallback attempted"

            if not allowed:
                result = TestResult(
                    id=result_id,
                    trigger_id=trigger_id,
                    trigger_name=trigger.name,
                    account_id=account_id,
                    profile_first_name=record.display_first_name,
                    verdict=TestVerdict.BLOCKED,
                    field_evaluations=evaluations,
                    block_reason=block_reason,
                    explanation=f"Guardrail blocked: {block_reason}",
                )
            else:
                sms_body = generate_sms(record, trigger) if channel == "SMS" else None
                email_subject, email_body = (None, None)
                if channel == "Email":
                    email_subject, email_body = generate_email(record, trigger)

                result = TestResult(
                    id=result_id,
                    trigger_id=trigger_id,
                    trigger_name=trigger.name,
                    account_id=account_id,
                    profile_first_name=record.display_first_name,
                    verdict=TestVerdict.PASS,
                    field_evaluations=evaluations,
                    selected_channel=channel,
                    channel_reason=channel_reason,
                    sms_body=sms_body,
                    email_subject=email_subject,
                    email_body=email_body,
                    explanation=f"{channel} selected: {channel_reason}",
                )

        self.message_queue.insert(0, result)

        history_entry = {
            "account_id": account_id,
            "profile_first_name": record.display_first_name,
            "verdict": result.verdict.value,
            "timestamp": result.timestamp.isoformat(),
        }
        trigger.test_history.insert(0, history_entry)
        trigger.test_history = trigger.test_history[:20]
        self.triggers[trigger_id] = trigger

        return result

    def run_batch_test(self, trigger_id: str) -> Optional[BatchTestSummary]:
        trigger = self.triggers.get(trigger_id)
        if not trigger:
            return None

        results: list[TestResult] = []
        pass_count = fail_count = blocked_count = 0

        for record in self.profiles.values():
            passed, evaluations = evaluate_condition(record, trigger)
            if not passed:
                fail_count += 1
                continue

            channel, channel_reason = select_channel(record, trigger)
            allowed, block_reason = check_guardrails(record, trigger, channel)

            if not allowed and channel == "SMS":
                channel = "Email"
                allowed, block_reason = check_guardrails(record, trigger, channel)

            if not allowed:
                blocked_count += 1
                results.append(
                    TestResult(
                        id=str(uuid.uuid4())[:8],
                        trigger_id=trigger_id,
                        trigger_name=trigger.name,
                        account_id=record.account_id,
                        profile_first_name=record.display_first_name,
                        verdict=TestVerdict.BLOCKED,
                        field_evaluations=evaluations,
                        block_reason=block_reason,
                        explanation=f"Guardrail blocked: {block_reason}",
                    )
                )
            else:
                pass_count += 1
                sms_body = generate_sms(record, trigger) if channel == "SMS" else None
                email_subject, email_body = (None, None)
                if channel == "Email":
                    email_subject, email_body = generate_email(record, trigger)

                results.append(
                    TestResult(
                        id=str(uuid.uuid4())[:8],
                        trigger_id=trigger_id,
                        trigger_name=trigger.name,
                        account_id=record.account_id,
                        profile_first_name=record.display_first_name,
                        verdict=TestVerdict.PASS,
                        field_evaluations=evaluations,
                        selected_channel=channel,
                        channel_reason=channel_reason,
                        sms_body=sms_body,
                        email_subject=email_subject,
                        email_body=email_body,
                        explanation=f"{channel} selected: {channel_reason}",
                    )
                )

        return BatchTestSummary(
            trigger_id=trigger_id,
            pass_count=pass_count,
            fail_count=fail_count,
            blocked_count=blocked_count,
            results=results,
        )

    def get_queue(
        self,
        trigger_id: Optional[str] = None,
        channel: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> list[TestResult]:
        results = self.message_queue
        if trigger_id:
            results = [r for r in results if r.trigger_id == trigger_id]
        if channel:
            results = [r for r in results if r.selected_channel == channel or (channel == "Blocked" and r.verdict == TestVerdict.BLOCKED)]
        if account_id:
            results = [r for r in results if r.account_id == account_id]
        return results


store = Store()
