# S007 — 제품·기업범위 Python owner 모집단 funnel 감사 결과

상태: **PASS — Python predicate의 dev 농축과 source-role 누락 확인, 정책 변경 없음**

실행일: 2026-09-23

## coverage

- dev: 200 records / 374 documents
- organizer 비라벨 모집단: 20,000 records / 38,862 documents
- runtime: 538.72초
- LLM calls: 0
- embedding calls: 0
- final prediction/F1 추정: 없음
- output: `outputs/clean-exp-s007-python-owner-population-funnel-v1/audit_report.json`

hash-pinned frozen L41의 실제 FactBuilder, exact product scanner, scope/absence predicate를 같은
경로로 실행했다. BGE ranking은 실행하지 않았으므로 `survives_no_bge`는 실제 final positive가
아니라 BGE veto 전 상한 funnel이다.

## 주요 분포 결과

| predicate | dev | 20k | dev/pop RR |
|---|---:|---:|---:|
| 소액수의 | 17.50% | 44.81% | 0.391 |
| 1억원 미만 | 53.00% | 71.66% | 0.740 |
| 2.3억원 이상 | 22.50% | 11.24% | 2.002 |
| v12 candidate | 1.50% | 0.345% | 4.348 |
| v13 candidate | 3.00% | 1.03% | 2.913 |
| v14 amount+scope pre | 8.50% | 2.385% | 3.564 |
| v14 survives no-BGE | 6.50% | 2.04% | 3.186 |
| v16 absence pre-product | 7.00% | 3.40% | 2.059 |
| v16 survives no-BGE | 4.50% | 2.415% | 1.863 |

dev는 Python owner가 양성을 만들기 쉬운 고액·제품/기업범위 조합을 2~4배 농축하고 있다.
따라서 dev에서 v12/v13/v14가 완벽하거나 높게 보인 것은 모집단 일반화 추정이 아니다. 반대로
모집단 다수인 소액수의·1억원 미만 예외가 dev에서 충분히 검증되지 않았다.

## organizer clause 대 source detector

`조항호내용`의 두 exact category를 label이 아니라 감사 strata로 사용했다.

| audit | dev | 20k |
|---|---:|---:|
| organizer 중기업 포함 제한 | 47 | 2,495 |
| organizer 소기업 전용 제한 | 29 | 1,773 |
| broad detector가 전자를 못 찾음 | 14 | 597 |
| small detector가 후자를 못 찾음 | 7 | 352 |
| v16 no-BGE survivor이면서 organizer broad | 4 | 158 |
| v18 no-BGE survivor이면서 organizer small | 5 | 177 |
| v13 candidate이면서 organizer broad | 1 | 101 |

그러나 organizer clause를 final veto로 쓰면 안 된다. dev의 v16 교차 4건 중 정답은 3건이 1,
1건만 0이었고, v18 교차 5건도 4건이 1, 1건만 0이었다. 이 metadata는 실제 공고문에 해당
참가제한 문장이 존재한다는 증거가 아니라 계약 분류/근거일 수 있다. 그러므로 이 필드를
`제한 존재`로 자동 변환하는 Python correction은 기각한다.

## label-blind source review

hash로 선택한 population v16 교차 표본에서 다음을 확인했다.

- `PPS-D-013624`: 공고문에 중소기업/소상공인 참가자격과 확인서 효력 문장이 실제 존재하지만
  frozen `scope_hits_v2`는 broad/small 모두 0이었다.
- `PPS-D-004930`: 공고문에 `중소기업·소상공인 확인서를 소지한 자`가 실제 존재하지만 detector가
  모두 0이었다.
- 다른 표본에는 metadata category만 있고 source restriction을 확인하지 못한 건도 있었다.

즉 metadata 자체가 답은 아니지만, source detector의 recall 결함도 실제로 존재한다. 줄바꿈,
가운데점, `중소기업`/`중·소기업` 표기, 참가효과 관계를 exact phrase 목록이 안정적으로
표현하지 못한다.

v13 표본에서도 `중기업, 소기업, 소상공인 확인서` 또는 `중·소기업자`를 허용하는데 small-only
candidate로 잡힌 사례가 반복됐다. 다만 한 공고에 broad와 small 조건이 동시에 있을 수 있으므로
organizer broad category만으로 v13을 0으로 만들지는 않는다.

## 결론

1. local-public 괴리에는 Python owner 양성 strata의 dev 농축이 명확히 포함된다.
2. `조항호내용`을 final label rule로 쓰는 것은 새 과적합이며 금지한다.
3. 다음 최소 후보는 v16 하나에서만 모든 문서의 source span을 읽어 기업범위·참가효과·시점을
   관계형으로 분리하는 presence guard다.
4. 계약 후 제출, 해당 시 제출, 법명 단순 인용은 presence가 아니다. 실제 입찰참가 조건만
   absence를 veto한다.
5. v18과 v13은 같은 fact view를 재사용할 수 있어도 v16의 source coverage와 dev regression을
   먼저 통과한 뒤 별도 manifest에서 평가한다.
