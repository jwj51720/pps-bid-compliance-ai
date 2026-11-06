# 실험 config 관리

`config.yaml`은 단 하나의 canonical 제출 정책이다. `configs/*.yaml`은 과거 또는
비교 실험이며, root config를 덮어쓰지 않는다.

## config가 표현하는 것

- `prompt.*`: 입력 문서 admission, RAG/카드 artifact, 판정·evidence·출력 계약
- `llm.*`: 동일 Gemma의 decoding 및 provider 전송 조건
- `grouped_run.*`: v-group 수와 reference bundle 사용 여부. 호출 수를 곱하는 실행
  정책이므로 runner CLI가 아니라 config에 기록한다.
- `data.fast_panel_ids_path`: 평가 cohort만 바꾼다. 모델 정책 차이로 해석하지 않는다.

`output_mode`의 의미는 아래와 같다.

| 값 | 판정/근거 계약 | 용도 |
|---|---|---|
| `labels_and_evidence` | 모든 v에 `위반여부`와 `근거문구` | canonical VE |
| `labels_only` | v 라벨만 | 속도 진단 전용; strict evidence와 함께 쓸 수 없음 |
| `labels_and_anchor` | 짧은 판단어구, 최종 e는 비움 | 별도 진단 |
| `labels_and_sparse_evidence` | VE와 같은 판정·원문근거 계약을 `판정/발췌/부재검토`로 직렬화 | 출력 직렬화 ablation |

## 변경 통제

기존 조건 하나만 바꾸는 실험은 `experiment.base_config`와
`experiment.allowed_policy_changes`를 반드시 선언한다. 유료 호출 전 다음을 실행한다.

```bash
PYTHONPATH=. .venv/bin/python scripts/preflight_experiment.py --config configs/<experiment>.yaml
PYTHONPATH=. .venv/bin/python scripts/run_experiment.py --config configs/<experiment>.yaml --mock --fresh
```

첫 명령은 effective prompt/LLM/group execution policy를 base와 비교해, 선언하지 않은
변경이 있으면 실패한다. 둘째 명령은 실제 schema·token admission·output 경로를
네트워크 없이 확인한다. grouped 실험은 `run_grouped_experiment.py`를 사용하되
`grouped_run`의 값을 CLI로 재정의하지 않는다.

`experiment.lifecycle: invalidated` config는 결함 있는 과거 기록 보존용이다. loader가
실행을 거부한다. 결과 파일의 source hash는 남지만, 해당 수치는 후보 비교나 제출 근거가 아니다.
