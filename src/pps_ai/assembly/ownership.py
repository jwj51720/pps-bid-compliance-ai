"""Explicit final-writer contract for the frozen L41 baseline."""

from __future__ import annotations


FINAL_OWNERS: dict[str, str] = {
    "v1": "deterministic.v1", "v2": "deterministic.v2",
    "v3": "hybrid.r10", "v4": "hybrid.r10",
    "v5": "deterministic.v5", "v6": "deterministic.v6",
    "v7": "deterministic.v7", "v8": "deterministic.v8",
    "v9": "llm.r10", "v10": "deterministic.v10",
    "v11": "deterministic.v11", "v12": "deterministic.v12",
    "v13": "deterministic.v13", "v14": "deterministic.v14",
    "v15": "hybrid.r10", "v16": "deterministic.v16",
    "v17": "deterministic.v17", "v18": "deterministic.v18",
    "v19": "llm.B", "v20": "deterministic.r10",
    "v21": "hybrid.r10", "v22": "hybrid.r10",
    "v23": "hybrid.r10", "v24": "llm.C24",
}


def validate_owner_matrix(owners: dict[str, str] = FINAL_OWNERS) -> None:
    expected = {f"v{index}" for index in range(1, 25)}
    if set(owners) != expected:
        raise ValueError("owner matrix must cover exactly v1-v24")
    if any(not isinstance(owner, str) or not owner for owner in owners.values()):
        raise ValueError("every item must have one nonempty final owner")
