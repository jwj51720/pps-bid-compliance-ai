# S017R — base repeat JSON fence 0-call replay 계획

작성일: 2026-09-23

상태: **계획 고정**

## 원인과 범위

S017의 6개 repeat는 모두 transport stop/invalid=false였다. 그중
`r10/PPS-DEV-21`만 전체 JSON object가 단일 `json` Markdown fence로 감싸져 frozen strict
parser가 fallback했다. 나머지 5건은 strict-valid였다.

S017R은 S016R에서 검증한 동일한 outer-fence adapter를 이 한 response에만 적용해 0-call로
재조립한다.

- base config: `experiments/manifests/clean_exp_s017_base_arm_exact_repeat_panel_v1.json`
- allowed change: `base_repeat_json_fence_replay`
- source raw responses:
  `outputs/clean-exp-s017-base-arm-exact-repeat-panel-v1/responses/`
- expected recovered task: `r10/PPS-DEV-21` 정확히 1개
- LLM/embedding calls: 0
- prompt/schema/inner JSON/reducer/merge/selected panel: 변경 없음
- fence 밖 text, 복수 fence, invalid inner JSON은 복구하지 않음

## 검증

1. raw response SHA와 adapted response를 기록한다.
2. inner JSON object structural equality를 확인한다.
3. recovered set이 사전 고정 한 건과 정확히 같아야 한다.
4. frozen assembler의 repeat diagnostic이 strict-valid로 바뀌는지 확인한다.
5. single/joint S001-equivalent V/E changed cells와 macro를 다시 계산한다.
6. calls.llm_new=0이어야 한다.

S017R 결과까지 final 변화가 0이면 이 두 source strata의 6-task micro에서 base generation
variance가 final S001 label로 전파되지 않았다고 결론낸다. 이는 전체 600 task 안정성이나 public
괴리 부재를 증명하지 않는다.
