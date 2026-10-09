# Knowledge Graph 추출 평가

`../data/sample_triples.json`의 수동 label이 붙은 gold set에 대해 entity 및 relation 추출을 채점합니다.

## 실행

Repo root에서 dependency를 설치하고 API key를 설정하세요:

```bash
uv sync --all-extras
cp .env.example .env  # 그런 다음 .env를 편집하여 ANTHROPIC_API_KEY 추가
```

그런 다음:

```bash
uv run python capabilities/knowledge_graph/evaluation/eval_extraction.py
```

## Metric

**Entity P/R/F1** — Canonical화한 이름이 같은 문서의 gold entity와 일치하면 추출한 entity를 true positive로 계산합니다. Canonicalization은 소문자로 바꾸고 `data/alias_map.json`을 통해 알려진 표면 형태의 변형을 mapping합니다("National Aeronautics and Space Administration" → "nasa").

**Relation P/R/F1** — Canonical화한 두 endpoint가 gold (source, target) 쌍과 일치하면 relation을 true positive로 계산합니다. **Predicate 표현은 무시합니다**. "commanded"와 "was commander of" 모두 인정하지만 같은 두 entity 사이에서 "destroyed"처럼 의미적으로 틀린 predicate도 인정합니다. 따라서 보고된 relation recall은 상한입니다. Extractor가 올바른 *연결*을 찾았는지를 측정하며 올바르게 label을 붙였는지는 측정하지 않습니다. 더 엄격한 scoring에는 predicate-similarity 확인을 추가할 수 있습니다(예: 후보 쌍마다 Claude judge 호출).

## 예상 Baseline

`claude-haiku-4-5`와 가이드의 extraction prompt를 사용하면 대략 다음을 예상할 수 있습니다:

| Metric | P | R | F1 |
|---|---|---|---|
| Entity | 0.80–0.90 | 0.70–0.85 | 0.75–0.85 |
| Relation | 0.70–0.85 | 0.55–0.70 | 0.60–0.75 |

이 범위는 참고용입니다. 모델의 non-determinism 때문에 실제 score는 실행마다 달라집니다.

Relation recall은 얻기 어려운 수치입니다. Extractor는 완전한 범위보다 적은 수의 확신 높은 edge를 선호하며 보수적인 경향이 있습니다. Recall을 높이도록 extraction prompt를 조정하면(예: "사소한 관계도 포함하여 명시된 모든 관계를 추출하세요") precision을 희생하여 recall을 얻습니다.

