# Clean native owner critical path

작성일: 2026-09-22

## 기준과 계산

C005D dev200 Macro positive-F1은 `0.8151465658`이지만 **완전한
독립 native 실행 점수는 아니다**. v3와 v19에만 native 후보 관측과
reducer가 적용됐고, 나머지 22개 item은 저장된 frozen L41 판정을
재사용했다. v3도 후보 없는 notice 및 미해결 관측에서는 frozen
v3를 보존하며, v19도 37건에서 frozen v19로 fallback했다(35건은
후보 없음, 나머지는 quote 미해결). 따라서 `native v3/v19 owner`라는
명칭조차 **조건부 hybrid**라는 단서를 붙여야 한다.

`F1_v3 = 0.9411764706`, `F1_v19 = 0.75`이고 두 item의 합계
Macro 기여는 `0.0704656863`이다. 나머지 22개 frozen item의
기여는 `0.7446808795`이다. 만약 native v3/v19가 frozen fallback
없이 **동일한 F1을 독립 재현한다는 가정** 아래 독립 baseline이
`0.8`을 내려면, 새 native 22개 item의 평균 F1이
`(24×0.8−0.9411764706−0.75)/22 = 0.7958556150` 이상이어야
한다. C005D frozen 22개 평균은 `0.8123791413`이다. 이는
가능성을 설명하는 조건부 산술이지 native 점수나 통계적
신뢰구간이 아니다. 현재는 v3/v19의 fallback 제거도 필요하다.

따라서 지금은 v17 단독 최대 headroom `(1−0.631579)/24 = 0.015351`
같은 개선만 쫓을 단계가 아니다. **22개 frozen-only item을 독립
native owner로 교체하고 v3/v19의 frozen fallback까지 없애면서
총점을 보존하는 경로**가 제출 후보의 선행조건이다.
v17 v3의 토큰 초과는 이 경로의 한 가지 입력 설계 결함일 뿐,
전체 C005D 입력이나 frozen L41의 초과가 아니다.

## 현재 native final-owner inventory

| 상태 | item | 독립 기준선으로 볼 수 없는 이유 |
| --- | --- | --- |
| 조건부 native + frozen fallback | v3, v19 | 후보 없음·미해결 시 저장된 L41 cell 사용 |
| panel 실험, 미승격 | v4 | fast/holdout 관계 판정 불안정; C005D final은 frozen |
| fast 진단 실패 | v24 | organizer operational truth와 출력 안정성 미해결 |
| fast 진단, 미승격 | v1 | N004 F1 .8571, invalid 0이나 실적 상대방 관계 FP 1 |
| native dev200 final | v22 | N006 phase relation fast/holdout/dev200 모두 F1 1.0; full pipeline 미통합 |
| native dev200 후보, 기각 | v2 | N008 fast/holdout F1 1.0 뒤 dev200 TP/FP/FN 7/3/0, F1 .823529, invalid 20; frozen v2 F1 1.0보다 낮음 |
| source-only 무호출 연구 | v9, v17 | 독립 final decision/score 없음 |
| frozen-only final | v2, v5–v8, v10–v16, v18, v20–v21, v23 | native final owner 미구현 |

v1 source-only v2는 200/200 prompt admission과 기존 e1 8/8
coverage를 통과했다. N004 bidder-relation fast20은 TP/FP/FN
3/1/0, F1 .857143, invalid 0이었다. 남은 FP는 `대학병원에 납품한
실적`의 대학병원을 현재 입찰자 기관유형으로 오독한 semantic
error라 승격되지 않았다. 여기서 `source-only`와
`panel`도 C005D의 해당 item cell은 frozen 판정이다. v3/v19 또한 순수 native cell은 아니다. 현재 **frozen
cell을 전혀 읽지 않고 측정한 24-item dev200 점수는 없다.**

v22는 N005D에서 제안서 평가 설명회를 입찰 전 사업설명회로 오독한 FP
2건이 있었으나, N006이 절차 단계를 `pre_submission_briefing`,
`pre_submission_bar`, `proposal_evaluation_session`으로 분리했다.
N006 fast/holdout/dev200은 각각 1/0/0, 1/0/0, 5/0/0으로 모두 F1 1.0이다.
따라서 v22는 frozen/reference 없이 검증된 첫 완전일치 native dev200
final owner다. 다만 24-item 공통 runtime graph에는 아직 통합되지 않았다.

v2는 N007의 역할 오독을 줄이기 위해 정량 하한과 실제 참가 단계의
결합을 요구한 N008에서 fast20과 holdout20 모두 F1 1.0을 냈다. 그러나
dev200에서는 허용조건 적용 실패 1건과 평가/제안서 양식을 참가자격으로
오독한 2건 때문에 F1 .823529로 하락했다. 또한 20/200 invalid 중 17건이
8,192-token whitespace runaway였다. 따라서 fast/holdout 결과만으로
승격하지 않은 gate가 실제 과대평가를 막았으며, v2는 여전히 frozen-only다.

## 작업 우선순위

1. **재현 가능한 native 소유권 inventory:** 각 item을 `native
   dev200 final`, `native panel-only candidate`, `source-only/no-call`,
   `frozen-only`로 구분한다. 단순한 파일 존재를 owner 완성으로 세지
   않는다. 전체 24개 출력에 빈 owner가 하나라도 있으면 독립 점수를
   주장하지 않는다.
2. **고득점 cell 보존:** C005D에서 F1=1.0인 v1/v2/v5/v7/v8/v15/
   v21/v22는 개선 headroom이 0이지만 각각 Macro `1/24`를 지탱한다.
   이들의 organizer truth condition과 원문/metadata source를 독립
   구현하고 blind panel로 반례를 검사한다. dev에서 맞은 문자열을
   코드 상수로 복제하지 않는다.
3. **native 후보 연결:** v3·v4·v19 등 이미 생성한 native 실험은
   각각의 source contract·holdout·dev200 gate와 no-frozen-fallback
   동작을 확인한 다음에만 독립 final owner로 승격한다. C005D의
   v3/v19는 둘 다 조건부 hybrid이며 v4는 아직 승격되지 않았다.
4. **낮은 F1 item 개선:** migration으로 기준 점수가 재현된 이후,
   dev headroom은 v24 `0.034357`, v9 `0.023810`, v4 `0.019444`,
   v17 `0.015351` 순이다. 이는 상한일 뿐 예상 이득이 아니다.
   각 후보는 예상 TP/FP/FN 변화와 추가 호출 비용을 함께 따진다.
5. **실행 가능성:** reference는 dev200에서 600 logical calls,
   최대 입력 11,590 tokens로 14,848-token admission을 통과했다.
   그러나 evaluator 1,853건/2시간 실행은 아직 증명되지 않았다.
   native 설계는 item×document 호출 곱셈을 기본값으로 하지 않는다.

독립 baseline의 측정 순서는 versioned fast20 → independent holdout20
→ dev200이다. 모든 유료 prompt는 각 active item의 exact rendered
semantic-input contract, tokenizer admission, mock, isolated output,
preflight를 먼저 통과해야 한다. baseline의 total score는 frozen
cell을 하나도 읽지 않은 dev200에서만 주장한다.

근거: `outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/run_report.json`,
`docs/clean_reference_l41_dev200_result.md`,
`docs/clean_native_submission_baseline_plan_v1.md`.
