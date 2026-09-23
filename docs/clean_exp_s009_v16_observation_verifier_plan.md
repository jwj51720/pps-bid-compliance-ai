# S009 — v16 관계 관측 verifier 계획

상태: **micro 실행 완료 — 의미 gate 실패, 기각**

## S008 실패 근거

S008의 V-only micro는 9/9 schema-valid였지만 사전 의미 gate를 통과하지 못했다.

- 실제 broad 입찰참가 제한 2건: 1건만 v16=0
- metadata clause만 있고 source 제한이 불명인 2건: 모두 v16=1
- 계약 후 확인서 제출 1건: v16=1
- 명시적 판로지원 예외 1건: v16=1로 오판

단일 bit만 출력해 어떤 축을 읽지 못했는지 알 수 없었다. S008은 dev200으로 확장하지 않는다.

## 가설과 허용 변경

base는 S008과 동일한 S001 positive-only v16 full-source route다. source, card, metadata, product,
overflow, AND merge, retry는 전부 고정하고 **출력 관측 schema와 reducer만** 바꾼다.

각 pass는 다음을 구조화한다.

- `applicability`: `APPLIES | NOT_APPLIES | UNCLEAR`
- `qualification`: `BIDDER_BROAD | SMALL_ONLY | POST_AWARD_OR_REFERENCE | NOT_FOUND | UNCLEAR`
- `qualification_quote`: 실제 pass 원문 substring
- `exception`: `EXPLICIT | NOT_FOUND | UNCLEAR`
- `exception_quote`: 실제 pass 원문 substring

Python은 다음 세 명시 반대사실 중 하나가 있을 때만 pass v16을 0으로 축약한다.

```text
NOT_APPLIES OR BIDDER_BROAD OR EXPLICIT_EXCEPTION
```

나머지는 1로 두고 notice final은 pass AND다. quote 검증과 merge 외의 Python 법률 규칙을
추가하지 않는다.

## 실행 gate

1. S008과 task source coverage 100%, context 수와 tokenizer admission 동일
2. exact rendered short/attachment/overflow 재검토
3. 같은 6-notice label-blind micro만 새로 호출
4. 9/9 valid, 실제 broad 2/2와 exception 1/1을 0으로 검출
5. metadata-only 2/2와 post-award 1/1을 1로 보존
6. 위 gate를 통과한 경우에만 dev200의 9 base-positive notice로 확장
7. dev200에서는 v16 외 cell 변화 0, 기존 TP 손실 0을 요구

S009가 실패하면 같은 micro에 prompt 문구를 더 맞추지 않고 v16 extra-call 방향을 기각한다.

실제 결과는 `docs/clean_exp_s008_s009_v16_verifier_results.md`에 기록했다. 9/9 schema-valid였지만
모든 notice를 v16=0으로 만들어 의미 gate에 실패했으며 dev200으로 확장하지 않았다.
