# N008D 동일 정책 dev200 paid-run preflight

작성일: 2026-09-22

## 변경 통제·가설 완결성

Manifest `experiments/manifests/clean_exp_n008d_v2_participation_dev200_v1.json`
의 base는 N008H holdout이며 유효 정책 차이는 `evaluation.cohort`와
`evaluation.panel_path=null`뿐이다. `scripts/preflight_experiment.py`
PASS, undeclared/unused 0. v32 card, v2 bounded source view,
observation task v2, schema, metadata, threshold projection,
parser/evidence gate, model/generation은 fast·holdout과 같다.
dev200은 200 notice-level calls이고 그룹 곱셈이 없다.

## 실제 입력·semantic contract

- organizer dev200 200건, 제공 문서 374개 모두 scan, selected source
  spans 1,748, gold e2 7/7. 실제 rendered task exact tokenizer
  admission 200/200, token min/max 2,082/10,985.
- `outputs/clean-exp-n008d-v2-participation-dev200-v1/dev200-preflight/rendered_inputs/`
  에 short `PPS-DEV-179`, attachment `PPS-DEV-196`,
  largest/overflow `PPS-DEV-140`의 actual system/user/schema를
  출력했다. 이 세 task는 앞서 직접 읽은
  `outputs/clean-native-v2-performance-task-v2/dev200/rendered_inputs/`
  의 해당 task와 exact JSON equality를 확인했다. 새 system의
  정량 하한 + 참가 단계 두 조건은 N008 fast rendered message에서
  직접 읽었고, card·metadata·source와 1/0/예외 관계는 N007/N008
  semantic review에서 확인했다. active item은 v2 하나다.
- card는 organizer 제공 법령을 offline 검토해 만든 compact 기준이고,
  prompt에 법령 원문·raw metadata JSON·법령 bundle을 넣지 않았다.
  source span에는 doc-id/type/offset/SHA-256이 있다.

## Mock·런타임 위험

`--mock` 200건은 별도 `dev200-mock`에서 200 logical calls,
invalid 0으로 완료됐다. Mock의 FN 7/F1 0은 성능결과가 아니다.
`pytest -q` 158 passed. 출력은 isolated
`outputs/clean-exp-n008d-v2-participation-dev200-v1/dev200/`에
응답별 checkpoint, config, preflight, observations, per-notice metrics를
보존한다.

N008H holdout에는 8,192 completion-token 공백 runaway 1건이 있었고
max completion request 1,024와 불일치했다. 원격 provider의
사유는 미확정이며 dev200에서 malformed/length와 wall time을 별도
기록한다. 이 위험을 숨기거나 같은 정책의 parser/provider parameter를
바꾸지 않는다. paid 실행 직전 가설 요소는 구현·선택돼 있다.
