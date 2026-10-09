"""
재무 비율 해석 module입니다.
업계 benchmark와 맥락적 분석을 제공합니다.
"""

from typing import Any


class RatioInterpreter:
    """업계 맥락으로 재무 비율을 해석합니다."""

    # 업계 benchmark 범위(시연을 위해 간소화)
    BENCHMARKS = {
        "technology": {
            "current_ratio": {"excellent": 2.5, "good": 1.8, "acceptable": 1.2, "poor": 1.0},
            "debt_to_equity": {"excellent": 0.3, "good": 0.5, "acceptable": 1.0, "poor": 2.0},
            "roe": {"excellent": 0.25, "good": 0.18, "acceptable": 0.12, "poor": 0.08},
            "gross_margin": {"excellent": 0.70, "good": 0.50, "acceptable": 0.35, "poor": 0.20},
            "pe_ratio": {"undervalued": 15, "fair": 25, "growth": 35, "expensive": 50},
        },
        "retail": {
            "current_ratio": {"excellent": 2.0, "good": 1.5, "acceptable": 1.0, "poor": 0.8},
            "debt_to_equity": {"excellent": 0.5, "good": 0.8, "acceptable": 1.5, "poor": 2.5},
            "roe": {"excellent": 0.20, "good": 0.15, "acceptable": 0.10, "poor": 0.05},
            "gross_margin": {"excellent": 0.40, "good": 0.30, "acceptable": 0.20, "poor": 0.10},
            "pe_ratio": {"undervalued": 12, "fair": 18, "growth": 25, "expensive": 35},
        },
        "financial": {
            "current_ratio": {"excellent": 1.5, "good": 1.2, "acceptable": 1.0, "poor": 0.8},
            "debt_to_equity": {"excellent": 1.0, "good": 2.0, "acceptable": 4.0, "poor": 6.0},
            "roe": {"excellent": 0.15, "good": 0.12, "acceptable": 0.08, "poor": 0.05},
            "pe_ratio": {"undervalued": 10, "fair": 15, "growth": 20, "expensive": 30},
        },
        "manufacturing": {
            "current_ratio": {"excellent": 2.2, "good": 1.7, "acceptable": 1.3, "poor": 1.0},
            "debt_to_equity": {"excellent": 0.4, "good": 0.7, "acceptable": 1.2, "poor": 2.0},
            "roe": {"excellent": 0.18, "good": 0.14, "acceptable": 0.10, "poor": 0.06},
            "gross_margin": {"excellent": 0.35, "good": 0.25, "acceptable": 0.18, "poor": 0.12},
            "pe_ratio": {"undervalued": 14, "fair": 20, "growth": 28, "expensive": 40},
        },
        "healthcare": {
            "current_ratio": {"excellent": 2.3, "good": 1.8, "acceptable": 1.4, "poor": 1.0},
            "debt_to_equity": {"excellent": 0.3, "good": 0.6, "acceptable": 1.0, "poor": 1.8},
            "roe": {"excellent": 0.22, "good": 0.16, "acceptable": 0.11, "poor": 0.07},
            "gross_margin": {"excellent": 0.65, "good": 0.45, "acceptable": 0.30, "poor": 0.20},
            "pe_ratio": {"undervalued": 18, "fair": 28, "growth": 40, "expensive": 55},
        },
    }

    def __init__(self, industry: str = "general"):
        """
        업계 맥락으로 interpreter를 초기화합니다.

        Args:
            industry: benchmarking할 업계 sector
        """
        self.industry = industry.lower()
        self.benchmarks = self.BENCHMARKS.get(self.industry, self._get_general_benchmarks())

    def _get_general_benchmarks(self) -> dict[str, Any]:
        """업계에 종속되지 않는 일반 benchmark를 얻습니다."""
        return {
            "current_ratio": {"excellent": 2.0, "good": 1.5, "acceptable": 1.0, "poor": 0.8},
            "debt_to_equity": {"excellent": 0.5, "good": 1.0, "acceptable": 1.5, "poor": 2.5},
            "roe": {"excellent": 0.20, "good": 0.15, "acceptable": 0.10, "poor": 0.05},
            "gross_margin": {"excellent": 0.40, "good": 0.30, "acceptable": 0.20, "poor": 0.10},
            "pe_ratio": {"undervalued": 15, "fair": 22, "growth": 30, "expensive": 45},
        }

    def interpret_ratio(self, ratio_name: str, value: float) -> dict[str, Any]:
        """
        맥락과 함께 비율 하나를 해석합니다.

        Args:
            ratio_name: 비율 이름
            value: 계산한 비율 값

        Returns:
            해석 상세 정보 dictionary
        """
        interpretation = {
            "value": value,
            "rating": "N/A",
            "message": "",
            "recommendation": "",
            "benchmark_comparison": {},
        }

        if ratio_name in self.benchmarks:
            benchmark = self.benchmarks[ratio_name]
            interpretation["benchmark_comparison"] = benchmark

            # benchmark로 rating 결정
            if ratio_name in ["current_ratio", "roe", "gross_margin"]:
                # 높을수록 좋음
                if value >= benchmark["excellent"]:
                    interpretation["rating"] = "Excellent"
                    interpretation["message"] = (
                        "Performance significantly exceeds industry standards"
                    )
                elif value >= benchmark["good"]:
                    interpretation["rating"] = "Good"
                    interpretation["message"] = (
                        f"Above average performance for {self.industry} industry"
                    )
                elif value >= benchmark["acceptable"]:
                    interpretation["rating"] = "Acceptable"
                    interpretation["message"] = "Meets industry standards"
                else:
                    interpretation["rating"] = "Poor"
                    interpretation["message"] = "Below industry standards - attention needed"

            elif ratio_name == "debt_to_equity":
                # 낮을수록 좋음
                if value <= benchmark["excellent"]:
                    interpretation["rating"] = "Excellent"
                    interpretation["message"] = "Very conservative capital structure"
                elif value <= benchmark["good"]:
                    interpretation["rating"] = "Good"
                    interpretation["message"] = "Healthy leverage level"
                elif value <= benchmark["acceptable"]:
                    interpretation["rating"] = "Acceptable"
                    interpretation["message"] = "Moderate leverage"
                else:
                    interpretation["rating"] = "Poor"
                    interpretation["message"] = "High leverage - potential risk"

            elif ratio_name == "pe_ratio":
                # 맥락에 따라 다름
                if value > 0:
                    if value < benchmark["undervalued"]:
                        interpretation["rating"] = "Potentially Undervalued"
                        interpretation["message"] = (
                            f"Trading below typical {self.industry} multiples"
                        )
                    elif value < benchmark["fair"]:
                        interpretation["rating"] = "Fair Value"
                        interpretation["message"] = "In line with industry averages"
                    elif value < benchmark["growth"]:
                        interpretation["rating"] = "Growth Premium"
                        interpretation["message"] = "Market pricing in growth expectations"
                    else:
                        interpretation["rating"] = "Expensive"
                        interpretation["message"] = "High valuation relative to industry"

        # 구체적인 권고 추가
        interpretation["recommendation"] = self._get_recommendation(
            ratio_name, interpretation["rating"]
        )

        return interpretation

    def _get_recommendation(self, ratio_name: str, rating: str) -> str:
        """비율과 rating으로 실행 가능한 권고를 생성합니다."""
        recommendations = {
            "current_ratio": {
                "Poor": "Consider improving working capital management, reducing short-term debt, or increasing liquid assets",
                "Acceptable": "Monitor liquidity closely and consider building additional cash reserves",
                "Good": "Maintain current liquidity management practices",
                "Excellent": "Strong liquidity position - consider productive use of excess cash",
            },
            "debt_to_equity": {
                "Poor": "High leverage increases financial risk - consider debt reduction strategies",
                "Acceptable": "Monitor debt levels and ensure adequate interest coverage",
                "Good": "Balanced capital structure - maintain current approach",
                "Excellent": "Conservative leverage - may consider strategic use of debt for growth",
            },
            "roe": {
                "Poor": "Focus on improving operational efficiency and profitability",
                "Acceptable": "Explore opportunities to enhance returns through operational improvements",
                "Good": "Solid returns - continue current strategies",
                "Excellent": "Outstanding performance - ensure sustainability of high returns",
            },
            "pe_ratio": {
                "Potentially Undervalued": "May present buying opportunity if fundamentals are solid",
                "Fair Value": "Reasonably priced relative to industry peers",
                "Growth Premium": "Ensure growth prospects justify premium valuation",
                "Expensive": "Consider valuation risk - ensure fundamentals support high multiple",
            },
        }

        if ratio_name in recommendations and rating in recommendations[ratio_name]:
            return recommendations[ratio_name][rating]

        return "Continue monitoring this metric"

    def analyze_trend(
        self, ratio_name: str, values: list[float], periods: list[str]
    ) -> dict[str, Any]:
        """
        시간에 따른 비율 추세를 분석합니다.

        Args:
            ratio_name: 비율 이름
            values: 비율 값 목록
            periods: 기간 label 목록

        Returns:
            추세 분석 dictionary
        """
        if len(values) < 2:
            return {
                "trend": "Insufficient data",
                "message": "Need at least 2 periods for trend analysis",
            }

        # 추세 계산
        first_value = values[0]
        last_value = values[-1]
        change = last_value - first_value
        pct_change = (change / abs(first_value)) * 100 if first_value != 0 else 0

        # 추세 방향 결정
        if abs(pct_change) < 5:
            trend = "Stable"
        elif pct_change > 0:
            trend = "Improving" if ratio_name != "debt_to_equity" else "Deteriorating"
        else:
            trend = "Deteriorating" if ratio_name != "debt_to_equity" else "Improving"

        return {
            "trend": trend,
            "change": change,
            "pct_change": pct_change,
            "message": f"{ratio_name} has {'increased' if change > 0 else 'decreased'} by {abs(pct_change):.1f}% from {periods[0]} to {periods[-1]}",
            "values": list(zip(periods, values, strict=False)),
        }

    def generate_report(self, ratios: dict[str, Any]) -> str:
        """
        종합 해석 보고서를 생성합니다.

        Args:
            ratios: 계산한 비율 dictionary

        Returns:
            서식 지정 보고서 문자열
        """
        report_lines = [
            f"Financial Analysis Report - {self.industry.title()} Industry Context",
            "=" * 70,
            "",
        ]

        for category, category_ratios in ratios.items():
            report_lines.append(f"\n{category.upper()} ANALYSIS")
            report_lines.append("-" * 40)

            for ratio_name, value in category_ratios.items():
                if isinstance(value, (int, float)):
                    interpretation = self.interpret_ratio(ratio_name, value)
                    report_lines.append(f"\n{ratio_name.replace('_', ' ').title()}:")
                    report_lines.append(f"  Value: {value:.2f}")
                    report_lines.append(f"  Rating: {interpretation['rating']}")
                    report_lines.append(f"  Analysis: {interpretation['message']}")
                    report_lines.append(f"  Action: {interpretation['recommendation']}")

        return "\n".join(report_lines)


