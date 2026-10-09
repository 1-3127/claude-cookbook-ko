# Claude Managed Agents의 MongoDB

[**MongoDB Atlas와 Claude Managed Agents를 사용하는 사기 검토 agent**](../CMA_with_mongodb_atlas.ipynb) cookbook의 설정 boilerplate입니다. **학습용 코드는 notebook 안에 있습니다.** 네 retrieval pipeline builder, custom tool handler, `requires_action` gate 루프가 모두 거기에 정의되어 있습니다. 이 package는 notebook에서 읽기보다는 import하는 요소만 보관합니다.

| Module | 내용 |
| --- | --- |
| [`config.py`](config.py) | 조절값, index 이름, MongoDB server version 확인(`supports_rank_fusion`). |
| [`embeddings.py`](embeddings.py) | MongoDB Atlas AI endpoint를 `voyageai` 인터페이스에 맞추는 embedding + rerank client로, cookbook이 provider에 구애받지 않게 합니다. |
| [`tools.py`](tools.py) | MongoDB Atlas 설정 — collection 초기 데이터 넣기, vector + Atlas Search index 생성과 query 가능하고 동기화될 때까지 대기, 사전 확인 — 및 notebook의 `record_decision` handler와 AP2 module이 사용하는 공유 decision/audit 문서 구성 함수. |
| [`ap2_mandates.py`](ap2_mandates.py) | AP2(Agent Payments Protocol) mandate 서명과 검증(ES256 JWT) — notebook이 `verify_mandates`로 호출하고 판정에 따라 행동하는 암호학 black box. |
| [`seed.py`](seed.py) | [`../example_data/mongodb_on_cma/`](../example_data/mongodb_on_cma/seed_transactions.jsonl)의 plaintext fixture를 불러옵니다. |

MongoDB credential(`MONGO_URI`)은 경계의 당신 측에만 있습니다. `pymongo`는 notebook의 host 측 handler에서 실행되고 agent context나 sandbox에서는 전혀 실행되지 않습니다. 연결 패턴과 전체 사기 검토 agent는 cookbook을 참고하세요.

