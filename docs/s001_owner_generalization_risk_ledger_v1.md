# S001 item-owner 일반화 위험 ledger v1

작성일: 2026-09-23

목적은 dev F1이 낮은 item을 순서대로 고치는 것이 아니라, public 0.605에서 공통적으로 발생할 수
있는 owner 위험을 source provenance와 분리하는 것이다. `risk`는 public 오류율 추정이 아니며,
현재 구현이 organizer truth condition보다 dev-selected lexical/absence/product 가정에 얼마나
의존하는지를 나타낸다.

| item | S001 final owner 요약 | risk | 우선 감사 이유 |
|---|---|---|---|
| v1 | Python same-line 기관·능력·등록 phrase | 높음 | 역할·동일조항을 lexical line으로 확정 |
| v2 | Python 실적 참가효과 + 소액수의 예외 | 높음 | 모집단 소액수의 44.8%; dev 17.5% |
| v3 | native monetary relation specialist | 높음 | dev-adaptive reducer, route 30.5% vs 20.42% |
| v4 | r10 q∧r hybrid | 높음 | model exception `e`를 reducer가 무시하는 known defect |
| v5 | Python 지역 역할 + 금액 | 높음 | 2026-09-22 공식 금액 selector 불일치 |
| v6 | Python 기초지역 + 금액 + 예외 | 높음 | 공식 금액 불일치와 지역 역할 lexical 결합 |
| v7 | Python 복수 광역 + 금액 + 예외 | 높음 | 공식 금액 불일치와 표현 recall 미검증 |
| v8 | Python 실적×지역 교집합 | 높음 | 두 역할 detector 오류가 곱해짐 |
| v9 | r10 semantic owner | 중간 | source pool omission과 모델 역할판정, Python override 적음 |
| v10 | Python BGE/exact product bridge와 직접생산 부재 | 매우 높음 | score threshold·query군·absence 결합 |
| v11 | Python 완전관측·제품·기업범위 absence | 매우 높음 | candidate 부재를 법적 부재로 변환 |
| v12 | Python 직접생산 phrase + meta/catalog 적용 | 매우 높음 | 제품 실제 적용성과 CSV 특이사항을 휴리스틱 계산 |
| v13 | Python exact code·소기업 scope·예외 | 높음 | code 역할과 small-quote strata 일반화 미검증 |
| v14 | Python hybrid product·금액·scope·예외 | 매우 높음 | BGE/lexical product 적용성을 final label로 확정 |
| v15 | amount gate + r10 | 중간 | 금액은 exact, semantic restriction은 model에 남음 |
| v16 | Python 완전관측·일반제품·범위 absence | 매우 높음 | 1억원 미만 모집단 71.7%와 absence 결합 |
| v17 | Python 저가·기업범위·제품 cross-veto | 매우 높음 | v10/v11 오류가 전파되는 cross-item owner |
| v18 | Python 완전관측·일반제품·범위 absence | 매우 높음 | 저가 다수 strata에서 부재 오판 위험 |
| v19 | native requirement-relation specialist | 중간 | 역할 schema는 의미 기반, route shift는 6.4%p; recall blind 제한 |
| v20 | Python SW 신호와 exact phrase absence | 높음 | 표현 미탐지를 법적 부재로 변환 |
| v21 | r10 + 공동계약 veto/force positive | 높음 | model judgment 뒤 lexical override |
| v22 | r10 + mandatory phrase/veto | 중간 | 독립 N006 owner는 좋았으나 S001에는 미통합 |
| v23 | r10 date roles + Python 기간 계산 | 중간 | 산술은 안정적이나 날짜 역할 추출 의존 |
| v24 | C24 four-axis model | 매우 높음 | dev TP/FP/FN=5/44/3, 명시된 대량 FP |

## 수학적 범위

현재 public에서 leaderboard 0.75~0.78까지 필요한 Macro 증가는 약 `0.14465~0.17465`다.
한 item을 어떤 상태에서든 완벽하게 고쳐 얻을 수 있는 최대 증가는 `1/24=0.041667`이다.
따라서 이론적 최저로도 각각 최소 4개·5개 item의 완전한 개선이 필요하다. 실제 item F1이 0보다
크므로 필요한 owner 수는 더 많다. v3 또는 v19 한 항목의 rollback만으로 상위권 차이를 메울 수 없다.

