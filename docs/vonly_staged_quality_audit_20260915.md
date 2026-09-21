# Saved V-only stage label-quality audit

작성: 2026-09-15, dev / mac

## 질문

EXP186/187의 낮은 최종 점수가 V-only 판정 자체의 실패인지, 아니면 뒤의 V/E verifier 또는
V-only resolver가 좋은 draft를 망친 것인지 분리한다. 새 provider 호출은 하지 않고 저장된
model-owned stage judgments를 같은 fixed fast20 labels로 직접 평가한다.

재현 명령:

```bash
.venv/bin/python scripts/analyze_vonly_staged_quality.py \
  --labels data/raw/open/dev_labels.csv \
  --run-dir outputs/exp-186-vonly-draft-full-final-fast-panel-c4 \
  --run-dir outputs/exp-187-vonly-consensus-full-source-fast-panel-c4 \
  --output outputs/vonly-staged-quality-audit-20260915/report.json
```

## 결과

| Run/stage | complete-source reads | Macro positive-F1 | predicted positives |
| --- | ---: | ---: | ---: |
| EXP186 V-only draft | 1 | `.136310` | 13 |
| EXP186 final V/E verifier | 2번째 read | `.206944` | 21 |
| EXP187 V-only draft 1 | 1 | `.109028` | 14 |
| EXP187 V-only draft 2 | 1 | `.117659` | 10 |
| EXP187 final V-only resolver | 3번째 read | `.097917` | 16 |

EXP186 draft는 v1/v2/v3/v12/v22 외 대부분의 positive item을 전부 0으로 냈다. EXP187의 두
독립 draft도 각각 `.1090`, `.1177`로 낮고 서로 다른 오류를 냈다. 따라서 “V-only draft는
좋았는데 final resolver가 망쳤다”는 설명은 성립하지 않는다. all-24 complete-source V-only
판정 자체가 이미 낮은 recall을 보인다.

EXP186에서는 V/E final이 V-only draft보다 `.070635` 높았다. EXP187에서는 V-only resolver가
두 draft보다도 낮았다. 여러 V-only read는 신뢰할 만한 독립 voter가 아니며, resolver도 그
오류를 안정적으로 교정하지 못했다.

## 현재 결론

1. all-item V-only single/multiple-read는 label-quality lever가 아니다.
2. 같은 prompt 반복은 v7 EXP224/309처럼 temperature 0에서도 결과가 뒤집힐 수 있어,
   majority나 best-of-run이 provider 변동을 성능으로 오인할 위험이 있다.
3. item-local V-only는 v4/v5/v6/v1/v7/v8에서 V/E와 동률, v19/v23/v12에서는 열위였고,
   v20에서만 V/E보다 일관되게 높았지만 dev200 FP 66으로 precision이 붕괴했다.
4. 따라서 evidence를 후처리하기 전에 V-only label gain을 요구한다는 원칙을 유지한다.
   현재 evidence-recovery 알고리즘을 정당화하는 일반 V-only 이득은 없다.
5. 다음 구조는 동일 input의 반복 판정이 아니라, 한 final에서 item attention을 보존하면서
   EXP208/262의 complete semantic input과 원문 재검증을 유지해야 한다.

이 감사는 저장된 stage outputs의 사후 평가이며 Python label merge나 submission policy 변경이
아니다.
