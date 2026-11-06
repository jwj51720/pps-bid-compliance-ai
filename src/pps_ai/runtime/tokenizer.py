"""Exact local Gemma chat-template token counter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence


class GemmaTokenCounter:
    def __init__(self, tokenizer_dir: str | Path) -> None:
        from transformers import PreTrainedTokenizerFast

        path = Path(tokenizer_dir)
        tokenizer_path = path / "tokenizer.json"
        template_path = path / "chat_template.jinja"
        if not tokenizer_path.is_file() or not template_path.is_file():
            raise FileNotFoundError("tokenizer.json and chat_template.jinja are required")
        self.tokenizer = PreTrainedTokenizerFast(tokenizer_file=str(tokenizer_path))
        self.tokenizer.chat_template = template_path.read_text(encoding="utf-8")

    def token_ids(self, messages: Sequence[dict[str, str]]) -> list[int]:
        encoded = self.tokenizer.apply_chat_template(
            list(messages), add_generation_prompt=True, enable_thinking=False,
            tokenize=True, truncation=False, return_dict=True,
        )
        values = encoded["input_ids"]
        if not isinstance(values, list) or any(type(value) is not int for value in values):
            raise ValueError("chat template did not return flat token IDs")
        return values

    def count(self, messages: Sequence[dict[str, str]]) -> int:
        return len(self.token_ids(messages))

    def task_sha256(self, task: dict[str, Any]) -> str:
        import hashlib

        payload = {
            "id": task["id"], "arm": task["arm"],
            "schema": task["schema"], "prompt_token_ids": self.token_ids(task["messages"]),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