dev headroom만 보면 v24, v9, v4, v17 순이지만 S004의 모집단 이동을 반영하면 v10~v18의
저가·소액수의·제품/absence owners가 공통 generalization audit의 우선 대상이다. 이는 해당 item을
한꺼번에 바꾸라는 뜻이 아니다. 공통 fact/view를 감사한 뒤 final owner는 item별로 하나씩
ablation한다.

2026-09-23 모집단 제품 fact 감사에서는 metadata exact match 2,123쌍 외에 문서에서만 발견된
CSV exact notice-code pair가 3,237개였고, CSV `특이사항`이 붙은 문서 mention도 3,564개였다.
따라서 metadata-only absence와 names-only product 적용은 generalization-safe하지 않다. 상세는
`docs/product_fact_population_audit_20260923.md`에 있다.

후속 S007은 frozen Python predicate를 20,000건에 직접 실행했다. v12/v13/v14/v16 후보 route가
dev에서 모집단보다 각각 약 4.35/2.91/3.19/1.86배 농축됐고, 기업범위 detector는 organizer의
exact broad/small clause strata 중 597/352건에서 source scope를 찾지 못했다. v16 no-BGE
survivor 483건 중 158건, v18 survivor 847건 중 177건이 해당 organizer clause와 교차했다.
다만 dev label 대조에서 clause 자체는 실제 원문 restriction 존재를 보장하지 않으므로 이를
Python label veto로 쓰는 안은 기각했다. 상세는
`docs/clean_exp_s007_python_owner_population_funnel_result.md`에 있다.

## 제거·보존 판정 규칙

- exact code join, source offset, 공식 숫자 비교, 날짜 산술은 보존한다.
- role·제품 적용성·예외가 lexical trigger 하나에 의해 final label이 되면 semantic candidate로
  강등할 후보로 표시한다.
- absence owner는 모든 제공 문서와 metadata/CSV applicable state의 관측 완결성을 증명하지 못하면
  final 1을 만들지 않는다.
- cross-item veto는 피참조 item의 오류가 전파되므로 organizer truth condition에 직접 존재하지
  않으면 제거 후보로 둔다.
- dev 오류 ID를 본 뒤 추가된 phrase/threshold는 20,000건 stratified source review 또는 새 public
  one-change ablation 없이는 유지 근거로 쓰지 않는다.

## 실행 우선순위

1. S005 v3-only revert로 최근 overlay 효과를 분리한다.
2. v10~v18 공통 product/absence fact의 저가·소액수의·첨부 strata coverage를 무호출 감사한다.
   S007로 완료했으며 다음은 v16 한 항목의 full-source presence verifier다.
3. v24의 44 FP를 label phrase로 고치지 말고 비교축별 source availability와 contradiction relation을
   모집단에서 측정한다.
4. v5~v7 공식 금액 selector는 correctness correction으로 별도 유지하되 source-role guard와 함께
   item별 승격한다.
5. 새 public 후보는 위 목록 중 정확히 한 owner/policy만 바꾼다.

S010 v3 모집단 morphology 감사에서 specialist route의 source-role 이동이 확인됐다. 모집단
candidate는 dev보다 평가 문구가 `+13.12%p`, 추정가격 초과 금액 표면이 `+10.56%p` 많았고,
고정 route 표본 8/8이 평가/서식이었다. 이는 v3의 role classifier가 public에서 더 어려운 입력을
받는다는 신호다. 다만 AGGREGATE 표면 자체는 candidate 기준 32.0% 대 30.69%로 안정적이므로
single-contract Python gate 복원은 기각한다. v3 위험 등급은 높음을 유지하고, S005 full owner
revert만 one-change public ablation 후보로 둔다.

S011은 Python owner를 무차별 rollback하는 안을 기각했다. initial→final expansion의 dev 추가
precision과 F1 개선 임계는 v16 `62.5% > 14.29%`, v17 `41.67% > 14.29%`, v18
`60.0% > 12.5%`였다. v10은 7 TP/1 FP를 추가하고 기존 FP 하나도 제거했다. population no-BGE
route는 v17·v18에서 large shift가 아니고, v16은 dev보다 population에서 더 적게 발화했다.
이 수치는 public 성능 증명이 아니지만 whole-owner 삭제에는 반대되는 강한 local counterfactual이다.
제품 적용성과 scope 결함은 owner 0화가 아니라 item별 semantic replacement로 해결한다.

