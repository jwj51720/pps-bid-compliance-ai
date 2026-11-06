# N005: native v22 briefing-qualification owner

작성일: 2026-09-22

## 가설과 수학적 우선순위

독립 native baseline은 frozen/reference owner를 읽지 않고도 현재 완전일치
항목의 점수를 보존해야 한다. v1·v2·v5·v7·v8·v15·v21·v22는 각각
최대 Macro `1/24 = 0.0416667`을 지탱한다. 이 가운데 v22는 다음 세
truth condition으로 닫히므로 구현 자유도와 호출비용이 가장 작다.

1. 계약이 협상계약이다.
2. 입찰 전 현장·사업설명회가 실제로 열린다.
3. 미참석자는 입찰 또는 제안서 제출이 불가능하다.

단순 설명회 안내, 선택 참석, 제안서 발표·평가 참석, 착수·중간·최종
보고회는 3번 조건이 아니다. dev200 양성은 5건이며 고정 fast20과
independent holdout20에 각각 1건이 있어 순차 gate가 가능하다. 같은
Macro 기여의 v2는 고시금액·기관규칙·특수기술 예외가 추가로 필요하므로
v22 다음으로 미룬다.

## 독립 입력과 역할 분리

- organizer 제공 모든 문서를 순서대로 scan한다.
- 각 문서의 시작부와 `설명회/현장설명/사업설명`, `입찰참가자격`
  anchor 주변의 변경 없는 source span만 bounded view로 렌더링한다.
- organizer metadata에서는 v22에 필요한 `낙찰방법`만 사람 친화적
  문장으로 렌더링한다. raw JSON·internal key는 넣지 않는다.
- Gemma는 `negotiated`, `briefing`, `exclusion` 세 사실만 관측한다.
- Python은 `Y/Y/Y`만 v22=1로 투영하고 exact evidence substring을
  검증한다. 키워드 자체로 label을 정하지 않는다.
- legacy, frozen loader, reference prompt/output을 import하거나 fallback으로
  사용하지 않는다.

## 실험 계약

- base config: `experiments/manifests/clean_native_v22_source_audit_v1.json`
- candidate: `experiments/manifests/clean_exp_n005_v22_briefing_fast_v1.json`
- allowed policy change: `run.mode`만 허용한다. 입력·prompt·provider는
  source audit manifest와 동일하게 고정한다.
- model: `google/gemma-4-26b-a4b-it`, temperature 0, seed 20260826
- prompt budget: exact Gemma tokenizer 14,848
- fast cohort: `configs/dev_fast_panel_v1.json`

## Gate

1. dev200 200/200 admission, 모든 제공 문서 inspected, gold e22 5/5
   source coverage, overflow 0
2. rendered short/attachment/largest와 fast positive 1건을 사람이 읽어
   세 truth condition·metadata·provenance가 실제 메시지에 있음을 확인
3. mock malformed 0
4. fast20 TP=1, FP=0, FN=0, U=0일 때만 holdout20
5. holdout20 TP=1, FP=0, FN=0, U=0일 때만 dev200
6. dev200 목표 TP=5, FP=0, FN=0, evidence validity 100%

fast 실패 시 prompt를 같은 panel에 반복 적합하지 않는다. 오류가 source
누락인지 relation 판정인지 먼저 분해한 새 계획 없이는 재실행하지 않는다.
