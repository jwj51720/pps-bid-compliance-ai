# Complete-fact exploration v3

작성일: 2026-09-09 (dev / mac)

## 결정

향후 후보 정책은 `4,000자`를 문서 선택 기준으로 쓰지 않는다. 4k ordered context는
organizer-control 및 과거 비교군으로만 보존한다. 실제 후보는 카드의 법적 판단 기준,
organizer metadata의 사실, competition-product CSV의 정확 적용 사실, 그리고 제공된 모든
공고 원문을 함께 접근 가능하게 해야 한다.

이것은 법령 원문 RAG를 다시 여는 결정이 아니다. 법령·고시의 해석은 versioned decision
card에만 압축하고, 공고별 사실은 metadata/CSV/원문에서 빠짐없이 읽게 한다.

## 현재 확인된 사실

- dev-200 원본 metadata는 정확히 21 field이며, `official_lines` renderer가 그 21개를
  모두 렌더한다. 원본에만 있고 renderer에서 빠지는 key는 없다.
- EXP154의 `32,768` exact-token admission은 200건 중 193건을 full-source 1회로,
  7건만 ordered 2~3 pack으로 처리했다(총 208 calls). 따라서 4k 앞부분 절단 없이
  원문 접근 자체는 실현 가능하다.
- EXP154는 card v6 + human-readable metadata + friendly exact product fact + complete
  source + V/E로 fast20 `0.241667`이었다. 내용 누락을 제거한 뒤에도 24개 동시 legal
  judgment가 약해지는 현상은 남아 있다.
- EXP157은 source-fact collection을 추가해 fast20 `0.286111`까지 회복했지만, final
  judgment에는 4k anchor와 제한된 fact inventory만 들어가므로 **최종 판정 입력의
  완결 정책은 아니다**. independent holdout도 `0.187500`이었다.

따라서 “모든 문서를 주면 자동으로 성능이 오른다” 또는 “4k가 더 좋으니 문서를 버려도
된다” 어느 쪽도 결론이 아니다. 먼저 complete-source candidate의 입력 완결성을 전수
검증하고, 그 위에서 판단 과부하를 분리하는 가설을 서로 섞지 않고 비교한다.

## 필수 admission gate

새 유료 실험 전 `scripts/audit_complete_fact_admission.py`는 dev-200 전체에서 다음을
검사한다. labels/predictions/provider는 읽지 않는다.

1. 각 supplied source document의 원문 전체가 하나 이상의 exact final message에 존재한다.
2. 21개 organizer metadata field가 message에 존재한다.
3. 모든 active v의 versioned card text가 system message에 존재한다.
4. v10–v18가 활성일 때 competition-products exact fact index가 구성돼 있다.
5. 모든 emitted pack이 exact Gemma chat-template prompt budget 이하이다.

이 전수 audit과 기존 3-record semantic contract audit은 서로 대체하지 않는다. 전자는
**사실 coverage**, 후자는 **각 v의 의미·적용 조건·예외가 정확한 위치에 있는지**를 본다.

## 넓게 탐색할 architecture family

모두 source-complete admission을 유지하고, V/E schema·decoder·frozen postprocess를
무단 변경하지 않는다. 각 family는 한 가지 policy difference만 갖는 config와 independent
fast/holdout gate를 가져야 한다.

| Family | 질문 | final V/E가 받는 사실 | 현재 상태 |
| --- | --- | --- | --- |
| A. complete one-stage | full source와 card를 한 번에 주는 것이 충분한가 | 모든 원문 + 모든 metadata/CSV + cards | EXP154: fast20 .241667 |
| B. complete-source output ergonomics | 같은 사실을 유지한 채 card/출력 presentation만 바꾸면 판단부담이 줄어드는가 | A와 정확히 동일 | 아직 설계 전; source/metadata/card hash가 A와 같아야 함 |
| C. source-first, full final | 1차가 source-grounded navigation만 만들고, 2차도 full source를 보면서 최종 판단하면 도움이 되는가 | 1차 raw fact ledger + 모든 원문 + metadata/CSV + cards | 구현·mock·admission 완료, OpenRouter fast 실행은 402로 3회 불완전 종료 |
| D. semantic task partition | 완결 source를 각 독립 task에 반복 제공할 때 법적 판단이 개선되는가 | 각 group에 모든 원문 + 해당 cards/metadata/CSV | EXP155/156의 단순 2-way는 실패; 새로운 grouping은 진리조건·runtime 근거 없이는 만들지 않음 |

Family C의 1차는 위반 label/법률 해석을 내리지 않는다. 그러나 2차가 4k anchor만 받아서는
안 된다. 2차에도 complete source가 exact-token admission으로 들어가야 한다. 이 때문에
먼저 dev-200 call/token/runtime projection을 내고 2시간 제한을 넘으면 유료 실행하지 않는다.

## 순서

1. EXP154 configuration으로 complete-fact full-population admission audit을 실행하고,
   zero omission인지 artifact로 확정한다.
2. EXP154 rendered input 3종(짧은/첨부/overflow)을 다시 읽어, 사람이 보기에도 card,
   metadata, CSV fact, actual documents의 경계가 이해 가능한지 기록한다.
3. Family B는 **presentation-only** candidate 하나를 만든다. input semantic payload의
   card text, source strings, metadata, CSV fact가 EXP154와 byte-level 동일하다는
   comparison audit이 먼저 통과해야 한다.
