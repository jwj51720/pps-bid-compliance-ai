# Clean L41 runtime-hardened submission result

작성일: 2026-09-22

상태: **ZIP 생성 및 staged mock PASS — GPU/vLLM runtime 미검증**

## 제출 파일

- archive: `dist/pps_20260922_145728.zip`
- archive SHA-256: `5cfe82085286b6c95179c419d4df4439a0b22bb098bd891143d12aeadc213af7`
- archive 크기: 136,448 bytes
- 압축 해제 크기: 911,615 bytes
- 파일명 길이: 23자
- members: `script.py`, `requirements.txt`, `runtime_config.json`
- packaged `script.py` SHA-256:
  `63f16695cea464e57d3618365f7f01cddc35d74a7a79f7abf79a70cdb3c575fe`

이 파일은 clean native 독립 제출물이 아니라 reference L41의 출처를 명시한
**L41-derived runtime-hardened candidate**다. 기준 전체 dev200 Macro positive-F1은
`0.7796736645`다. C005D의 `0.8151465658`은 stored L41 결과에 v3/v19 specialist를
추가한 hybrid 품질 실험이고, N008D의 `0.823529`는 v2 단일-item F1이므로 이 ZIP의
24-item 점수로 표기하지 않는다.

## invalid와 실행 오류 대응

기준 L41의 prompt/schema/owner/reducer/evidence/model parameter는 변경하지 않았다.
다음 runtime 대응만 추가했다.

1. backend batch exception이면 동일 batch를 이등분해 재시도하고 순서를 보존한다.
2. 한 request까지 격리해 실패한 경우 invalid placeholder로 기록한다.
3. 최초 세 arm 중 `finish_reason != stop`, empty/invalid response, JSON object parse
   실패인 arm만 동일 message/schema로 1회 batch 재생성한다.
4. 정상 최초 응답은 재생성하거나 덮어쓰지 않는다.
5. retry 이후에도 일부 또는 모든 arm이 invalid이면 기존 arm-specific fallback으로
   조립을 계속하고 `records_without_valid_arm`에 기록한다.
6. retrieval·조립·CSV 처리의 run-level 예외가 남으면 입력 ID 전체에 대해 유효한
   emergency zero-label CSV를 atomic write하고 `DEGRADED_PASS`로 종료한다.
7. retry targets/recovered/unresolved, backend batch/input/error 수를
   `l41_runtime_report.json`에 남긴다.

Local vLLM은 `StructuredOutputsParams(..., disable_any_whitespace=True)`와
`max_tokens=1536`을 사용한다. 이는 OpenRouter N008에서 관찰된 8,192-token whitespace
runaway를 evaluator 경로에서 직접 억제한다. retry는 그 이후에도 발생할 수 있는
length/empty/JSON 실패에 대한 조건부 안전망이다.

## 제출 계약 점검

- server mode는 `PPS_DATA_DIR`, `PPS_OUTPUT_DIR`, `PPS_MODEL_DIR`,
  `PPS_EMBED_DIR` 네 환경변수가 모두 없으면 시작하지 않는다.
- model/BGE는 local path와 `local_files_only=True`만 사용한다.
- `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, telemetry off를 설정한다.
- BGE-M3는 Gemma load 전에 CPU에서 사용하고 unload/GC 뒤 Gemma를 올린다.
- Gemma prompt는 exact chat-template token IDs로 생성하고 14,848 prompt-token
  budget을 넘으면 원문을 자르거나 숨기지 않고 실패한다.
- output은 atomic CSV write 후 49열, ID/순서, binary label, evidence substring/500자,
  NFC 및 CSV formula-prefix 규칙을 검사한다.

## staged ZIP mock

생성된 ZIP을 임시 디렉터리에 새로 풀고 그 안의 `script.py`를 organizer 제공
`data/test.jsonl.gz` 앞 10건에 대해 `--mock`으로 실행했다.

| 항목 | 결과 |
| --- | ---: |
| rows | 10 |
| columns | 49 |
| unique IDs | 10 |
| binary labels | PASS |
| runtime status | PASS |
| invalid retry attempted/recovered/unresolved | 0 / 0 / 0 |

추가 fault-injection tests는 다음을 확인했다.

- synthetic batch failure가 3개 request의 순서를 유지한 채 이등분 복구됨
- valid response는 보존되고 invalid arm 하나만 retry되어 복구됨
- 세 arm 모두 미복구여도 ID를 기록하고 조립을 계속함
- run-level exception에서도 전체 ID·49열 emergency zero-label CSV와
  `DEGRADED_PASS` report 생성
- server mode가 네 organizer 환경변수를 모두 요구함

전체 test suite: `164 passed`. `unzip -t`와 `git diff --check`도 PASS다.

## 남은 제한

- 현재 mac에는 evaluator GPU/vLLM이 없어 1,853건을 120분 안에 완료한다고 검증할 수 없다.
- 기본 workload는 test notice당 3회, 즉 1,853건이면 5,559 logical generations이며
  invalid recovery가 발생하면 그 수만큼 증가한다. batch size 128은 generation 수를
  줄이지 않는다.
- reference ZIP의 public `0.7+`와 server runtime은 사용자 제공 외부 관측이다.
  이번 검증은 로컬 dev200 품질 재현과 mechanical staged mock까지만 증명한다.
- retry는 temperature 0의 동일 task 재생성이므로 항상 다른 출력을 보장하지 않는다.
  대신 structured decoding의 whitespace 금지, batch 격리, fallback, no-dummy abort를
  결합해 silent corruption 가능성을 줄였다.

재생성 명령:

```bash
.venv/bin/python scripts/package_l41_hardened_submission.py
```
