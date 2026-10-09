#!/usr/bin/env python3
"""
TechStart Inc용 Hiring Impact Calculator
Engineer 채용의 재무 영향을 계산합니다
"""

import json
import sys


def calculate_hiring_impact(
    num_engineers: int, salary_per_engineer: int = 200000
) -> dict[str, int | float | str]:
    """
    Engineer 채용의 재무 영향을 계산합니다.

    Args:
        num_engineers: 채용할 engineer 수
        salary_per_engineer: Engineer당 연봉(기본값: $200K)

    Returns:
        재무 영향 metrics의 dictionary
    """
    # 현재 재무 정보(CLAUDE.md에서 가져옴)
    CURRENT_BURN_MONTHLY = 500000  # $500K/월
    CURRENT_RUNWAY_MONTHS = 20  # 20개월
    CASH_IN_BANK = 10000000  # $10M

    # 총부담 비용 계산(급여 + 복리후생 + 세금 = 급여 * 1.3)
    annual_loaded_cost_per_engineer = salary_per_engineer * 1.3
    monthly_cost_per_engineer = annual_loaded_cost_per_engineer / 12

    # 총 월 비용 증가
    total_monthly_increase = monthly_cost_per_engineer * num_engineers

    # 새로운 burn rate
    new_burn_monthly = CURRENT_BURN_MONTHLY + total_monthly_increase

    # 새로운 runway
    new_runway_months = CASH_IN_BANK / new_burn_monthly
    runway_reduction_months = CURRENT_RUNWAY_MONTHS - new_runway_months

    # 잠재적 매출 영향 계산(가정: engineer가 velocity를 15% 증가)
    velocity_increase = 0.15 * num_engineers / 5  # Engineer 5명 = 15% 증가로 가정

    # 권고
    if runway_reduction_months > 3:
        recommendation = "HIGH RISK: Significant runway reduction. Consider phased hiring."
    elif runway_reduction_months > 1.5:
        recommendation = "MODERATE RISK: Manageable if revenue growth accelerates."
    else:
        recommendation = "LOW RISK: Minimal impact on runway. Proceed if talent is available."

    return {
        "num_engineers": num_engineers,
        "salary_per_engineer": salary_per_engineer,
        "monthly_cost_per_engineer": round(monthly_cost_per_engineer, 2),
        "total_monthly_increase": round(total_monthly_increase, 2),
        "current_burn_monthly": CURRENT_BURN_MONTHLY,
        "new_burn_monthly": round(new_burn_monthly, 2),
        "current_runway_months": CURRENT_RUNWAY_MONTHS,
        "new_runway_months": round(new_runway_months, 2),
        "runway_reduction_months": round(runway_reduction_months, 2),
        "velocity_increase_percent": round(velocity_increase * 100, 1),
        "recommendation": recommendation,
    }


def main() -> None:
    # command line argument 파싱
    if len(sys.argv) < 2:
        print("Usage: python hiring_impact.py <num_engineers> [salary_per_engineer]")
        sys.exit(1)

    num_engineers = int(sys.argv[1])
    salary = int(sys.argv[2]) if len(sys.argv) > 2 else 200000

    # 영향 계산
    impact = calculate_hiring_impact(num_engineers, salary)

    # 쉽게 parsing하도록 JSON 출력
    print(json.dumps(impact, indent=2))

    # 요약도 출력
    print("\n=== HIRING IMPACT SUMMARY ===")
    print(f"Hiring {impact['num_engineers']} engineers at ${impact['salary_per_engineer']:,}/year")
    print(f"Monthly burn increase: ${impact['total_monthly_increase']:,.0f}")
    print(f"New burn rate: ${impact['new_burn_monthly']:,.0f}/month")
    print(
        f"Runway change: {impact['current_runway_months']:.1f} → {impact['new_runway_months']:.1f} months"
    )
    print(f"Velocity increase: +{impact['velocity_increase_percent']}%")
    print(f"\n{impact['recommendation']}")


if __name__ == "__main__":
    main()
