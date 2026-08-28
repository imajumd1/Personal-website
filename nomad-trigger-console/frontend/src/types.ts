export type TriggerStatus = 'Draft' | 'Active' | 'Inactive';
export type PriorityTier = 'Operational' | 'Commercial';
export type Channel = 'SMS' | 'Email' | 'SMS if opted in, else Email';
export type TestVerdict = 'Pass' | 'Fail' | 'Blocked';

export interface ConditionClause {
  field: string;
  operator: string;
  value: unknown;
  description: string;
}

export interface StructuredCondition {
  event: string;
  clauses: ConditionClause[];
  time_window?: string;
  logic: string;
}

export interface Trigger {
  trigger_id: string;
  name: string;
  lifecycle_phase: string;
  condition_human: string;
  condition_structured: StructuredCondition;
  priority_tier: PriorityTier;
  suggested_channel: Channel;
  nba_offer: string;
  status: TriggerStatus;
  created_by: string;
  last_modified: string;
  test_history: Array<{
    account_id: string;
    profile_first_name: string;
    verdict: string;
    timestamp: string;
  }>;
  offer_value: number;
}

export interface GoldenRecord {
  account_id: string;
  display_first_name: string;
  hashed_email: string;
  phone_masked: string;
  one_key_tier: string;
  one_key_cash_balance: number;
  travel_archetype: string;
  last_search_destination?: string;
  sms_opt_in_ts?: string;
  email_subscription_status: string;
  flight_status: string;
  delay_minutes: number;
  cart_abandon_flag: boolean;
  landed_flag: boolean;
  days_to_departure?: number;
  channel_affinity_score_sms: number;
  channel_affinity_score_email: number;
  clv_score: number;
  in_quiet_hours: boolean;
}

export interface FieldEvaluation {
  field: string;
  expected: string;
  actual: string;
  passed: boolean;
}

export interface TestResult {
  id: string;
  trigger_id: string;
  trigger_name: string;
  account_id: string;
  profile_first_name: string;
  verdict: TestVerdict;
  field_evaluations: FieldEvaluation[];
  selected_channel?: string;
  channel_reason?: string;
  block_reason?: string;
  sms_body?: string;
  email_subject?: string;
  email_body?: string;
  explanation: string;
  timestamp: string;
}

export interface ParsedDraft {
  name: string;
  lifecycle_phase: string;
  condition_human: string;
  condition_structured: StructuredCondition;
  priority_tier: PriorityTier;
  suggested_channel: Channel;
  nba_offer: string;
  ambiguities: string[];
  confidence: number;
}

export interface FieldDef {
  field: string;
  type: string;
  description: string;
}

export interface ArbitrationRules {
  priority_tier: string;
  priority_rule: string;
  frequency_cap_bucket: string;
  expected_value_formula: string;
  channel_routing: string;
  offer_value: number;
}

export interface BatchSummary {
  trigger_id: string;
  pass_count: number;
  fail_count: number;
  blocked_count: number;
  results: TestResult[];
}
