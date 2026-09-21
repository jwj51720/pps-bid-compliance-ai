#!/usr/bin/env python3
"""Render a no-network two-pass adjudication prompt for human review."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inspect_prompt import _request_preview, build_pipeline_for_preview
from src.config import load_config
from src.data import load_records
from src.prompt import append_untrusted_review_draft


def _token_counter(source: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(source)

    def count(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(ids)

    return count


def _load_drafts(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    drafts: dict[str, dict[str, dict[str, Any]]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        payload = json.loads(line)
        record_id, judgment = payload.get("id"), payload.get("judgment")
        if not isinstance(record_id, str) or not isinstance(judgment, dict):
            raise ValueError(f"invalid draft prediction at {path}:{line_number}")
        drafts[record_id] = judgment
    return drafts


def _markdown(
    record_id: str,
    a_messages: list[dict[str, str]],
    b_messages: list[dict[str, str]],
    a_tokens: int,
    b_tokens: int,
    draft_source: Path,
) -> str:
    return f"""# Two-pass actual LLM input: {record_id}

This is a no-network preview. Pass A is the exact configured organizer control.
Pass B has the same system message and original user content, plus only the
explicitly untrusted label-only draft shown at the end of its user message.
The preview draft came from `{draft_source.relative_to(ROOT)}`; a real run
would use the current record's newly generated Pass-A judgment instead.

| pass | tokenizer input tokens |
| --- | ---: |
| A | {a_tokens} |
| B | {b_tokens} |
| added by review draft | {b_tokens - a_tokens} |

## Pass A — System message

```text
{a_messages[0]['content']}
```

## Pass A — User message

```text
{a_messages[1]['content']}
```

## Pass B — System message

```text
{b_messages[0]['content']}
```

## Pass B — User message

```text
{b_messages[1]['content']}
```
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--record-id", required=True)
    parser.add_argument("--draft-predictions", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    if config.raw.get("experiment", {}).get("lifecycle") != "preview":
        raise ValueError("two-pass inspection requires a lifecycle: preview config")
    source = Path(args.draft_predictions).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"draft predictions do not exist: {source}")
    record = next(
        (value for value in load_records(config.data.input_path) if value["id"] == args.record_id),
        None,
    )
    if record is None:
        raise ValueError(f"record not found: {args.record_id}")
    drafts = _load_drafts(source)
    if record["id"] not in drafts:
        raise ValueError(f"draft predictions do not contain {record['id']}")
    pipeline = build_pipeline_for_preview(config)
    contexts = pipeline.contexts_for_record(record)
    if len(contexts) != 1:
        raise ValueError("two-pass preview requires exactly one notice context")
    a_messages = pipeline.messages_for_context(record, contexts[0])
    b_messages = append_untrusted_review_draft(
        a_messages, drafts[record["id"]], pipeline.active_items
    )
    count = _token_counter(config.llm.tokenizer_source or config.llm.model)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = record["id"].lower()
    (output_dir / f"{stem}.two-pass.messages.md").write_text(
        _markdown(record["id"], a_messages, b_messages, count(a_messages), count(b_messages), source),
        encoding="utf-8",
    )
    (output_dir / f"{stem}.two-pass.request.json").write_text(
        json.dumps(
            {
                "pass_a": _request_preview(config, a_messages, pipeline.response_schema),
                "pass_b": _request_preview(config, b_messages, pipeline.response_schema),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(output_dir / f"{stem}.two-pass.messages.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
