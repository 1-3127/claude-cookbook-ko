# Claude의 Capabilities

Claude Cookbooks의 Capabilities 절에 오신 것을 환영합니다! 이 디렉터리에는 Claude가 뛰어난 특정 능력을 보여주는 가이드 모음이 있습니다. 각 가이드는 특정 능력을 깊이 살펴보며 가능한 사용 사례, 결과를 최적화하는 prompt engineering 기법 및 Claude의 성능 평가 방식을 논의합니다.

## 가이드

- **[Claude로 Classification하기](./classification/guide.ipynb)**: 특히 복잡한 업무 규칙과 제한된 학습 데이터가 있는 상황에서 Claude가 classification 작업을 혁신하는 방법을 알아보세요. 데이터 준비, retrieval-augmented generation (RAG)을 사용한 prompt engineering, 테스트 및 평가를 안내합니다.

- **[Claude를 사용한 Retrieval Augmented Generation](./retrieval_augmented_generation/guide.ipynb)**: RAG로 분야별 지식을 제공하여 Claude의 능력을 향상시키는 방법을 알아보세요. RAG 시스템을 처음부터 구축하고 성능을 최적화하며 평가 suite를 생성하는 방법을 보여줍니다. Summary indexing 및 re-ranking 같은 기법이 질의응답 작업의 precision, recall 및 전반적인 정확도를 크게 개선하는 방식을 학습합니다.

- **[Contextual Embedding을 사용한 Retrieval Augmented Generation](./contextual-embeddings/guide.ipynb)**: 새로운 기법으로 RAG 시스템 성능을 개선하는 방법을 알아보세요. 기존 RAG에서는 효율적인 retrieval을 위해 문서를 작은 chunk로 나누는 것이 일반적입니다. 여러 애플리케이션에서 잘 작동하지만 개별 chunk에 충분한 context가 없으면 문제가 생길 수 있습니다. Contextual Embedding은 embedding 전에 각 chunk에 관련 context를 추가하여 해결합니다. Semantic search, BM25 search 및 reranking과 contextual embedding을 함께 사용하여 성능을 개선하는 방법을 학습합니다.

- **[Claude로 요약하기](./summarization/guide.ipynb)**: 여러 출처의 정보를 요약하고 종합하는 Claude의 능력을 살펴보세요. Multi-shot, 분야 기반 및 chunking 방법 등 다양한 요약 기법과 긴 콘텐츠 및 여러 문서를 처리하는 전략을 다룹니다. 예술, 주관성 및 적절한 접근 방식 사이의 균형일 수 있는 요약 평가도 살펴봅니다!

- **[Claude를 사용한 Text-to-SQL](./text_to_sql/guide.ipynb)**: Prompting 기법, self-improvement 및 RAG로 자연어에서 복잡한 SQL query를 생성하는 방법을 다룹니다. Syntax, 데이터 정확성, 행 수 등을 테스트하는 평가를 통해 생성한 SQL query의 정확도를 평가하고 개선하는 방법도 살펴봅니다.

- **[Claude로 Knowledge Graph 구축하기](./knowledge_graph/guide.ipynb)**: 비정형 텍스트에서 named entity recognition, relation extraction, entity resolution 및 multi-hop query까지 knowledge graph를 end-to-end로 구축합니다. Schema 검증을 받는 추출에 structured output을 사용하고 string-similarity heuristic 대신 Claude 기반 중복 제거를 사용합니다.

- **[Claude로 Content Policy 적용하기](./content_moderation/guide.ipynb)**: 작성된 content policy를 프로그램이 적용할 수 있는 rule로 변환합니다. Claude는 policy 문장을 검증된 JSON rule로 compile하고 각 content(텍스트 및 이미지)에서 유형이 있는 field를 추출합니다. Deterministic rule engine은 전체 audit trail과 함께 판정을 생성합니다. 광고 creative, marketplace listing 및 community content를 다룹니다.

## 시작하기

원하는 가이드 디렉터리로 이동하여 `guide.ipynb` 파일의 지침을 따르세요. 각 가이드는 독립적이며 예제와 실험을 재현하는 데 필요한 모든 코드, 데이터 및 평가 script를 포함합니다.