S012는 v19 위험을 `중간`으로 유지하되 whole-owner rollback의 우선순위를 낮췄다. candidate route는
dev 82.50%, 모집단 76.10%였고 자기서약·서식 후보 비율은 candidate 기준 88.44% 대 88.54%로
안정적이었다. 외부 발행자+공급/기술지원+입찰 표면은 오히려 dev 7.50%에서 모집단 4.30%로
감소했다. hash 고정 8건 source review에서도 계약 후, 적격심사 전, 입찰 전 보유를 분리해야 하는
실제 문맥이 확인됐다. native owner는 base B 대비 dev FP 8건을 제거했고 동일 165건 저장 total
token도 약 35.3% 적었다. recall blind는 남지만 v19 제거보다 v3-only public ablation이 우선이다.

S013은 v24 위험을 `매우 높음`으로 재확인했다. C24는 `TP/FP/FN=5/44/3`, precision 10.20%였고
positive evidence surface 중 region은 0 TP/13 FP였다. population에서는 region candidate가 dev보다
12.67%p, multi-candidate가 10.645%p 많아 과잉양성 노출이 줄어든다는 근거도 없다. 반면 FP의
52.3%는 네 축 모두 comparable했고 UNOBSERVED 비율은 TN과 비슷해 단순 입력 누락이 주원인은
아니다. exact evidence가 없는 v24 positive 네 건은 모두 FP였지만 생성 quote는 정규화하면 실제
source에 대응했고, v15의 evidence 빈 positive 두 건은 모두 TP였다. 따라서 strict evidence 실패를
label 0으로 바꾸는 보정도 기각한다. label-specific region veto나 새 lexical exception은 만들지 않는다.

S014의 fixed-strata post-stratification에서는 Macro가 0.81515에서 0.79539로 하락했다. 관측 public
괴리의 약 9.42%만 설명하므로 coarse 계약방법·1억원·첨부 mix가 전부는 아니다. weighted 하락은
v17, v19, v10, v23 순으로 컸지만 실제 rollback 비교에서는 current가 모두 우세했다. v3 specialist는
r10보다 `0.9204 vs 0.2668`, v19 native는 base B보다 `0.6064 vs 0.3720`, v17 final은 initial보다
`0.4810 vs 0.1214`였다. 따라서 위험 등급은 유지하되 wholesale rollback은 기각한다. 다음 최소
semantic replacement 대상은 direct/<1억 FP weight가 큰 v17이다.

S015~S016R에서 v19 generation variance를 직접 측정했다. 동일 task 반복 consensus는 TP 6/6을
보존하고 FP 2/4를 제거했지만, Macro 효과는 `+0.00446`이고 test 추가 호출은 약 85개로 예상된다.
따라서 v19 risk는 `중간`을 유지하며 whole-owner rollback도 즉시 repeat 통합도 하지 않는다.
JSON fence 6건은 내부 schema가 완전한 순수 serialization 문제였으므로 parser hardening과 semantic
owner 평가는 분리한다. 다음 generation-risk 감사 대상은 아직 repeat pair가 없는 r10/B/C24다.

S017/S017R은 두 population-relevant strata의 중앙 token 공고에서 r10/B/C24를 exact repeat했다.
한 r10 JSON fence와 N/U 관측 변화가 있었지만 adapter+reducer+S001 owner overlay 뒤 V/E 변화는
0/6이었다. 작은 표본이라 base 위험을 낮추지는 않되, 전체 base repeat framework로 확대할 근거도
없다. 매우 높은 위험의 v17은 S014 weighted F1 하락이 가장 컸지만 S011 wholesale rollback은 크게
나빴으므로, cross-item 삭제가 아니라 제품/기업범위/제한 relation을 한 항목에서 감사한다.

S018에서 v17의 `broad hit`가 실제 중기업 참가 허용이 아닌 소기업 전용 문장이나 적용 예외
문장인 사례가 dev FP와 비라벨 hash 표본 양쪽에서 확인됐다. 제품 CSV exact code도 문서에
있어도 구매대상과 직접생산 참가요건의 역할을 분리해야 한다. dev TP에도 코드와 예외 조문이
등장하므로 단어 veto는 금지한다. v17 위험은 `매우 높음`을 유지하되, 다음 최소 교체 가설은
제품/참가범위/적용예외의 관계 관측이다. 참조:
`docs/clean_exp_s018_v17_source_relation_audit_result.md`.

