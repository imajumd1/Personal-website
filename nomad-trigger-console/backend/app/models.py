from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TriggerStatus(str, Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class PriorityTier(str, Enum):
    OPERATIONAL = "Operational"
    COMMERCIAL = "Commercial"


class Channel(str, Enum):
    SMS = "SMS"
    EMAIL = "Email"
    SMS_OR_EMAIL = "SMS if opted in, else Email"


class ConditionClause(BaseModel):
    field: str
    operator: str
    value: Any
    description: str = ""


class StructuredCondition(BaseModel):
    event: str = ""
    clauses: list[ConditionClause] = Field(default_factory=list)
    time_window: Optional[str] = None
    logic: str = "AND"


class TriggerDefinition(BaseModel):
    trigger_id: str
    name: str
    lifecycle_phase: str
    condition_human: str
    condition_structured: StructuredCondition
    priority_tier: PriorityTier
    suggested_channel: Channel
    nba_offer: str
    status: TriggerStatus = TriggerStatus.ACTIVE
    created_by: str = "Seed"
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    test_history: list[dict] = Field(default_factory=list)
    offer_value: float = 50.0


class GoldenRecord(BaseModel):
    account_id: str
    display_first_name: str
    hashed_email: str
    phone_masked: str
    home_country: str = "US"
    home_market_currency: str = "USD"
    one_key_tier: str
    one_key_cash_balance: float = 0.0
    preferred_home_airport: str = "SFO"
    sms_opt_in_ts: Optional[str] = None
    email_subscription_status: str = "Subscribed"
    quiet_hours_window: str = "21:00–08:00"
    quiet_hours_timezone: str = "America/Los_Angeles"
    last_search_origin: Optional[str] = None
    last_search_destination: Optional[str] = None
    last_search_dates: Optional[str] = None
    property_detail_views_7d: int = 0
    searches_same_destination_24h: int = 0
    cart_abandon_flag: bool = False
    cart_abandon_component: Optional[str] = None
    price_sensitivity_tier: str = "Value"
    travel_archetype: str = "Family Vacationer"
    favorite_destinations: list[str] = Field(default_factory=list)
    active_booking_id: Optional[str] = None
    booking_status: str = "None"
    component_types_booked: list[str] = Field(default_factory=list)
    total_booking_value: float = 0.0
    days_to_departure: Optional[int] = None
    flight_status: str = "On Time"
    delay_minutes: int = 0
    landed_flag: bool = False
    at_airport_flag: bool = False
    destination_city: Optional[str] = None
    hours_since_return: Optional[int] = None
    channel_affinity_score_sms: float = 0.5
    channel_affinity_score_email: float = 0.5
    propensity_insurance_purchase: float = 0.3
    propensity_room_upgrade: float = 0.3
    propensity_ground_transport: float = 0.3
    clv_score: int = 50
    clv_tier: str = "Silver"
    predictive_personalization_opt_in: bool = True
    local_time_at_location: str = ""
    sms_sent_promotional_72h: int = 0
    sms_sent_total_24h: int = 0
    email_sent_marketing_24h: int = 0
    in_quiet_hours: bool = False


class ParsedTriggerDraft(BaseModel):
    name: str
    lifecycle_phase: str
    condition_human: str
    condition_structured: StructuredCondition
    priority_tier: PriorityTier
    suggested_channel: Channel
    nba_offer: str
    ambiguities: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class FieldEvaluation(BaseModel):
    field: str
    expected: str
    actual: str
    passed: bool


class TestVerdict(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"
    BLOCKED = "Blocked"


class TestResult(BaseModel):
    id: str
    trigger_id: str
    trigger_name: str
    account_id: str
    profile_first_name: str
    verdict: TestVerdict
    field_evaluations: list[FieldEvaluation] = Field(default_factory=list)
    selected_channel: Optional[str] = None
    channel_reason: Optional[str] = None
    block_reason: Optional[str] = None
    sms_body: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    explanation: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BatchTestSummary(BaseModel):
    trigger_id: str
    pass_count: int
    fail_count: int
    blocked_count: int
    results: list[TestResult]
