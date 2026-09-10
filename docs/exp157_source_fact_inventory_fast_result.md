# EXP157 — source fact inventory → final fast-20 결과

작성일: 2026-09-09 (dev / mac)

## 구조

1차는 32k exact-token complete-source packs를 모두 읽고, v별 판단이 아니라 7개 factual
category별 unchanged excerpt(각 최대 3개)만 반환한다. 1차는 card·법령 해석·0/1을 받거나
내지 않는다. 2차는 card v6, readable organizer metadata, friendly exact product fact,
4k original orientation context, 1차 source-labelled excerpts로 독립 V/E를 판단한다.
inventory empty는 final 0이 아니며 final evidence는 원본 supplied document substring으로
검증된다.

## 검증

- EXP154 대비 declared diff는 stage mode 및 source-fact output capacity(1,536→2,500)
  뿐이며 preflight PASS.
- short `PPS-DEV-01`, attachment `PPS-DEV-03`, overflow `PPS-DEV-143`의 stage1/stage2
  exact message를 export했다. semantic contract는 24/24 PASS이며, stage1이 모든 supplied
  source를 읽고 stage2가 cards/metadata/CSV를 받음을 별도로 검사했다.
- source-category schema, parse, unchanged substring cleaning, empty-inventory non-final
  wording의 regression과 mock fast20을 통과했다.

## 결과

| 정책 | fast20 macro positive-F1 |
| --- | ---: |
| EXP147 input-truthful 4k single | 0.291071 |
| EXP154 32k complete-source one-stage | 0.241667 |
| EXP153 per-v inventory → final | 0.280556 |
| **EXP157 source-category inventory → final** | **0.286111** |

runtime은 81.0초, prompt/completion token은 run artifact에 기록되며 parse error는 0이다.
first-stage unchanged excerpts는 271개였다. 종료 뒤에만 gold positive evidence와 대조한
coverage는 38개 중 12개(31.6%)로 EXP153의 6/38(15.8%)보다 두 배 이상 높다. 이는
labels를 prompt/collector에 사용한 결과가 아니라 post-run measurement다.

## 해석과 다음 gate

EXP157은 4k control보다 -0.004960으로 근소하게 낮지만, complete-source architecture 중
최고 fast20 결과다. fast panel에 맞춘 category/phrase 변경을 하지 않는다. 같은 config를
label-blind independent holdout `configs/dev_prompt_holdout_v1.json`에서 EXP158으로 먼저
확인한다. holdout도 control 수준이면 dev-200 및 runtime projection을 검토할 수 있다.

## EXP158 독립 holdout 결과

동일 policy를 고정 holdout-20에서 재실행한 EXP158은 macro positive-F1 `0.187500`이었다.
wall time은 70.9초, parse error는 없었다. fast20 `0.286111`과의 큰 차이 때문에 EXP157의
fast 개선은 generalization evidence가 아니다. 이 candidate는 dev-200/submission으로
확대하지 않는다. source-category inventory가 EXP153보다 coverage를 높였다는 관측과
현재 7-category/3-excerpt representation이 충분하지 않다는 결론을 분리해 보존한다.

종료 뒤 output-capacity 비교에서도 fast/holdout은 각각 inventory 271/292 excerpts,
23/22 source calls, completion 28,155/28,115 tokens로 거의 같았다. holdout은 오히려
더 많은 source fact를 수집했다. 따라서 holdout 하락을 excerpt 수·source pack 수 부족으로
해석하지 않으며, category 수나 excerpt 상한만 늘리는 후속 유료 실험은 하지 않는다.
