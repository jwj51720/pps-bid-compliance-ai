# EXP331 — v5 지방 지역제한 금액 selector 교정

작성: 2026-09-18, dev / mac

## 발견과 가설

v26/v27 v5 카드는 지방 일반 물품·용역에서 `세종시·시·군·구는 5억원`이라고 일괄했다.
주최 측 지방계약법 시행규칙 제24조의 exact source는 다음과 같이 다르다.

- 건설기술·건축설계·공사감리·엔지니어링기술 용역: 3억3천만원.
- 위 유형 중 시설물 안전점검·정밀안전진단: 1억5천만원.
- 그 밖의 물품·제조·용역에서 지방계약법 제5조제1항 적용 지방자치단체: 행정안전부장관
  고시금액. 단, 서울·부산·인천 관할 군·구는 5억원.
- 제5조제1항 비적용 지방자치단체: 5억원.

따라서 모든 시·군·구 및 세종을 5억원으로 보는 기존 selector는 source 오류다. v28은 v5만
교정하며, organizer 입력으로 기관의 제5조 적용 여부나 세부 용역 유형을 확정할 수 없으면
추정하지 않고 0으로 둔다. 가설은 이 교정이 v5 FP를 줄이면서 fast/holdout 양성을 보존한다는
것이다.

## 변경 통제

- base: `configs/config.exp330-v27-v23-interval-card-fast-panel-c4.yaml`
- candidate: `configs/config.exp331-v28-v5-local-threshold-fast-panel-c4.yaml`
- allowed change: `prompt.decision_cards_path` 하나
- v27→v28 delta: v5 하나
- V/E, 24-item all-source, metadata/product renderer, merge/provider/output schema 고정
- Python 금액 selector/label override, v5 specialist, grouping, V-only를 추가하지 않는다.

## 검증 및 실행 gate

fixed fast에는 v5 positive PPS-DEV-049, independent holdout에는 PPS-DEV-046이 각각 하나 있다.
두 건 모두 5억원을 넘으므로 교정 후에도 positive 보존을 검사할 수 있다. fast에는 서로 다른
지방 소관구분·가격·지역제한 negative도 포함된다.

유료 실행 전 preflight, v5-only card delta, exact tokenizer coverage, value-delivery audit,
062/194/143/049/046 rendered semantic contract, fast20 mock를 완료한다. fast에서 v5 positive를
잃거나 macro가 base EXP330보다 나빠지면 holdout/dev200으로 확대하지 않는다. 통과할 때만
EXP330과 policy-identical holdout pair를 만든다.

## 알려진 입력 한계

주최 측 법령 package에는 제24조가 참조하는 현행 행안부 고시금액 숫자 자체가 별도 문서로
보존돼 있지 않다. 또한 organizer metadata `소관구분`만으로 모든 지방기관의 제5조 적용 여부를
확정할 수 있다고 가정하지 않는다. v28은 잘못된 5억원 추정을 제거하지만, 공급되지 않은
기관별 적용 사실이나 고시 숫자를 만들어 내지는 않는다.

## 사전 검증 결과

- preflight PASS: base 대비 `prompt.decision_cards_path`만 변경.
- v27→v28 delta는 v5 하나; decision-card/value-delivery tests `19 passed`.
- exact tokenizer dev200: 200 records, 374 supplied documents, omission 0,
  169×1 + 20×2 + 11×3 = 242 calls.
- actual-value delivery audit: 200 records / 242 final contexts PASS.
- semantic contract: 062, 194, 143, fast v5-positive 049, holdout v5-positive 046에서
  24/24 PASS.
- exact rendered review: 049에는 지방계약/교육기관/일반용역/추정가격 6억원/경상남도 제한,
  046에는 지방계약/지방정부/물품/추정가격 555,308,000원/경기도 제한이 v28 카드와 함께
  전달된다. short/attachment/overflow source도 보존된다.
- exact fast20 mock: 20 rows, parse error 0, 49열 validation PASS.

유료 fast 한 arm 실행 gate를 충족했다.

## 유료 fast 결과와 해석

- EXP331 Macro positive-F1: `.1280753968`.
- matched base EXP330: `.1756944444` (`-.0476190476`).
- v5는 두 run 모두 `TP/FP/FN=0/0/1`; fixed-fast 양성 PPS-DEV-049를 모두 놓쳤다.
- v5 예측은 20건 전부 동일했다. 달라진 셀은 v1 2건, v3 1건, v8 1건뿐이다.
- 20건, parse/validation error 0, evidence validity `1.0`, runtime `310.701s`,
  prompt/completion `526,935 / 18,009` tokens, cost `$0.07003411`.

따라서 macro 하락은 v5 카드 교정 효과가 아니라 수정 대상 밖 all-item/provider 변동이다.
이 run은 v28의 성능 개선을 입증하지 못했고 holdout/dev200으로 확대하지 않는다. 동시에 이 결과는
organizer source와 충돌하던 기존 `지방 일반 물품·용역 5억원 일괄` 문구를 복원할 근거도 아니다.
v28은 source-correct completeness artifact로 보존하되 canonical 성능 정책으로 승격하지 않는다.

후속의 우선 목적은 prompt 기법 탐색이 아니라 24개 카드의 source-concordance다. 같은 잘못된
지방 금액 selector가 남은 v2와 v6을 먼저 찾아 고치되, 한 항목씩 provenance와 실제 final-value
delivery를 검증한다. 성능 실행은 수정된 정보가 모델 행동을 훼손하는지 보는 별도 회귀검사이며,
낮은 단일 run 때문에 source-correct 조건을 카드에서 제거하지 않는다.
