"""MongoDB-on-CMA cookbook의 seed 데이터 loader.

fixture는 사전 계산된 1024차원 Voyage embedding을 가진 사기 검토 transaction 20개이며,
``example_data/mongodb_on_cma/`` 아래 plaintext로 한 줄당 JSON 하나를 저장합니다.
inline gzip+base64 blob 대신 plaintext로 제공하여 notebook을 읽기 쉽게 유지하고
긴 base64 문자열이 secret scanner에 걸리지 않게 합니다.
"""

from __future__ import annotations

import json
from pathlib import Path

# example_data/mongodb_on_cma/seed_transactions.jsonl을 이 파일 기준으로 찾아
# caller의 working directory와 관계없이 loader가 작동하게 합니다.
SEED_PATH = (
    Path(__file__).resolve().parent.parent
    / "example_data"
    / "mongodb_on_cma"
    / "seed_transactions.jsonl"
)


def load_seed(path: Path | str | None = None) -> list[dict]:
    """seed transaction을 dict 목록으로 반환합니다(JSONL 한 줄당 하나)."""
    p = Path(path) if path is not None else SEED_PATH
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
