# Clean EXP-C007CR v4 quote replay result

작성일: 2026-09-21

결론: **직렬화 복구는 성공했지만 품질 승격은 기각**한다. 저장된 C007C 응답을
0-call로 모두 파싱했을 때, 모델이 `PPS-DEV-049`의 제출서류 목록을 참가자격으로
분류한 잠복 FP가 드러났다. C007C의 `3/0/0`은 invalid 응답의 baseline fallback에
의존했으므로 품질 개선의 충분한 증거가 아니었다.

## 재현과 변경 통제

- manifest: `experiments/manifests/clean_exp_c007cr_v4_quote_replay_v1.json`
- command: `.venv/bin/python scripts/run_v4_requirement_experiment.py --config experiments/manifests/clean_exp_c007cr_v4_quote_replay_v1.json --cohort fast20`
- base C007C 대비 manifest preflight PASS, undeclared differences 0.
- fast20 task hash 18/18 동일; C007B source audit와도 동일.
- 저장된 응답 18개 재사용, 새로운 모델 호출 0, model/prompt/schema/semantic fields 불변.
- 기존 valid task 15개의 최종 v4/e4 변경 0.
- 전체 테스트 84 passed.

## 정량 결과

| fast20 | v4 TP/FP/FN | v4 F1 | Macro positive-F1 |
| --- | ---: | ---: | ---: |
| C005D base | 2/0/1 | 0.800000 | 0.727778 |
| C007C strict quote, 3 invalid fallback | 3/0/0 | 1.000000 | 0.736111 |
| C007CR recovered quote | 3/1/0 | 0.857143 | 0.730159 |

`run_report.json`: status PASS, invalid 0, fallback 2(후보 없음), 18 logical calls,
0 new calls, non-v4 changed cells 0, v4 positive-without-evidence 0,
evidence-validator label mutations 0, replay 0.268초. 저장 원응답 usage 합계는
prompt 52,351 / completion 3,868 tokens이며 replay 비용이 아니다.
전체 validator가 보고한 기존 v15 positive-without-evidence 1건은 C005D 상속 셀로,
이번 v4 변경 또는 v4 evidence 위반이 아니다.

## 원인과 반례

- 30·191: negative 후보의 불필요한 quote를 버려 정상 negative proof로 복구.
- 049: 유일한 공백 차이인 positive quote를 공고문 원문에서 exact 207자 span으로 복구.
  하지만 해당 문장은 공고문의 `7. 규격 입찰서(제안서) 제출 → 라. 제출서류` 목록에
  속한다. 기존 350자 전방 candidate window에는 이 상위 제목이 빠져 있었고,
  모델은 `r=Q,m=Y,x=S,a=N,n=N`으로 잘못 분류했다. 즉 quote 해석의 문제가
  아니라 **후보의 상위 절차 역할 누락**이 잠복 FP를 만든 것이다.

따라서 C007CR을 holdout/dev200/canonical로 진행하지 않는다. 다음 후보는
049만 겨냥한 라벨 예외가 아니라, 모든 실적 candidate에 원문에서 확인 가능한
상위 절 제목·문서 위치를 제공하고 동일한 관계 관측을 다시 수행해야 한다.
새 구조가 금액 scope 충돌까지 해결했다고 주장하지 않는다.

Ignored artifacts:
`outputs/clean-exp-c007cr-v4-quote-replay-v1/fast20/`의 `preflight.json`,
`semantic_contract.json`, `rendered_inputs/`, `observations.json`, `metrics.json`,
`run_report.json`, `submission.csv`.
