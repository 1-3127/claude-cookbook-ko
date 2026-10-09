"""MongoDB-on-CMA: 사기 검토 agent cookbook의 설정 boilerplate.

notebook에 학습용 코드가 있습니다. retrieval pipeline builder, custom tool handler,
`requires_action` gate 루프가 모두 내부에 정의되어 있습니다. 이 package는 notebook이
가르치는 대신 import하는 실제 boilerplate 요소만 보관합니다.

- ``config``       — 조절값, index 이름, server version 확인
- ``embeddings``   — Atlas AI / Voyage embedding + rerank client
- ``tools``        — Atlas 설정(seed, index, 사전 확인) + 공유 decision/audit 문서 구성 함수
- ``ap2_mandates`` — AP2(Agent Payments Protocol) mandate 서명/검증(암호학 black box)
- ``seed``         — plaintext 예제 데이터 fixture 불러오기
"""

from __future__ import annotations

from .config import (
    DEFAULT_MODEL,
    EMBED_DIM,
    EMBED_MODEL,
    RERANK_MODEL,
    EmbeddingDimensionMismatch,
    IndexTimeout,
    supports_rank_fusion,
)
from .embeddings import (
    AtlasEmbeddingClient,
    embed_documents,
    embed_query,
    make_embedding_client,
    rerank,
)
from .seed import load_seed
from .tools import (
    build_audit_event,
    build_decision_doc,
    ensure_indexes,
    has_anthropic_auth,
    missing_required_env,
    preflight,
    prepare_seed,
    resolve_model,
    search_index_model,
    seed_collection,
    server_version,
    vector_index_model,
    wait_for_index_sync,
)

__all__ = [
    "AtlasEmbeddingClient",
    "DEFAULT_MODEL",
    "EMBED_DIM",
    "EMBED_MODEL",
    "EmbeddingDimensionMismatch",
    "IndexTimeout",
    "RERANK_MODEL",
    "build_audit_event",
    "build_decision_doc",
    "embed_documents",
    "embed_query",
    "ensure_indexes",
    "has_anthropic_auth",
    "load_seed",
    "make_embedding_client",
    "missing_required_env",
    "preflight",
    "prepare_seed",
    "rerank",
    "resolve_model",
    "search_index_model",
    "seed_collection",
    "server_version",
    "supports_rank_fusion",
    "vector_index_model",
    "wait_for_index_sync",
]
