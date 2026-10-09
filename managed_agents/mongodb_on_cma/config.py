"""MongoDB-on-CMA cookbook의 공유 설정.

retrieval, tool, AP2 module에서 사용하는 조절값, index 이름, 한도, server version 확인입니다.
다른 모든 module이 자유롭게 의존할 수 있도록 import를 가볍게 유지합니다.
"""

from __future__ import annotations

DEFAULT_MODEL = "claude-haiku-4-5"
EMBED_MODEL = "voyage-4-large"
EMBED_DIM = 1024
RERANK_MODEL = "rerank-2.5"
DECIDED_STATUSES = ("approved", "rejected", "escalated", "completed")
VECTOR_INDEX_NAME = "transactions_vector_index"
SEARCH_INDEX_NAME = "transactions_search_index"
LEXICAL_PATHS = ["text", "sender.name", "recipient.name"]
PROJECT_FIELDS = ["transaction_id", "text", "amount", "sender", "recipient", "decision"]
# MONGO_URI는 필수입니다. 이 cookbook이 소유하는 host 측 data path입니다.
# Anthropic 인증은 의도적으로 필수가 아닙니다. SDK가 API key, auth token 또는
# profile(예: `ant` CLI workload-identity federation)을 결정하므로
# ANTHROPIC_API_KEY만 요구하는 대신 해당 신호가 있는지 유연하게 확인합니다.
REQUIRED_ENV = ("MONGO_URI",)
ANTHROPIC_AUTH_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE")

ATLAS_EMBEDDINGS_URL = "https://ai.mongodb.com/v1/embeddings"
ATLAS_RERANK_URL = "https://ai.mongodb.com/v1/rerank"


class EmbeddingDimensionMismatch(RuntimeError): ...


class IndexTimeout(RuntimeError): ...


def _parse_major_minor(version: str) -> tuple[int, int]:
    parts = str(version).split(".")
    try:
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        return (0, 0)


def supports_rank_fusion(version: str) -> bool:
    return _parse_major_minor(version) >= (8, 0)
