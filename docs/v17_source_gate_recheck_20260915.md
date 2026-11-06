# v17 source gate 재점검

2026-09-15, dev / mac. 새 성능 실험이 아닌 source 및 saved-output 감사.

## 이미 검증한 것과 남은 것

- incumbent v10은 중소기업·소기업·소상공인 제한의 방향을 묶어 모호하게 표현한다.
- EXP237의 `decision_cards_v14_v17_scope.json`은 중기업 포함 여부를 구분했다.
  fast TP/FP/FN은 existing `0/1/1` → corrected `0/0/1`: 오탐은 줄지만 양성은 미회복.
- organizer 시행령 원문 25–29행은 1억원 미만 물품·용역의 정상 기업범위와 두 단서를
  명시한다. corrected card의 `소수업체·유찰` 표현에는 정확한 수치/조건이 없다.
  이 source-fidelity 부족을 새 성능 gain의 근거로 취급하지 않는다.

## saved raw 응답 대조

`outputs/exp-237-v17-only-corrected-scope-fast-panel-c4/predictions.jsonl`의 042는
v17=0을 내면서 실제 기업범위 참가자격을 근거로 인용했다. parse errors는 없고 pass/final도0이다.
0-label의 근거를 공란으로 정리한 것은 label을 뒤집는 evidence gate가 아니다.

이는 모델이 관련 조항을 출력에 사용했다는 관측이다. 적용성 unknown, 법조문 번호와 문구의
충돌, 예외 해석 중 무엇 때문에0을 냈는지는 기록되지 않았다. 기존 문서의 unknown 원인
단정은 수정했다. 해당 조항을 인용했다는 것만으로 충분히 이해했다고도 단정하지 않는다.

## 독립 양성의 정보성

source packet `outputs/product-item-source-audit-20260915/PPS-DEV-053.md`의 053은
실제 연구용역과 행사대행 code의 관계를 재대조해야 하고, nonprofit 허용 문구도 있다.
053의 gold를 맞추기 위해 code match를 무시하거나 예외를 축소하는 규칙을 만들지 않는다.
따라서 단지 fast/holdout에 각각 양성이 있다는 이유만으로 충분한 source gate를 통과한 것은 아니다.

## 다음 행동의 경계

기업범위 방향 교정은 이미 실행했으므로 반복하지 않는다. 숫자 예외 추가만으로 TP를 회복한다는
가설도 아직 사례에서 입증되지 않았다. 구매대상/고시조건 적용성 또는 예외 역할을 organizer
source로 확정할 수 있는 후보가 필요하다. CSV 후보 검색 제안의 승인 대기는 별도이며,
이번 감사로 exact-code 합의를 변경하거나 유료 실험을 시작하지 않았다.
