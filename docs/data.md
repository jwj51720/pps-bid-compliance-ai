# Official Data Reference

This document records the EXP-001 profile of the unmodified archive at `data/raw/open.zip`. Reproduce the machine-readable profile with:

```bash
python scripts/profile_data.py --output outputs/data_profile.json
```

## Files and Intended Use

| File | Rows | Purpose | Modification |
|---|---:|---|---|
| `train_unlabeled.jsonl.gz` | 20,000 | Candidate mining and future self-labeling | Never modify |
| `dev.jsonl.gz` | 200 | Gold local inference input | Never modify |
| `dev_labels.csv` | 200 | Gold 49-column local evaluation labels | Never modify |
| `data/test.jsonl.gz` | 10 | Unlabeled submission-path smoke test | Never modify |
| `sample_submission.csv` | 10 | 49-column format example | Never modify |
| `data/항목표.json` | 24 items | Item names, legal references, absence flags | Never modify |
| `data/정답스키마_디코딩.json` | — | Structured-output JSON Schema | Never modify |
| `data/법령패키지/` | 23 laws plus ministry notice data | Official legal snapshot | Never modify |

Generated data belongs under `data/derived/` and must be registered in `data/derived/registry.yaml`. Raw and derived data are ignored by Git and exported separately.

## Notice Schema and Grain

One JSONL line is one notice, keyed uniquely by `id`. All 20,210 profiled IDs were non-null and unique. Each record contains:

- `docs`: one or more `{doc_id, type, text}` objects; at least one `공고문`
- `meta`: the 21 registration fields below
- `dropped_doc_counts`: unavailable documents by type
- `input_completeness`: extraction and observation flags
- `anon_applied` and `assembly_policy_version`: provenance metadata

Allowed document types are `공고문`, `규격서`, `과업지시서`, `제안요청서`, and `예외공표서`.

## Dataset Shape

| Dataset | Notices | Docs/notice mean | Characters/notice mean | Median | P90 | P95 | Max | Incomplete |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Train | 20,000 | 1.94 | 16,525.98 | 13,780 | 32,673.10 | 37,308.05 | 49,947 | 853 (4.27%) |
| Dev | 200 | 1.87 | 17,580.13 | 12,944.5 | 39,117.90 | 42,706.30 | 54,068 | 10 (5.00%) |
| Test sample | 10 | 2.30 | 20,494.20 | 17,486.5 | 31,548.50 | 36,950.75 | 42,353 | 0 |

Dev contains 201 announcement documents, 63 specifications, 53 task instructions, and 57 RFPs. Their mean lengths are 7,840, 5,473, 8,766, and 19,837 characters respectively. EXP-001 deliberately limits document context to 4,000 characters, so truncation/input loss is a known baseline risk rather than a data defect.

## Metadata Fields

Types and null rates below are observed in dev. `null` and the string `미입력` have different meanings.

| Field | Observed type | Null rate | Example / meaning |
|---|---|---:|---|
| 적용계약법 | string | 0% | `지방계약법`; governing contract law |
| 업무구분 | string | 0% | `일반용역`; procurement category |
| 계약방법 | string | 0% | `제한경쟁` |
| 낙찰방법 | string | 0% | `협상에의한계약` |
| 낙찰하한율 | float/null | 57.0% | `82.995` |
| 배정예산금액 | integer | 0% | `310000000` |
| 입찰추정가격 | integer | 0% | `281818182` |
| 소관구분 | string | 0% | `지방공기업` |
| 공동도급구성방식 | string/null | 79.5% | `공동이행` |
| 정보화사업여부 | string | 0% | observed as `미입력` |
| 세부품명번호목록 | string/null | 61.0% | `컴퓨터서버[4321150102]` |
| 제한지역코드목록 | string/null | 56.5% | `부산광역시` |
| 지역제한여부 | string | 0% | `Y` / `N` |
| 면허업종제한목록 | string/null | 39.0% | registered license restrictions |
| 업종제한여부 | string | 0% | `Y` / `N` |
| 조항호내용 | string | 0% | registered restriction clause |
| 공고게시일자 | string | 0% | `YYYYMMDD` |
| 개찰예정일자 | string | 0% | `YYYYMMDD` |
| 긴급공고여부 | string/null | 69.0% | `Y` / `N` |
| 입찰방법 | string | 0% | `전자입찰` |
| 조달방식 | string | 0% | `자체조달` |

## Dev Label Distribution

Positive counts are: `v1=7`, `v2=7`, `v3=8`, `v4=6`, `v5=7`, `v6=6`, `v7=7`, `v8=6`, `v9=6`, `v10=7`, `v11=6`, `v12=6`, `v13=6`, `v14=8`, `v15=6`, `v16=6`, `v17=6`, `v18=7`, `v19=6`, `v20=5`, `v21=6`, `v22=5`, `v23=5`, and `v24=8`.

Dev intentionally covers every item but does not represent test prevalence. Compare positive-class precision, recall, and F1 per item; do not interpret dev calibration as test calibration.

## Quality Assessment

- **Pass:** required schema, unique IDs, record counts, and controlled document types are consistent across all supplied inputs.
- **High analytical risk:** a 4,000-character baseline prompt excludes much of the median notice and often all attachments.
- **Medium analytical risk:** dropped documents make absence-based decisions uncertain for 4.27% of train and 5.0% of dev. Treat “not observed” separately from “not present” in later experiments.
- **Known limitation:** gold evidence is document text only; metadata supports reasoning, especially `v24`, but cannot itself be submitted as evidence.
