# N008 v2 prompt-only fast20 preflight

작성일: 2026-09-22

## 변경 통제

`experiments/manifests/clean_exp_n008_v2_participation_fast_v1.json`은
N007 manifest를 base로 하고 `data.source_audit_path`, `prompt.task`만
`allowed_policy_changes`에 선언했다. `scripts/preflight_experiment.py`
결과 PASS, undeclared 0, unused 0이다. card=v32, source view=v2,
schema, metadata, reducer, evidence gate, provider와 fixed fast20은 동일하다.
테스트는 두 task의 user message와 schema가 정확히 같고 system의
`performance_participation` 정의만 바뀜을 확인한다.

## 완결 전략 구성·입력 계약

- 새 task builder `build_v2_performance_task_v2`가 manifest에서 실제
  선택되고, dev200 audit `outputs/clean-native-v2-performance-task-v2/dev200/audit.json`
  의 task hash 200/200과 fast panel task hash 20/20이 일치한다.
- dev200은 200건·374문서 scan, candidate 1,748, gold e2 7/7,
  actual prompt 최대 10,985토큰, admission 200/200이다.
- fast20은 20건·35문서, candidate 191, token min/max 2,838/10,585,
  admission 20/20이다. call topology는 20 notice-level calls다.
- 적용 계약법, 업무구분, 입찰추정가격, 공고 원문 참가자격,
  1 조건의 명시적 정량 실적 하한, 0 조건의 평가용 실적 및
  예외/기관규칙 검토가 v32 card + human-readable metadata + source span +
  system observation에 남아 있다. v2 하나만 active item이다.
- short 양성 `PPS-DEV-062`, attachment 음성 `PPS-DEV-131`,
  longest/overflow 음성 `PPS-DEV-165`의 실제 rendered file은
  `outputs/clean-exp-n008-v2-participation-fast-v1/fast20-preflight/rendered_inputs/`
  에 있다. short system/user를 직접 읽었다. attachment/longest의
  user message는 앞서 직접 읽은 N007의 동일 ID 실제 메시지와
  byte-for-byte 같음을 확인했고, 세 system message는 동일 SHA-256
  `3b15c834fa13a0d75cf74fb021f309c0943c463f288e834a1a46e9cd183621c0`
  로 short에서 직접 읽은 새 정의와 같다. 따라서 세 유형의 실제
  rendered system/user 내용을 검토했다.
- `PPS-DEV-062`는 원문의 참가자격 절에 과거 수행실적 3억원 하한이
  있고 organizer 추정가격은 227,272,727원이다.
  `PPS-DEV-165`는 참가자격과 별개의 제안서 정량평가 실적 6점 및
  증명서 서식이 함께 보인다. N008의 새 정의가 바로 이 역할 차이를
  묻는다. `PPS-DEV-131`은 첨부 제안요청서와 2,138,181,818원
  추정가격이 보인다.

## Mock과 유료 범위

`--mock`은 isolated `fast20-mock`에서 20건·invalid 0을 통과했다.
mock F1=0은 점수가 아니다. 실제 실행은 별도 `fast20`에 응답별로
checkpoint하고 20회 모델 호출한다. 검사 시점의 전체 테스트는
`158 passed`다. N007의 paid response는 N008이 읽지 않는다.

유료 실행 직전 체크: 새 task·동일 card/view/schema/reducer·새 audit·
fixed panel·model credentials loader·isolated output 모두 실제
config와 코드에 구현·선택돼 있다. 따라서 N008 완결 가설로 실행 가능하다.
