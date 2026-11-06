"""Structured-response recovery primitives with append-only attempt artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .openrouter import atomic_json


def response_is_usable(response: dict[str, Any]) -> bool:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return False
    content = response.get("content")
    if not isinstance(content, str) or not content.strip():
        return False
    try:
        parsed = json.loads(content)
    except (TypeError, ValueError):
        return False
    return isinstance(parsed, dict)


def attempt_path(root: Path, arm: str, notice_id: str, attempt: int) -> Path:
    if attempt < 1:
        raise ValueError("attempt number must be positive")
    return root / arm / notice_id / f"attempt_{attempt:03d}.json"


def write_attempt(
    root: Path, arm: str, notice_id: str, attempt: int, response: dict[str, Any],
) -> Path:
    destination = attempt_path(root, arm, notice_id, attempt)
    if destination.exists():
        raise FileExistsError(f"attempt artifact already exists: {destination}")
    atomic_json(destination, response)
    return destination
