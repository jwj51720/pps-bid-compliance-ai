# S004 — dev200 대 organizer 20,000 입력분포 감사 계획

상태: zero-call 진단 계획

## 가설

S001의 local-public 괴리에는 항목당 양성을 의도적으로 포함한 dev200과 실제 평가 모집단의
입력·후보 발동 분포 차이가 포함돼 있다. 제출의 두 신규 specialist인 v3/v19 source view와
주요 metadata/document feature를 dev200과 organizer 비라벨 20,000건에서 동일한 native code로
측정하면, dev 점수에 기여한 route가 모집단에서 얼마나 다른 빈도로 작동하는지 알 수 있다.

이 실험은 비라벨 자료로 F1을 추정하거나 public label을 추론하지 않는다. 입력분포와 route
coverage만 측정하며 final v cell은 만들거나 바꾸지 않는다.

## 변경 통제

- base config: `experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json`
- allowed change: `generalization_audit` 추가만
- calls: 0
- output: `outputs/clean-exp-s004-generalization-shift-audit-v1/`
- active import: `src.pps_ai`만. frozen reference와 legacy import·실행 0.

## 측정값

- 계약법, 업무구분, 계약방법, 낙찰방법의 범주 분포와 total variation distance
- 문서 수, 전체 문자 수, 첨부 유무, 문서유형 signature의 분포
- 입찰추정가격의 organizer threshold 기반 band 분포
- v3 monetary source candidate의 notice activation/count
- v19 requirement source candidate의 notice activation/count
- 각 이진 route의 dev rate, population rate, percentage-point 차이, risk ratio
- 입력 JSONL SHA-256, record/document coverage, missing metadata

연속량은 median·p90·p99와 standardized mean difference를 기록한다. 표본 수가 20,000이라
사소한 차이도 통계적으로 유의해질 수 있으므로 p-value가 아니라 effect size를 사용한다.

## 판정 gate

- dev 200, unlabeled 20,000, unique ID와 nonempty docs 100%
- 원본 파일 hash와 동일 native view code 경로 기록
- API/embedding calls 0
- aggregated output만 저장하며 raw organizer 문장은 결과에 복사하지 않음
- `abs(rate_dev-rate_population) >= 0.10` 또는 risk ratio가 `[0.67, 1.50]` 밖인 route는
  큰 shift로 표시하되 곧바로 label 제거 근거로 쓰지 않음

결과는 다음 public ablation의 우선순위를 정하는 진단일 뿐 canonical submission을 변경하지 않는다.
