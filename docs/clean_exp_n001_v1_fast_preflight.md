# N001 native v1 fast20 preflight

작성일: 2026-09-22

결론: **20회의 v1-only 유료 진단 호출을 실행할 준비가 됐다.** 이
승인은 fast20에만 한정하며 holdout/dev200 또는 final owner 승격을
뜻하지 않는다.

- manifest diff: PASS. base audit manifest 대비 선언된 변화는
  `run.mode: source_audit_only → fast20_observation`뿐이다.
- cohort: `configs/dev_fast_panel_v1.json`의 고정 20건, v1 positive 3건.
- source: 20건의 제공 문서 35개를 모두 scan, exact 후보 span 102개.
- tokenizer: 20/20 fit, min 2,429, max 10,658, sum 126,011 tokens.
- audited dev200 task hash와 fast20 task hash: 20/20 exact match.
- topology: notice당 1회, logical calls 20, overflow 0, grouping/split 곱셈 없음.
- mock: 20/20 structured U response parse, invalid 0. U는 0 label로
  확정하지 않고 별도 집계된다.
- frozen/legacy: manifest와 실행 모듈에 reference ZIP/base submission
  경로가 없고 `src.pps_ai`만 import한다.

실제 rendered message 전문을 다음 세 가지에서 읽었다.

- short complete: `outputs/clean-exp-n001-v1-fast-diagnostic-v1/fast20/rendered_inputs/short_complete_PPS-DEV-062.json`
- attachment complete: `outputs/clean-exp-n001-v1-fast-diagnostic-v1/fast20/rendered_inputs/attachment_complete_PPS-DEV-131.json`
- largest complete: `outputs/clean-exp-n001-v1-fast-diagnostic-v1/fast20/rendered_inputs/largest_complete_PPS-DEV-165.json`

세 메시지 모두 법률판정 역할 → Y/N/U 출력 계약 → v31 v1 카드 →
source id/doc id/offset가 붙은 실제 문서 조각 순서다. v1은 필요한
organizer metadata와 경쟁제품 CSV 사실이 없으므로 해당 section을
억지로 넣지 않았다. 카드의 적용 전제, 1 조건, 법정 등록·면허,
평가·계약이행·제품/과업 규격 등 실질 0 조건이 렌더링됐다.
short에서는 참가자격/실적/공동수급, attachment에서는 공고문
참가자격과 첨부 구매요약, largest에서는 다문서 참가자격과 서식/
계약이행 문맥이 함께 보인다. 이 때문에 모델이 역할을 구분할 입력은
존재한다. 반대로 source view가 전체 원문을 그대로 싣지 않으므로
판단 사실이 부족하면 U로 답하도록 명시했고 N을 부재 증명으로
자동 해석하지 않는다.

결과 보고는 v1 TP/FP/FN, positive/negative U, invalid, exact quote,
tokens/runtime을 분리한다. U→0 F1은 보수적 진단 값일 뿐 native
final-owner 점수가 아니다. fast20에 양성 3건이 있으므로 recall
방향은 측정 가능하다. 결과가 좋아도 independent holdout20을 먼저
통과해야 dev200으로 간다.
