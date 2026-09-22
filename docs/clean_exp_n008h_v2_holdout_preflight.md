# N008H v2 독립 holdout20 preflight

작성일: 2026-09-22

## 정책 동등성과 실행 경계

N008H manifest는
`experiments/manifests/clean_exp_n008h_v2_participation_holdout_v1.json`.
Base는 N008 fast manifest이고 선언된 차이는
`evaluation.cohort`, `evaluation.panel_path` 두 개다.
`scripts/preflight_experiment.py`는 PASS, undeclared/unused 0.
card=v32, view=v2, task=v2, schema, model/generation, Python projection,
evidence parser, prompt budget, call topology는 동일하다.
`configs/dev_prompt_holdout_v1.json`에 고정된 독립 20건만 실행한다.

## 실제 메시지·출처 계약

- dev200 actual task audit: 200건·374문서, gold e2 7/7,
  tokenizer admission 200/200, 최대 10,985토큰.
- holdout panel: 20건·41문서, candidate 164, exact task hash
  20/20, token min/max 2,587/10,919, logical calls 20.
- 실제 rendered system/user 출력 경로:
  `outputs/clean-exp-n008h-v2-participation-holdout-v1/holdout20-preflight/rendered_inputs/`.
  short `PPS-DEV-094`, attachment `PPS-DEV-192`, longest/overflow
  `PPS-DEV-121`을 직접 읽었다. 세 문서의 카드에 적용조건·1/0·
  허용 근거 확인 조건이 있고, v2에 필요한 계약법·업무구분·추정가격
  metadata 및 제공된 공고문·첨부 source span이 있다.
- holdout 양성 `PPS-DEV-053`은
  `outputs/clean-native-v2-performance-task-v2/holdout-positive-review/rendered_inputs/`
  에 별도 출력·검토했다. `[P002 | 공고문/D0 2001:3405]`의
  참가자격 1억원 이상 단일 실적 조건과 추정가격 22,690,000원이
  실제 메시지에 있다.
- longest 음성 `PPS-DEV-121`은 참가자격 조항과 별도의
  제안서 정량평가(단일 20백만원 이상 실적, 4점), 증명서 서식의
  `입찰 참가용` 표기가 함께 있다. N008은 형식 표기보다 실제
  참가 문턱을 관측해야 한다. 첨부 음성 `PPS-DEV-192`의 원문은
  소액수의견적 물품구매와 규격서를 모두 포함한다.
- short 음성 `PPS-DEV-094`의 organizer 추정가격 입력은 1원이다.
  값이 이례적이지만 raw metadata를 임의 교정하지 않는다.
  그 입력에 정량 실적 참가제한이 나타나지 않으므로 이 샘플에서
  v2 양성 결정의 필수값으로 쓰이지 않는다.

## Mock·테스트·유료 실행 직전 선택 확인

`--mock`은 별도 `holdout20-mock`에서 20건, invalid 0으로
실행됐다. Mock의 all-zero/F1=0은 성능점수가 아니다.
`pytest -q`는 158 passed. 유료 실행은 동일 task hash와
`OPENROUTER_API_KEY` loader를 사용하고,
`outputs/clean-exp-n008h-v2-participation-holdout-v1/holdout20/`에만
응답별 checkpoint·metrics를 남긴다. fast 응답을 읽거나 재사용하지
않는다. 가설의 모든 필수 요소가 manifest에서 선택돼 있어 독립
holdout20 호출을 진행할 수 있다.
