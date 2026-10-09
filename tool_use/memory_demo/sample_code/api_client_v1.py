"""
비슷한 동시성 문제가 있는 async API client.
Claude가 thread-safety 패턴을 async 코드에 적용하는 모습을 보여줍니다.
"""

import asyncio
from typing import Any

import aiohttp


class AsyncAPIClient:
    """여러 endpoint에서 데이터를 가져오는 async API client."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.responses = []  # BUG: 여러 coroutine이 shared state에 접근합니다!
        self.error_count = 0  # BUG: Counter 증가 시 race condition!

    async def fetch_endpoint(self, session: aiohttp.ClientSession, endpoint: str) -> dict[str, Any]:
        """Endpoint 하나를 조회합니다."""
        url = f"{self.base_url}/{endpoint}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                data = await response.json()
                return {
                    "endpoint": endpoint,
                    "status": response.status,
                    "data": data,
                }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "error": str(e),
            }

    async def fetch_all(self, endpoints: list[str]) -> list[dict[str, Any]]:
        """
        여러 endpoint를 동시에 조회합니다.

        BUG: Threading 문제와 비슷하게 여러 coroutine이
        조정 없이 self.responses와 self.error_count를 수정합니다!
        Python의 GIL이 thread의 일부 race condition을 방지하더라도
        async 코드는 여전히 interleaving 문제가 있을 수 있습니다.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_endpoint(session, endpoint) for endpoint in endpoints]

            for coro in asyncio.as_completed(tasks):
                result = await coro

                # RACE CONDITION: 여러 coroutine이 shared state 수정
                if "error" in result:
                    self.error_count += 1  # Atomic하지 않습니다!
                else:
                    self.responses.append(result)  # Async context에서 thread-safe하지 않습니다!

        return self.responses

    def get_summary(self) -> dict[str, Any]:
        """요약 통계를 가져옵니다."""
        return {
            "total_responses": len(self.responses),
            "errors": self.error_count,
            "success_rate": (
                len(self.responses) / (len(self.responses) + self.error_count)
                if (len(self.responses) + self.error_count) > 0
                else 0
            ),
        }


async def main():
    """Async API client를 테스트합니다."""
    client = AsyncAPIClient("https://jsonplaceholder.typicode.com")

    endpoints = [
        "posts/1",
        "posts/2",
        "posts/3",
        "users/1",
        "users/2",
        "invalid/endpoint",  # 오류 발생
    ] * 20  # 총 요청 120개

    results = await client.fetch_all(endpoints)

    print("Expected: ~100 successful responses")
    print(f"Got: {len(results)} responses")
    print(f"Summary: {client.get_summary()}")
    print("\nNote: Counts may be incorrect due to race conditions!")


if __name__ == "__main__":
    asyncio.run(main())
