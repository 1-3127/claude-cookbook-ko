#!/usr/bin/env python3
"""
Financial Forecast Tool - 전략적 결정을 위한 고급 재무 model링
Chief of Staff agent가 Bash로 실행하는 custom Python tool
"""

import argparse
import json
from typing import Any


def forecast_financials(
    current_arr: float, growth_rate: float, months: int, burn_rate: float
) -> dict[str, Any]:
    """여러 시나리오로 재무 예측을 생성합니다"""

    forecasts: dict[str, Any] = {
        "base_case": [],
        "optimistic": [],
        "pessimistic": [],
        "metrics": {},
    }

    # 기본 시나리오
    arr = current_arr
    for month in range(1, months + 1):
        arr = arr * (1 + growth_rate)
        monthly_revenue = arr / 12
        net_burn = burn_rate - monthly_revenue
        runway = -1 if net_burn <= 0 else (10_000_000 / net_burn)  # 은행 현금 $10M 가정

        forecasts["base_case"].append(
            {
                "month": month,
                "arr": round(arr),
                "monthly_revenue": round(monthly_revenue),
                "net_burn": round(net_burn),
                "runway_months": round(runway, 1) if runway > 0 else "infinite",
            }
        )

    # 낙관적(성장 1.5배)
    arr = current_arr
    for month in range(1, months + 1):
        arr = arr * (1 + growth_rate * 1.5)
        forecasts["optimistic"].append({"month": month, "arr": round(arr)})

    # 비관적(성장 0.5배)
    arr = current_arr
    for month in range(1, months + 1):
        arr = arr * (1 + growth_rate * 0.5)
        forecasts["pessimistic"].append({"month": month, "arr": round(arr)})

    # 핵심 metrics
    forecasts["metrics"] = {
        "months_to_profitability": calculate_profitability_date(forecasts["base_case"]),
        "cash_required": calculate_cash_needed(forecasts["base_case"]),
        "break_even_arr": burn_rate * 12,
        "current_burn_multiple": round(burn_rate / (current_arr / 12), 2),
    }

    return forecasts


def calculate_profitability_date(forecast: list[dict[str, Any]]) -> int:
    """회사가 수익성을 달성하는 시점을 찾습니다"""
    for entry in forecast:
        if entry["net_burn"] <= 0:
            return int(entry["month"])
    return -1  # 예측 기간 내 수익성 달성하지 못함


def calculate_cash_needed(forecast: list[dict[str, Any]]) -> int:
    """수익성 달성까지 필요한 총현금을 계산합니다"""
    total_burn = 0
    for entry in forecast:
        if entry["net_burn"] > 0:
            total_burn += entry["net_burn"]
        else:
            break
    return round(total_burn)


def main() -> None:
    parser = argparse.ArgumentParser(description="Financial forecasting tool")
    parser.add_argument("--arr", type=float, default=2400000, help="Current ARR")
    parser.add_argument("--growth", type=float, default=0.15, help="Monthly growth rate")
    parser.add_argument("--months", type=int, default=12, help="Forecast period")
    parser.add_argument("--burn", type=float, default=500000, help="Monthly burn rate")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")

    args = parser.parse_args()

    forecast = forecast_financials(args.arr, args.growth, args.months, args.burn)

    if args.format == "json":
        print(json.dumps(forecast, indent=2))
    else:
        # 사람이 읽기 위한 text 출력
        print("📊 FINANCIAL FORECAST")
        print("=" * 50)
        print(f"Current ARR: ${args.arr:,.0f}")
        print(f"Growth Rate: {args.growth * 100:.1f}% monthly")
        print(f"Burn Rate: ${args.burn:,.0f}/month")
        print()

        print("BASE CASE PROJECTION:")
        print("-" * 30)
        for i in [2, 5, 11]:  # 3, 6, 12개월 차 표시
            if i < len(forecast["base_case"]):
                m = forecast["base_case"][i]
                print(f"Month {m['month']:2}: ARR ${m['arr']:,} | Runway {m['runway_months']}")

        print()
        print("KEY METRICS:")
        print("-" * 30)
        metrics = forecast["metrics"]
        if metrics["months_to_profitability"] > 0:
            print(f"Profitability: Month {metrics['months_to_profitability']}")
        else:
            print("Profitability: Not in forecast period")
        print(f"Cash Needed: ${metrics['cash_required']:,}")
        print(f"Burn Multiple: {metrics['current_burn_multiple']}x")

        print()
        print("SCENARIO ANALYSIS:")
        print("-" * 30)
        last_base = forecast["base_case"][-1]["arr"]
        last_opt = forecast["optimistic"][-1]["arr"]
        last_pess = forecast["pessimistic"][-1]["arr"]
        print(f"12-Month ARR: ${last_pess:,} to ${last_opt:,}")
        print(f"Range: {((last_opt - last_pess) / last_base * 100):.0f}% variance")


if __name__ == "__main__":
    main()
