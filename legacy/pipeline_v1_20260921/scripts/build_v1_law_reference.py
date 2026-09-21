#!/usr/bin/env python3
"""Extract complete official v1 provisions into a packageable fixed reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def extract_article(text: str, article: int) -> str:
    match = re.search(rf"^제{article}조\([^\n]+", text, re.MULTILINE)
    if match is None:
        raise ValueError(f"article {article} was not found")
    following = re.search(r"^제\d+조\(", text[match.end() :], re.MULTILINE)
    end = match.end() + following.start() if following else len(text)
    return text[match.start() : end].rstrip()


def source_file(law_dir: Path, filename: str) -> Path:
    path = law_dir / filename
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--law-dir", default="data/raw/open/data/법령패키지/법령")
    parser.add_argument("--output", default="data/derived/law_reference_v1_v1.json")
    args = parser.parse_args()
    law_dir = Path(args.law_dir)
    national = source_file(law_dir, "국가를 당사자로 하는 계약에 관한 법률 시행령.txt")
    local = source_file(law_dir, "지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt")
    sources = (
        (national, "국가계약법 시행령", (12, 21)),
        (local, "지방계약법 시행령", (13, 20)),
    )
    blocks: list[str] = []
    hashes: dict[str, str] = {}
    for path, title, articles in sources:
        raw = path.read_text(encoding="utf-8")
        hashes[path.name] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        for article in articles:
            blocks.append(f"[출처: {title} 제{article}조]\n{extract_article(raw, article)}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    manifest = output.with_suffix(".manifest.json")
    manifest.write_text(
        "{\n"
        '  "item": "v1",\n'
        '  "method": "complete statutory articles; no character or token truncation",\n'
        f'  "output": "{output.name}",\n'
        '  "source_sha256": ' + json.dumps(hashes, ensure_ascii=False) + "\n}\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