def perform_comprehensive_analysis(
    ratios: dict[str, Any],
    industry: str = "general",
    historical_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    해석을 포함한 종합 비율 분석을 수행합니다.

    Args:
        ratios: 계산된 재무 비율
        industry: benchmarking할 업계 sector
        historical_data: 추세 분석용 선택적 과거 비율 data

    Returns:
        해석과 권고가 포함된 전체 분석
    """
    interpreter = RatioInterpreter(industry)
    analysis = {
        "current_analysis": {},
        "trend_analysis": {},
        "overall_health": {},
        "recommendations": [],
    }

    # 현재 비율 분석
    for category, category_ratios in ratios.items():
        analysis["current_analysis"][category] = {}
        for ratio_name, value in category_ratios.items():
            if isinstance(value, (int, float)):
                analysis["current_analysis"][category][ratio_name] = interpreter.interpret_ratio(
                    ratio_name, value
                )

    # 과거 data가 있으면 추세 분석 수행
    if historical_data:
        for ratio_name, historical_values in historical_data.items():
            if "values" in historical_values and "periods" in historical_values:
                analysis["trend_analysis"][ratio_name] = interpreter.analyze_trend(
                    ratio_name, historical_values["values"], historical_values["periods"]
                )

    # 전반적인 건전성 평가 생성
    analysis["overall_health"] = _assess_overall_health(analysis["current_analysis"])

    # 핵심 권고 생성
    analysis["recommendations"] = _generate_key_recommendations(analysis)

    # 서식 지정 보고서 추가
    analysis["report"] = interpreter.generate_report(ratios)

    return analysis


def _assess_overall_health(current_analysis: dict[str, Any]) -> dict[str, str]:
    """비율 분석으로 전반적인 재무 건전성을 평가합니다."""
    ratings = []
    for _category, category_analysis in current_analysis.items():
        for _ratio_name, ratio_analysis in category_analysis.items():
            if "rating" in ratio_analysis:
                ratings.append(ratio_analysis["rating"])

    # 간단한 scoring 시스템
    score_map = {
        "Excellent": 4,
        "Good": 3,
        "Acceptable": 2,
        "Poor": 1,
        "Fair Value": 3,
        "Potentially Undervalued": 3,
        "Growth Premium": 2,
        "Expensive": 1,
    }

    scores = [score_map.get(rating, 2) for rating in ratings]
    avg_score = sum(scores) / len(scores) if scores else 0

    if avg_score >= 3.5:
        health = "Excellent"
        message = "Company shows strong financial health across most metrics"
    elif avg_score >= 2.5:
        health = "Good"
        message = "Overall healthy financial position with some areas for improvement"
    elif avg_score >= 1.5:
        health = "Fair"
        message = "Mixed financial indicators - attention needed in several areas"
    else:
        health = "Poor"
        message = "Significant financial challenges requiring immediate attention"

    return {"status": health, "message": message, "score": f"{avg_score:.1f}/4.0"}


def _generate_key_recommendations(analysis: dict[str, Any]) -> list[str]:
    """분석에 따른 우선순위 권고를 생성합니다."""
    recommendations = []

    # 핵심 문제 확인
    for _category, category_analysis in analysis["current_analysis"].items():
        for ratio_name, ratio_analysis in category_analysis.items():
            if ratio_analysis.get("rating") == "Poor":
                recommendations.append(
                    f"Priority: Address {ratio_name.replace('_', ' ')} - {ratio_analysis.get('recommendation', '')}"
                )

    # 추세 기반 권고 추가
    for ratio_name, trend in analysis.get("trend_analysis", {}).items():
        if trend.get("trend") == "Deteriorating":
            recommendations.append(
                f"Monitor: {ratio_name.replace('_', ' ')} showing negative trend"
            )

    # 건전하면 일반적인 권고 추가
    if not recommendations:
        recommendations.append("Continue current financial management practices")
        recommendations.append("Consider strategic growth opportunities")

    return recommendations[:5]  # 상위 5개 권고 반환
