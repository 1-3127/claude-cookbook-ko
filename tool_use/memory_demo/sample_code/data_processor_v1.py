"""
여러 동시성 및 thread-safety 문제가 있는 data processor.
여러 bug로 context editing을 시연하기 위해 Session 3에서 사용합니다.
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


class DataProcessor:
    """여러 thread-safety 문제가 있는 데이터 파일을 동시에 처리합니다."""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.processed_count = 0  # BUG: Counter의 race condition
        self.results = []  # BUG: Locking 없는 공유 list
        self.errors = {}  # BUG: Locking 없는 공유 dict
        self.lock = threading.Lock()  # 사용 가능하지만 사용하지 않습니다!

    def process_file(self, file_path: str) -> dict[str, Any]:
        """파일 하나를 처리합니다."""
        try:
            with open(file_path) as f:
                data = json.load(f)

            # 일부 처리 simulation
            processed = {
                "file": file_path,
                "record_count": len(data) if isinstance(data, list) else 1,
                "size_bytes": Path(file_path).stat().st_size,
            }

            return processed

        except Exception as e:
            return {"file": file_path, "error": str(e)}

    def process_batch(self, file_paths: list[str]) -> list[dict[str, Any]]:
        """
        여러 파일을 동시에 처리합니다.

        여러 BUG:
        1. Locking 없이 self.processed_count 증가
        2. 여러 thread에서 self.results에 추가
        3. 여러 thread에서 self.errors 수정
        4. Lock이 있지만 사용하지 않습니다!
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.process_file, fp) for fp in file_paths]

            for future in futures:
                result = future.result()

                # RACE CONDITION: Lock 없이 counter 증가
                self.processed_count += 1  # BUG!

                if "error" in result:
                    # RACE CONDITION: Lock 없이 dict 수정
                    self.errors[result["file"]] = result["error"]  # BUG!
                else:
                    # RACE CONDITION: Lock 없이 list에 추가
                    self.results.append(result)  # BUG!

        return self.results

    def get_statistics(self) -> dict[str, Any]:
        """
        처리 통계를 가져옵니다.

        BUG: Thread-safety를 보장하지 않고 shared state에 접근합니다.
        처리 중 호출하면 일관되지 않은 값을 얻을 수 있습니다.
        """
        total_files = self.processed_count
        successful = len(self.results)
        failed = len(self.errors)

        # BUG: Race condition 때문에 이 수의 합계가 올바르지 않을 수 있습니다
        return {
            "total_processed": total_files,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_files if total_files > 0 else 0,
        }

    def reset(self):
        """
        Processor state를 초기화합니다.

        BUG: Locking이 없어 처리 중 호출하면 손상을 일으킵니다.
        """
        self.processed_count = 0  # RACE CONDITION
        self.results = []  # RACE CONDITION
        self.errors = {}  # RACE CONDITION


class SharedCache:
    """
    Thread-safety 문제가 있는 공유 cache.

    BUG: 전형적인 read-modify-write race condition 패턴.
    """

    def __init__(self):
        self.cache = {}  # BUG: Locking 없는 공유 dict
        self.hit_count = 0  # BUG: Race condition
        self.miss_count = 0  # BUG: Race condition

    def get(self, key: str) -> Any:
        """Cache에서 가져오기 - hit/miss 수의 RACE CONDITION."""
        if key in self.cache:
            self.hit_count += 1  # BUG: Atomic하지 않습니다!
            return self.cache[key]
        else:
            self.miss_count += 1  # BUG: Atomic하지 않습니다!
            return None

    def set(self, key: str, value: Any):
        """Cache에 설정 - dict 수정의 RACE CONDITION."""
        self.cache[key] = value  # BUG: Dict 접근이 synchronized되지 않습니다!

    def get_stats(self) -> dict[str, Any]:
        """Cache 통계 가져오기 - 일관되지 않을 수 있습니다."""
        total = self.hit_count + self.miss_count
        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate": self.hit_count / total if total > 0 else 0,
        }


if __name__ == "__main__":
    # 테스트 파일 생성(포함되지 않음)
    processor = DataProcessor(max_workers=10)

    # 많은 파일 처리 simulation
    file_paths = [f"data/file_{i}.json" for i in range(100)]

    print("Processing files concurrently...")
    results = processor.process_batch(file_paths)

    print(f"\nStatistics: {processor.get_statistics()}")
    print("\nNote: Counts may be inconsistent due to race conditions!")
