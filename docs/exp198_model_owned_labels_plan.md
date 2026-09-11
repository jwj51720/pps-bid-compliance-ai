# EXP198: model-owned labels with explicit postprocess provenance

작성: 2026-09-11, dev / mac

## 문제

EXP171 계열은 `postprocess.frozen_rule_set: exp123_v1`로 v2·v3·v21을 모델 출력 뒤에
Python이 교체한다. dev200의 최종 `.307962` 중 이 세 항목의 완전 F1이 macro `.125`를
차지하지만, 규칙 전 모델 판단은 `.250070`이고 public에서 EXP123의 개선은 크게 축소됐다.
최근의 “Python은 최종 라벨을 override하지 않는다”는 정책 설명과 canonical 구현도 충돌한다.

## 구조 변경

모든 `Prediction`은 다음을 명시적으로 보존한다.

- `model_judgment`: source-pack merge와 evidence 검증까지 끝났지만 configured postprocess 전인
  모델 소유 판정
- `judgment`: 제출에 쓰이는 최종 판정
- `postprocess_policy`: 적용한 정책 이름 또는 null
- `postprocess_changes`: item별 before/after label·evidence

후처리는 pipeline의 단일 함수에서만 실행하고, direct/final/subset 경로가 각자 몰래 적용하지
않는다. submission 로그는 변경 record/cell 수를 출력한다.

## EXP198 후보

- base: `configs/config.exp197-human-readable-metadata-fast-panel-c4.yaml`
- allowed policy change: `postprocess.frozen_rule_set` 하나
- candidate: null
- cards v10, 제품 조건 v2, 익명화 semantics, human-readable metadata, complete source,
  source-first/full-final, merge/evidence/model/provider는 그대로 유지한다.

저장된 과거 pass judgment로 계산한 rule-free 점수는 새 모델 호출이 아닌 진단이며, EXP198
성능 결과로 부르지 않는다. paid fast20은 preflight/input/render/mock gate 이후에만 실행한다.
fast gain이 있을 때만 independent holdout20, 그 뒤 dev200으로 확장한다.
