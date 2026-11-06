# EXP197: human-readable metadata 기술 검증 결과

작성: 2026-09-11, dev / mac

## 결론

입력 조립·문서 운반은 정상이나, EXP192/196의 감사가 `competition_product_context`만
검사해 별도 원시 metadata line의 제품·업종 코드를 놓쳤다. 확대 감사에서 EXP196은 코드가
있는 dev 공고 173/173건 모두 prompt-owned 영역에 식별자를 노출했다.

EXP197은 과거 `official_lines` 출력을 바꾸지 않고 새 `official_lines_human_v2`에서만
두 coded metadata field를 사람이 읽는 이름으로 렌더한다. dev200의 final 217 packs와
source-first stage 1의 217 packs를 모두 검사한 결과 코드 노출은 0건이다. 실제 source
document는 변경하지 않았으며, 문서 원문에 적힌 코드는 그대로 남는다.

## 변경 통제

- config: `configs/config.exp197-human-readable-metadata-fast-panel-c4.yaml`
- base: `configs/config.exp196-corrected-input-source-first-fast-panel-c4.yaml`
- declared/actual change: `prompt.metadata_style` 하나
- preflight: PASS
- cards, 제품 조건 renderer, organizer semantics, source scope, tokenizer admission, staged
  topology, merge/evidence/rules, model/provider parameter: 불변

## 입력 검증

- raw dev input: 200 unique notices, 374 supplied documents
- complete-fact exact-token admission:
  - source omission 0
  - 21 metadata field omission 0
  - card omission 0
  - organizer semantics omission 0
  - over-budget pack 0
  - final direct pack distribution: 185×1, 13×2, 2×3
- source-first profile:
  - stage 1 calls 217, source omission 0
  - empty-navigation final calls 218, source omission 0, total 435
  - saved fast inventory: 24+24 calls, 양 단계 source omission 0
  - schema upper: 총 450 calls, source omission 0
- conditional product delivery:
  - 35 notices, final 43 packs, condition omission 0
  - 전체 dev final 217 packs 및 stage-1 217 packs 검사
  - coded metadata notices 173, prompt-owned code leak 0
- semantic-input contract: 24/24 PASS
- mock: fast panel 20 rows, staged mode 실행, 49-column/ID/evidence validation PASS

## Rendered review

- short complete: `outputs/exp-197-human-readable-metadata-fast-panel-c4/prompt_review/pps-dev-062.messages.md`
- attachment: `.../pps-dev-194.messages.md`
- overflow 3 packs: `.../pps-dev-169.messages.md`
- conditional product: `.../pps-dev-054.messages.md`

수동 검토에서 `김가공기[2318152101]`는 metadata에서 `김가공기`로, 행사대행업의
`(9901)`은 업종명만 남도록 렌더됐다. `DEV054`의 제품명과 `추정가격 3억원 미만에 한함`
조건은 유지됐다. 금액·날짜·조항·`null` 대 `미입력` 의미는 변하지 않았다.

## 성능 및 제출 판정

이 결과는 무료 기술 검증이며 paid fast20 성능 결과가 아니다. EXP196 자체가 fast gate에서
크게 하락했으므로 이 입력 수정만으로 canonical 승격을 주장하지 않는다. root
`config.yaml`과 submission runtime은 아직 과거 EXP171 정책이며, public timeout 문제도
해결되지 않았다. 따라서 현재 canonical zip을 다시 제출하면 안 된다.
