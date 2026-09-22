"""Submission-time v3 and v19 task routing and final-cell ownership."""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Sequence

from .decisions.v3_basis_reducer_v2 import decide_v3_basis_v2
from .decisions.v3_keyed_serialization import adapt_keyed_response, build_v3_keyed_task
from .decisions.v19_quote_resolution_v2 import (
    parse_v19_observations_relaxed_quote,
    reduce_v19_with_quote_resolution,
)
from .decisions.v19_requirements import build_v19_task
from .views.v3_monetary import build_v3_monetary_view
from .views.v19_requirements import build_v19_requirement_view


def build_specialist_tasks(
    records: Sequence[Mapping[str, Any]],
    count_tokens: Callable[[Sequence[Mapping[str, str]]], int] | None = None,
    prompt_budget: int = 14848,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    views: dict[str, dict[str, Any]] = {}
    tasks: dict[str, dict[str, Any]] = {}
    routing: dict[str, dict[str, Any]] = {}
    for record in records:
        notice_id = str(record["id"])
        v3_view = build_v3_monetary_view(record)
        v19_view = build_v19_requirement_view(record)
        views[notice_id] = {"v3": v3_view, "v19": v19_view}
        v3_ids: list[str] = []
        v19_ids: list[str] = []
        if v3_view["candidates"]:
            task_id = f"V3/{notice_id}"
            task = build_v3_keyed_task(record, v3_view)
            if count_tokens is None or count_tokens(task["messages"]) <= prompt_budget:
                tasks[task_id] = task
                v3_ids.append(task_id)
        if v19_view["candidates"]:
            current = []
            packs = []
            overflow = False
            for candidate in v19_view["candidates"]:
                trial = tuple([*current, candidate])
                task = build_v19_task(record, trial)
                if count_tokens is None or count_tokens(task["messages"]) <= prompt_budget:
                    current.append(candidate)
                    continue
                if not current:
                    overflow = True
                    break
                packs.append(tuple(current))
                current = [candidate]
                single = build_v19_task(record, tuple(current))
                if count_tokens is not None and count_tokens(single["messages"]) > prompt_budget:
                    overflow = True
                    break
            if current and not overflow:
                packs.append(tuple(current))
            for part, candidates in enumerate(() if overflow else packs, 1):
                task_id = f"V19/{notice_id}/p{part:02d}"
                task = build_v19_task(record, candidates)
                tasks[task_id] = task
                v19_ids.append(task_id)
        routing[notice_id] = {
            "v3": v3_ids,
            "v19": v19_ids,
            "use_base_b_initially": not bool(v19_ids),
        }
    return views, tasks, routing


def valid_response(
    task_id: str,
    task: Mapping[str, Any],
    response: Mapping[str, Any],
    views: Mapping[str, Any],
) -> bool:
    parts = task_id.split("/")
    notice_id = parts[1]
    if parts[0] == "V3":
        return adapt_keyed_response(response, views[notice_id]["v3"]) is not None
    index = {
        candidate.source_id: candidate
        for candidate in views[notice_id]["v19"]["candidates"]
    }
    source_ids = task["schema"]["properties"]["observations"]["required"]
    candidates = tuple(index[source_id] for source_id in source_ids)
    parsed, _ = parse_v19_observations_relaxed_quote(response, candidates)
    return parsed is not None


def apply_specialists(
    records: Sequence[Mapping[str, Any]],
    rows: dict[str, dict[str, Any]],
    views: Mapping[str, Any],
    tasks: Mapping[str, Mapping[str, Any]],
    responses: Mapping[str, Mapping[str, Any]],
    routing: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, Any]]:
    fallback_b: list[str] = []
    diagnostics: dict[str, Any] = {}
    for record in records:
        notice_id = str(record["id"])
        row = rows[notice_id]
        route = routing[notice_id]
        if route["v3"]:
            task_id = route["v3"][0]
            value, evidence, detail = decide_v3_basis_v2(
                record,
                views[notice_id]["v3"],
                responses[task_id],
                int(row["v3"]),
                str(row["e3"]),
            )
            if detail["valid"]:
                row["v3"], row["e3"] = value, evidence
            diagnostics[task_id] = detail
        if route["v19"]:
            parsed_rows = []
            valid = True
            all_candidates = tuple(views[notice_id]["v19"]["candidates"])
            candidates_by_id = {candidate.source_id: candidate for candidate in all_candidates}
            for task_id in route["v19"]:
                schema_ids = list(tasks[task_id]["schema"]["properties"]["observations"]["required"])
                candidates = tuple(candidates_by_id[source_id] for source_id in schema_ids)
                parsed, reason = parse_v19_observations_relaxed_quote(
                    responses[task_id], candidates,
                )
                if parsed is None:
                    diagnostics[task_id] = {"valid": False, "reason": reason}
                    valid = False
                    break
                parsed_rows.extend(parsed)
            if valid:
                value, evidence, detail = reduce_v19_with_quote_resolution(
                    all_candidates, parsed_rows,
                )
                diagnostics[route["v19"][0]] = detail
                if value is not None:
                    row["v19"], row["e19"] = value, evidence
                else:
                    fallback_b.append(notice_id)
            else:
                fallback_b.append(notice_id)
    return rows, fallback_b, diagnostics


def schema_valid(value: Any, schema: Mapping[str, Any]) -> bool:
    if "enum" in schema and value not in schema["enum"]:
        return False
    kind = schema.get("type")
    kinds = kind if isinstance(kind, list) else [kind] if kind else []
    names = {
        "object": dict, "array": list, "string": str, "integer": int,
        "boolean": bool, "null": type(None),
    }
    if kinds and type(value) not in [names[name] for name in kinds]:
        return False
    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            return False
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            return False
    if isinstance(value, list):
        if "minItems" in schema and len(value) < int(schema["minItems"]):
            return False
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            return False
        return all(schema_valid(item, schema["items"]) for item in value)
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if not set(schema.get("required", [])) <= set(value):
            return False
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            return False
        return all(
            key in properties and schema_valid(child, properties[key])
            for key, child in value.items()
        )
    return True


def valid_base_response(task: Mapping[str, Any], response: Mapping[str, Any]) -> bool:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return False
    try:
        parsed = json.loads(str(response.get("content", "")))
    except (TypeError, ValueError):
        return False
    return schema_valid(parsed, task["schema"])
