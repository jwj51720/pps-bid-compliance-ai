# N006: v22 pre-submission versus evaluation phase relation

작성일: 2026-09-22

## 근거와 가설

N005D는 dev200에서 v22 TP/FP/FN 5/2/0, F1 .833333이었다. 두 FP는
모두 `제안서 설명회(평가)` 불참자를 **평가대상에서 제외**하는 문장을,
입찰 전에 열리는 사업·현장설명회 미참석자의 **입찰·제안서 제출을
금지**하는 조건으로 오독했다. 입력·metadata·quote·parser 오류는 없었다.

기존 `briefing` 축은 organizer truth condition에 있는 절차 단계를 표현하지
못한다. N006은 v22 하나에 한해 다음 관계를 분리한다.

- `pre_submission_briefing`: 입찰·제안서 제출 전에 사업·현장을 설명하는
  행사가 있는가
- `pre_submission_bar`: 그 행사 미참석자가 입찰 또는 제안서 제출을
  할 수 없는가
- `proposal_evaluation_session`: 이미 제출한 제안자의 발표·질의응답·평가
  세션인가

두 종류 행사가 한 공고에 함께 있을 수 있으므로 단일 event enum으로
대표 하나를 고르지 않는다. final v22는 `negotiated=Y AND
pre_submission_briefing=Y AND pre_submission_bar=Y`일 때만 1이다.
evaluation 축은 배제관계 검증용이며 그 자체로 1을 만들지 않는다.

## 고정 범위와 허용 변경

base는 `clean_exp_n005r_v22_binary_projection_replay_v1.json`이다.

- fixed: all-document source view v1, v31 card, human-readable 낙찰방법,
  tokenizer budget, provider/model/temperature/seed, exact evidence gate
- allowed: v2 task/schema, 그 task의 source-audit path, binary decision owner,
  저장-response replay에서 실제 fast panel 실행으로의 전환
- prohibited: FP 두 문구의 Python keyword correction, ID rule, label override,
  legacy/reference/frozen import 또는 fallback

## 단계별 gate

1. dev200 no-call audit: 200/200 admission, 374/374 documents, gold e22 5/5,
   overflow 0
2. short/attachment/largest와 N005D FP 2건, fast/holdout 양성을 실제
   rendered message로 읽는다.
3. mock invalid 0
4. fixed fast20: TP=1, FP=0, FN=0, invalid=0
5. independent holdout20: TP=1, FP=0, FN=0, invalid=0
6. dev200: 목표 TP=5, FP=0, FN=0; N005D의 두 FP에서
   `proposal_evaluation_session=Y`, `pre_submission_bar!=Y`인지 확인

fast 또는 holdout 실패 시 확대하지 않는다. dev200에서 새 오류가 생기면
N006을 승격하지 않는다.
