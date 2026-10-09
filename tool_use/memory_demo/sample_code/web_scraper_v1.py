"""
Race condition bug가 있는 동시 web scraper.
여러 thread가 synchronization 없이 shared state를 수정합니다.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests


class WebScraper:
    """여러 URL을 동시에 조회하는 web scraper."""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.results = []  # BUG: 여러 thread가 shared mutable state에 접근합니다!
        self.failed_urls = []  # BUG: 또 다른 race condition!

    def fetch_url(self, url: str) -> dict[str, Any]:
        """URL 하나를 조회하여 결과를 반환합니다."""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return {
                "url": url,
                "status": response.status_code,
                "content_length": len(response.content),
            }
        except requests.exceptions.RequestException as e:
            return {"url": url, "error": str(e)}

    def scrape_urls(self, urls: list[str]) -> list[dict[str, Any]]:
        """
        여러 URL을 동시에 scrape합니다.

        BUG: 여러 thread가 locking 없이 self.results에 접근합니다!
        이로 인해 결과가 손실되거나 손상될 수 있는 race condition이 발생합니다.
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.fetch_url, url) for url in urls]

            for future in as_completed(futures):
                result = future.result()

                # RACE CONDITION: 여러 thread가 동시에 self.results에 추가
                if "error" in result:
                    self.failed_urls.append(result["url"])  # RACE CONDITION
                else:
                    self.results.append(result)  # RACE CONDITION

        return self.results

    def get_stats(self) -> dict[str, int]:
        """Scraping 통계를 가져옵니다."""
        return {
            "total_results": len(self.results),
            "failed_urls": len(self.failed_urls),
            "success_rate": (
                len(self.results) / (len(self.results) + len(self.failed_urls))
                if (len(self.results) + len(self.failed_urls)) > 0
                else 0
            ),
        }


if __name__ == "__main__":
    # 여러 URL로 테스트
    urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/status/200",
        "https://httpbin.org/status/404",
        "https://httpbin.org/delay/2",
        "https://httpbin.org/status/500",
    ] * 10  # Race condition 확률을 높이기 위해 총 URL 50개

    scraper = WebScraper(max_workers=10)
    results = scraper.scrape_urls(urls)

    print("Expected: 50 results")
    print(f"Got: {len(results)} results")
    print(f"Stats: {scraper.get_stats()}")
    print("\nNote: Results count may be less than expected due to race condition!")
