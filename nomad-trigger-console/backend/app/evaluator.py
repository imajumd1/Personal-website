"""Evaluate trigger conditions against golden records."""

from __future__ import annotations

from typing import Any

from .models import FieldEvaluation, GoldenRecord, StructuredCondition, TriggerDefinition


def _get_field(record: GoldenRecord, field: str) -> Any:
    return getattr(record, field, None)


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "==":
        return actual == expected
    if operator == "!=":
        return actual != expected
    if operator == ">":
        return actual is not None and actual > expected
    if operator == ">=":
        return actual is not None and actual >= expected
    if operator == "<":
        return actual is not None and actual < expected
    if operator == "<=":
        return actual is not None and actual <= expected
    if operator == "in":
        if isinstance(expected, list):
            return actual in expected
        return actual == expected
    return False


def evaluate_condition(record: GoldenRecord, trigger: TriggerDefinition) -> tuple[bool, list[FieldEvaluation]]:
    structured = trigger.condition_structured
    evaluations: list[FieldEvaluation] = []
    results: list[bool] = []

    for clause in structured.clauses:
        actual = _get_field(record, clause.field)
        passed = _compare(actual, clause.operator, clause.value)
        results.append(passed)
        evaluations.append(
            FieldEvaluation(
                field=clause.field,
                expected=f"{clause.operator} {clause.value}",
                actual=str(actual),
                passed=passed,
            )
        )

    if not results:
        return False, evaluations

    passed_all = all(results) if structured.logic == "AND" else any(results)
    return passed_all, evaluations


def find_qualifying_profiles(
    records: list[GoldenRecord], trigger: TriggerDefinition
) -> list[GoldenRecord]:
    qualifying = []
    for record in records:
        passed, _ = evaluate_condition(record, trigger)
        if passed:
            qualifying.append(record)
    return qualifying
