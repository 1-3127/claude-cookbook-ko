"""
Mutable default argument bug가 있는 cache manager.
Python에서 가장 흔한 함정 중 하나입니다.
"""

from datetime import datetime
from typing import Any


class CacheManager:
    """TTL을 지원하여 cache된 데이터를 관리합니다."""

    def __init__(self):
        self.cache = {}

    def add_items(
        self,
        key: str,
        items: list[str] = None,  # BUG: Mutable default argument!
    ) -> None:
        """
        Cache에 항목을 추가합니다.

        BUG: []를 기본값으로 사용하면 모든 호출이 공유하는 list를 만듭니다!
        Python의 고전적인 함정 중 하나입니다.
        """
        # Items를 제공하지 않는 모든 호출이 items list를 공유합니다
        if items is None:
            items = []
        items.append(f"Added at {datetime.now()}")
        self.cache[key] = items

    def add_items_fixed(self, key: str, items: list[str] | None = None) -> None:
        """기본값을 올바르게 처리하여 항목을 추가합니다."""
        if items is None:
            items = []
        items = items.copy()  # Mutation을 피하기 위해 복사본도 만듭니다
        items.append(f"Added at {datetime.now()}")
        self.cache[key] = items

    def merge_configs(
        self,
        name: str,
        overrides: dict[str, Any] = None,  # BUG: Mutable default!
    ) -> dict[str, Any]:
        """
        설정을 overrides와 병합합니다.

        BUG: 모든 호출이 기본 dict를 공유합니다!
        """
        if overrides is None:
            overrides = {}
        defaults = {"timeout": 30, "retries": 3, "cache_enabled": True}

        # 공유 overrides dict를 수정합니다
        overrides.update(defaults)
        return overrides

    def merge_configs_fixed(
        self, name: str, overrides: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """설정을 올바르게 병합합니다."""
        if overrides is None:
            overrides = {}

        defaults = {"timeout": 30, "retries": 3, "cache_enabled": True}

        # Mutation을 피하기 위해 새 dict 생성
        result = {**defaults, **overrides}
        return result


class DataProcessor:
    """Mutable default bug의 또 다른 예제."""

    def process_batch(
        self,
        data: list[int],
        filters: list[str] = None,  # BUG: Mutable default!
    ) -> list[int]:
        """
        선택적 filter로 데이터를 처리합니다.

        BUG: 호출들이 filters list를 공유합니다!
        """
        if filters is None:
            filters = []
        filters.append("default_filter")  # 공유 list를 수정합니다!

        result = []
        for item in data:
            if "positive" in filters and item < 0:
                continue
            result.append(item * 2)
        return result


if __name__ == "__main__":
    cache = CacheManager()

    # Bug 시연
    print("=== Demonstrating Mutable Default Argument Bug ===\n")

    # Items 없이 첫 번째 호출
    cache.add_items("key1")
    print(f"key1: {cache.cache['key1']}")

    # Items 없이 두 번째 호출 - 놀랍게도 같은 list를 받습니다!
    cache.add_items("key2")
    print(f"key2: {cache.cache['key2']}")  # Timestamp가 두 개가 됩니다!

    # 세 번째 호출 - 더 나빠집니다!
    cache.add_items("key3")
    print(f"key3: {cache.cache['key3']}")  # Timestamp가 세 개가 됩니다!

    print("\nAll keys share the same list object!")
    print(f"key1 is key2: {cache.cache['key1'] is cache.cache['key2']}")

    print("\n=== Using Fixed Version ===\n")
    cache2 = CacheManager()
    cache2.add_items_fixed("key1")
    cache2.add_items_fixed("key2")
    cache2.add_items_fixed("key3")
    print(f"key1: {cache2.cache['key1']}")
    print(f"key2: {cache2.cache['key2']}")
    print(f"key3: {cache2.cache['key3']}")
    print(f"\nkey1 is key2: {cache2.cache['key1'] is cache2.cache['key2']}")