S019는 v17 중심의 다음 순서를 전체 Python 전략 감사로 넓혔다. frozen direct owner의 최종 발화
dev/pop 비율은 v1 5.93, v2 2.75, v5 16.67, v6 3.55, v7 2.01, v8 17.65이었다.
이는 dev200이 Python 양성 경로를 넓게 농축한 증거지만, 비라벨 20k에서 precision은 식별할 수
없다. S007 제품/absence 위험과 결합해 owner군별 source-role 감사가 우선이며, 개별 lexical
patch나 전체 rollback은 여전히 기각한다. `docs/clean_exp_s019_python_policy_population_audit_result.md`.

S020 hash 고정 source 표본은 direct owner의 공통 원인을 더 좁혔다. v1은 참가 허용·일반 등록,
v5는 지역 가점·과거 납품처, v6은 운반거리 평가를 참가제한으로 읽은 사례가 있었다. v7/v8 표본은
동일한 역할 오류를 즉시 뒷받침하지 않았다. v1/v2/v5/v6/v7/v8에는 기존 Gemma 대체 owner가 없어
Python 제거는 양성 전건 0화다. 따라서 역할 검증 대체 경로를 먼저 입증해야 한다. 상세:
`docs/clean_exp_s020_direct_owner_source_role_audit_result.md`.

S021 기존 지역 source view의 v5 guard는 dev 7 TP를 보존했지만, 비라벨 42 양성 중
13건을 제거했고 그 안에 S020에서 확인한 실제 참가자 소재지 제한 두 건이 포함됐다.
평가 가점 한 건은 반대로 남았다. 기존 view를 final veto로 쓰는 안은 기각했다.
`docs/clean_exp_s021_v5_existing_role_guard_result.md`.

S022의 full-source v5 역할 탐침은 처음에는 인용문 공백 차이 3/24로 strict malformed gate에
실패했다. S022R의 저장응답 0-call replay에서 세 인용을 변경 없는 원문 span으로 모두 복구했고
기존 21개의 역할·인용을 보존했다. dev 양성 7건과 비라벨 역할 양성 14건은 참가자 소재지로,
기존에 확인한 평가 가점·과거 납품처 2건은 다른 역할로 관측됐다. 그러나 blind 비라벨 8건은
모두 양성 역할이어서 음성 일반화가 시험되지 않았다. 이 owner를 승격하거나 v5에 더 많은
prompt 변형을 붙이지 않는다. 현재 목적은 owner군 전체의 Python final 승격 위험을 20k
노출·원문 역할·대체 경로 기준으로 비교하는 것이다.
`docs/clean_exp_s022_v5_role_probe_result.md`.

S023은 direct Python 여섯 항목의 dev 평가가 교체 선택에 구조적으로 불리함을 확인했다.
v1/v2/v5/v7/v8은 dev200에서 TP/FP/FN이 각각 7/0/0 또는 v8 6/0/0으로 F1=1이다.
이 경로의 기존 양성을 지우는 gate는 dev에서 반드시 감점된다. 여섯 항목의 dev Macro
기여 0.24679는 관측 local-public 차이 0.20979보다 크므로 공통 실패의 수학적 영향 범위는
충분하지만 실제 public 기여는 item별 결과 없이는 알 수 없다. 이후 포화 item의 dev F1
상승을 과적합 제거의 필수 gate로 요구하지 않고, blind 원문 역할·가능한 독립 라벨/한 변경
public 평가를 분리한다. `docs/clean_exp_s023_dev_saturation_generalization_gate_result.md`.

S024에서 같은 여섯 owner의 첨부-only predicate 후보가 비라벨 20k에 240
notice-item pair 존재했다. v2 164건이 가장 많았지만 제안요청서의 실적 평가·서식이
섞였고, v1 30건에는 참가 허용/평가위원/참관객 역할이 다수였다. v5/v6도 지역 가점·
운반거리와 실제 참가조건이 혼재했다. 이 결과는 source omission과 lexical FP를
**동시에** 보여 준다. 정책은 그대로 두고, 전 문서 source-role 관측을 하나의
item truth condition에서 먼저 검증한다. `docs/clean_exp_s024_direct_attachment_coverage_result.md`.
