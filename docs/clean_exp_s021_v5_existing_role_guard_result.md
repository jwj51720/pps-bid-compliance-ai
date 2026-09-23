# S021 — 기존 source view의 v5 강등 반사실 결과

상태: **PASS 진단 / guard 승격 기각**. S001 제출물과 canonical 정책은 불변.

`scripts/audit_v5_role_guard.py`가 frozen L41 v5와 기존 clean
`build_regional_participation_candidates`를 dev200·비라벨 20,000건에 동일하게 적용했다.
S001 v5 positive ID와 frozen 재현 ID가 정확히 일치했다. LLM/BGE 호출 0회.
산출물: `outputs/clean-exp-s021-v5-existing-role-guard-v1/audit_report.json`.

| | 기존 v5 양성 | view 통과 | 강등 |
|---|---:|---:|---:|
| dev200 | 7 | 7 | 0 |
| 비라벨 20,000 | 42 | 29 | 13 |

dev200의 v5 `TP=7, FP=0, FN=0, F1=1.0`은 반사실에서도 동일하다. 그러나 이는 이미
adaptive하게 사용한 7개 양성만의 결과다. 비라벨 13건 제거를 곧바로 FP 감소로 세는 것은
정답이 없어 불가능하다.

S020에서 미리 hash 고정된 v5 8건과 교차 검증하니, 기존 view는 실제 참가자 본점
지역제한으로 보이는 `PPS-D-000980`, `PPS-D-005393`을 **제거**했고, 평가 가점 문맥인
`PPS-D-020790`은 **남겼다**. 과거 납품처 지역 문맥인 `PPS-D-013579`은 제거했다.
나머지 네 건은 원문 표면상 참가자 지역제한으로 보이며 남았다. 따라서 이 표본의 source-role
관찰만 놓고 보면 원래 6/8건이 참가자 소재지 제한 표면, view 이후 4/5건이 해당 표면이다.
역할 표면에 대한 F1은 원래 `12/(12+2)=0.857`, view 이후 `8/(8+1+2)=0.727`이다.
이는 대회 v5 정답 F1이 아니라, hash 표본에서 view의 false-removal 비용을 보여주는
진단 수치다.

결론: 기존 regex view는 dev200 성능을 보존하면서 모집단 예측을 31% 줄이지만, 필요한
참가제한까지 버린다. 그러므로 `view가 없으면 v5=0`은 일반화 성능 개선 후보로 채택하지
않는다. `평가` 단어 한두 개를 추가·삭제하는 식의 보정도 같은 문제를 반복한다. 다음 후보는
원문 **전체**와 section 문맥을 읽고 참가자·납품처·평가 대상을 분리하는 source-grounded
관측이어야 한다. 그 관측 역시 dev TP 보존, S020 반례 구분, malformed rate, 호출/시간,
첨부·overflow coverage를 통과하기 전에는 final label에 연결하지 않는다.