4. Family C는 1차/2차 모두 complete-source가 token budget에 들어가는지 exact tokenizer로
   profile하고, final-stage source omission이 0인 설계를 먼저 구현한다. inventory category
   수·excerpt 상한을 label 결과에 맞춰 늘리는 방식은 금지한다.
5. 각 family는 fast panel과 independent holdout을 모두 통과한 하나만 dev-200으로 확장한다.
   fast score만으로 제출 정책으로 올리지 않는다.

Family C의 runtime admission feasibility는 완료했다. Stage1+final은 dev-200에서 최소
416 calls, moderate/schema-upper navigation에서 423/435 calls다. 이후 OpenRouter에서
fast20을 concurrency 20, 4, 1로 각각 실행했으나 18/20, 15/20, 13/20에서 동일한
in-flight-credit HTTP 402로 끝났다. 따라서 **원격 quality probe도 현재는 불가능**하며,
partial output을 점수·정책 근거로 쓰지 않는다. 이 family는 로컬 vLLM에서만 별도 runtime
budget을 재검증할 수 있다. 상세는 `docs/source_first_full_final_feasibility_v1.md`.

`notice_anchor_chars: 4000`은 overflow pack에서 반복되는 공고문 식별용 보조 문맥 길이일
뿐, 선택 상한이 아니다. 공고문 전체와 모든 첨부 원문은 ordered payload에 별도로 들어가며
`audit_complete_fact_admission.py`가 source byte coverage를 전수 검사한다.

## Source-first/full-final의 dev-200 대조 결과

EXP171은 7개 원문 사실 유형의 non-final navigation을 먼저 만들고, **모든 원문을 다시
포함한** V/E final로 판정한다. EXP172는 같은 card v6·friendly metadata·exact product
fact·32k admission·2,500 output cap·decoder·postprocess·concurrency에서 navigation만
제거한 one-stage control이다. 사전 admission은 둘 모두 source 374/374, metadata 21/21,
active card 24/24, over-budget 0을 확인했다.

| dev200 policy | macro F1 | runtime | call count | note |
| --- | ---: | ---: | ---: | --- |
| EXP171 source-first/full-final | **0.307962** | 1,501.6 s | 435 | inventory 216 + final 219 |
| EXP172 capacity-matched one-stage | 0.259281 | 686.5 s | 216 | final only |

따라서 current complete-source incumbent는 Family C다. source-first가 FP를 넓게 줄였지만
remote provider의 한 반복 결과이므로, “model이 법령을 더 잘 이해했다”라고 단정하지
않는다. 안전한 해석은 source-only fact navigation이 long all-item final의 **attention
structure**를 보완할 가능성을 보였다는 것이다. 다음 ablation은 full final source 및
non-final first stage를 유지하고 inventory coverage/표현 하나만 변경한다. source를 다시
4k로 축소하거나 raw law/RAG·dev-label rule을 추가하는 것은 이 결과의 후속이 아니다.

### Provider execution note

EXP163의 one-stage complete-source safe-applicability probe도 11/20에서 HTTP 402로
불완전 종료했다. 따라서 이 시점에는 source-first처럼 다단계인 구조뿐 아니라 새 remote
quality fast probe 전반을 신뢰성 있게 끝낼 수 없다. partial output은 비교표에 넣지 않고,
새 provider retry 대신 offline admission/contract work 또는 local-vLLM 검증만 진행한다.

### EXP159 — Family B 첫 단일 ablation

`configs/config.exp159-full-source-32k-card-v6-markdown-v2-fast-panel.yaml`은 EXP154의
complete-source fact payload를 그대로 유지하고 `prompt.layout`만 `plain → markdown_v2`로
바꾼다. v별 카드에 heading/bullet/output skeleton을 주어 Gemma가 항목 경계와 1/0/evidence
계약을 더 쉽게 읽는지를 확인한다. 이는 새 사실, 새 법령, 새 rule, 새 call, 새 merge를
추가하지 않는다. 유료 fast20 전에는 EXP154와 semantic contract/admission 결과를 나란히
검사하고, short/attachment/overflow exact rendered message를 다시 읽는다.

### EXP159 결과

사전 gate를 모두 통과한 EXP159의 fast20 macro positive-F1은 `0.244444`였다. EXP154
`0.241667`보다 `+0.002778`이지만, v23 FP 하나가 줄어든 결과에 불과하고 핵심 FN은
회복하지 못했다. 또한 heading/output skeleton으로 passes `22→23`, prompt tokens
`336,480→353,170`, wall `40.5→53.4초`가 됐다. independent holdout/dev-200으로
확대하지 않는다. 상세는 `docs/exp159_complete_fact_markdown_v2_fast_result.md`.

## 금지되는 지름길

- 4k prefix로 document/attachment를 다시 조용히 생략하는 candidate
- raw law/RAG/casebook을 context에 다시 넣는 candidate
- dev label/error를 보고 item별 Python threshold를 추가하는 candidate
- final input에서 source를 잃고 inventory null을 0으로 취급하는 staged candidate
- multiple policy changes를 한 config에 섞어 원인을 식별 못 하는 candidate

## 다음 즉시 산출물

- ignored `outputs/exp154-complete-fact-admission-dev200-v1.json`: EXP154의 전수
  fact-coverage admission 결과
- 기존 `outputs/exp154-semantic-contract-audit-v1/rendered_inputs/`의 사람이 읽은
  short / attachment / overflow message review

이 두 결과가 모두 PASS여야 새 complete-source paid candidate를 설계한다.
