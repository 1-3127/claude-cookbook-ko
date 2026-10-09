"""MongoDB Atlas 설정 helper + 공유 문서 builder.

notebook이 가르치는 대신 import하는 설정 boilerplate입니다. collection에 초기 데이터를
넣고, vector + Atlas Search index를 만들어 query 가능하고 동기화될 때까지 기다리며,
사전 확인을 수행합니다. notebook의 `record_decision` handler와 AP2 module이 공유하는
작은 ID/timestamp 및 decision/audit 문서 구성 함수도 있습니다. retrieval pipeline builder와
custom tool handler 자체는 이제 notebook 안에 있습니다(학습 내용). `pymongo`는 여전히
경계의 당신 측에서만 실행됩니다.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

from .config import (
    ANTHROPIC_AUTH_ENV,
    DEFAULT_MODEL,
    EMBED_DIM,
    REQUIRED_ENV,
    SEARCH_INDEX_NAME,
    VECTOR_INDEX_NAME,
    IndexTimeout,
)


def _new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _now():
    return datetime.now(UTC)


def build_decision_doc(
    transaction_id,
    decision,
    *,
    confidence,
    risk_factors,
    reasoning,
    reviewed_by,
    decision_id=None,
    created_at=None,
) -> dict:
    return {
        "decision_id": decision_id or _new_id("dec"),
        "transaction_id": transaction_id,
        "decision": decision,
        "confidence_score": confidence,
        "risk_factors": list(risk_factors),
        "reasoning": reasoning,
        "reviewed_by": reviewed_by,
        "created_at": created_at or _now(),
    }


def build_audit_event(
    event_type,
    transaction_id,
    *,
    decision_id=None,
    severity="info",
    event_data=None,
    event_id=None,
    timestamp=None,
) -> dict:
    return {
        "event_id": event_id or _new_id("evt"),
        "timestamp": timestamp or _now(),
        "event_type": event_type,
        "transaction_id": transaction_id,
        "decision_id": decision_id,
        "severity": severity,
        "event_data": event_data or {},
    }


def resolve_model(env=None) -> str:
    import os

    return (env if env is not None else os.environ).get("COOKBOOK_MODEL", DEFAULT_MODEL)


def missing_required_env(env=None) -> list[str]:
    import os

    source = env if env is not None else os.environ
    return [name for name in REQUIRED_ENV if not source.get(name)]


def has_anthropic_auth(env=None) -> bool:
    """Anthropic 인증 신호(API key, auth token, profile)가 있으면 True입니다.

    API key가 아닌 인증(예: `ant` CLI workload-identity federation)도 유효하므로
    유연한 확인입니다. False면 차단하지 말고 경고해야 합니다. SDK는 여전히 credential을
    스스로 결정합니다.
    """
    import os

    source = env if env is not None else os.environ
    return any(source.get(name) for name in ANTHROPIC_AUTH_ENV)


def server_version(coll) -> str:
    return str(coll.database.command("buildInfo").get("version", "0.0"))


def prepare_seed(docs, *, now) -> list[dict]:
    prepared = []
    for doc in docs:
        doc = dict(doc)
        days = doc.pop("created_days_ago", 0)
        doc["created_at"] = now - timedelta(days=days)
        prepared.append(doc)
    return prepared


def seed_collection(coll, docs) -> int:
    coll.delete_many({})
    if docs:
        coll.insert_many(list(docs))
    return coll.count_documents({})


def ensure_indexes(
    coll, *, dim=EMBED_DIM, poll_interval=2.0, timeout_s=180.0, sleep=None, monotonic=None
) -> None:
    sleep = sleep or time.sleep
    monotonic = monotonic or time.monotonic
    coll.create_index("transaction_id", unique=True)
    existing = {idx["name"] for idx in coll.list_search_indexes()}
    if VECTOR_INDEX_NAME not in existing:
        coll.create_search_index(vector_index_model(dim))
    if SEARCH_INDEX_NAME not in existing:
        coll.create_search_index(search_index_model())
    deadline = monotonic() + timeout_s
    names = (VECTOR_INDEX_NAME, SEARCH_INDEX_NAME)
    while True:
        status = {idx["name"]: idx for idx in coll.list_search_indexes()}
        if all(status.get(n, {}).get("queryable") is True for n in names):
            break
        if monotonic() >= deadline:
            pending = [n for n in names if status.get(n, {}).get("queryable") is not True]
            raise IndexTimeout(f"indexes not queryable within {timeout_s}s: {pending}")
        sleep(poll_interval)
    # 새로 넣은 write를 수집하기 전에 `queryable`이 true가 되어 여기서 query하면
    # 조용히 빈 결과를 반환할 수 있습니다. 두 index가 초기 문서를 실제로 반영할 때까지 기다립니다.
    wait_for_index_sync(
        coll, deadline=deadline, poll_interval=poll_interval, sleep=sleep, monotonic=monotonic
    )


def wait_for_index_sync(
    coll, *, deadline=None, timeout_s=180.0, poll_interval=2.0, sleep=None, monotonic=None
) -> None:
    """Atlas Search index가 현재 문서를 반영할 때까지 기다립니다.

    Atlas Search와 Vector Search는 eventually consistent입니다. index는 정의가
    만들어지면 바로 ``queryable``을 보고하지만 최신 write를 수집하기 *전*일 수 있습니다.
    그 사이에 query하면 데이터가 있어도 빈 결과를 반환합니다. vector probe와
    lexical ``exists`` probe를 둘 다 hit를 반환할 때까지(또는 collection이 실제로 비어
    있을 때까지) polling하여 caller가 지연된 index를 query하지 않게 합니다.
    """
    sleep = sleep or time.sleep
    monotonic = monotonic or time.monotonic
    if deadline is None:
        deadline = monotonic() + timeout_s
    probe = coll.find_one({}, {"embedding": 1})
    if probe is None:
        return  # 초기 데이터 없음; 기다릴 것 없음
    qvec = probe["embedding"]
    vector_probe = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": qvec,
                "numCandidates": 100,
                "limit": 1,
            }
        },
        {"$limit": 1},
    ]
    lexical_probe = [
        {"$search": {"index": SEARCH_INDEX_NAME, "exists": {"path": "text"}}},
        {"$limit": 1},
    ]
    while True:
        vector_ready = bool(list(coll.aggregate(vector_probe)))
        lexical_ready = bool(list(coll.aggregate(lexical_probe)))
        if vector_ready and lexical_ready:
            return
        if monotonic() >= deadline:
            lagging = [
                name
                for name, ready in (
                    (VECTOR_INDEX_NAME, vector_ready),
                    (SEARCH_INDEX_NAME, lexical_ready),
                )
                if not ready
            ]
            raise IndexTimeout(f"indexes not reflecting seeded docs within timeout: {lagging}")
        sleep(poll_interval)


def vector_index_model(dim=EMBED_DIM) -> dict:
    return {
        "name": VECTOR_INDEX_NAME,
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": dim,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "status"},
            ]
        },
    }


def search_index_model() -> dict:
    return {
        "name": SEARCH_INDEX_NAME,
        "type": "search",
        "definition": {"mappings": {"dynamic": True}},
    }


def preflight(coll, *, expected_dim=EMBED_DIM) -> dict:
    issues: list[str] = []
    try:
        coll.database.command("ping")
    except Exception as exc:
        return {
            "ok": False,
            "issues": [f"cannot reach MongoDB (check MONGO_URI / IP allowlist): {exc}"],
        }
    indexes = {idx["name"]: idx for idx in coll.list_search_indexes()}
    for name in (VECTOR_INDEX_NAME, SEARCH_INDEX_NAME):
        index = indexes.get(name)
        if index is None:
            issues.append(
                f"missing MongoDB Atlas Search index '{name}' — create it, then wait until queryable"
            )
        elif index.get("queryable") is not True:
            issues.append(f"index '{name}' is still building — wait until it is queryable")
    vector_index = indexes.get(VECTOR_INDEX_NAME)
    if vector_index is not None:
        definition = vector_index.get("latestDefinition") or vector_index.get("definition") or {}
        if not any(
            f.get("type") == "filter" and f.get("path") == "status"
            for f in definition.get("fields", [])
        ):
            issues.append(
                "vector index is missing a `status` filter field — recreate from vector_index_model()"
            )
    return {"ok": not issues, "issues": issues}
