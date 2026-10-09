#!/usr/bin/env python3
"""
Decision Matrix Tool - 복잡한 선택을 위한 전략적 의사결정 framework
Chief of Staff agent용 custom Python script
"""

import argparse
import json
from typing import Any, TypedDict


class OptionScore(TypedDict):
    name: str
    scores: dict[str, float]
    weighted_scores: dict[str, float]
    total: float
    pros: list[str]
    cons: list[str]
    verdict: str


class Analysis(TypedDict):
    clear_winner: bool
    margin: float
    recommendation: str
    key_differentiators: list[str]
    risks: list[str]


class DecisionMatrix(TypedDict):
    options: list[OptionScore]
    winner: str | None
    analysis: Analysis


def create_decision_matrix(
    options: list[dict[str, Any]], criteria: list[dict[str, Any]]
) -> DecisionMatrix:
    """전략적 선택을 위한 가중 decision matrix를 생성합니다"""

    # 올바른 type checking을 위해 명시적인 type으로 analysis를 별도 초기화
    initial_analysis: Analysis = {
        "clear_winner": False,
        "margin": 0.0,
        "recommendation": "",
        "key_differentiators": [],
        "risks": [],
    }

    results: DecisionMatrix = {
        "options": [],
        "winner": None,
        "analysis": initial_analysis,
    }

    for option in options:
        option_scores: OptionScore = {
            "name": option["name"],
            "scores": {},
            "weighted_scores": {},
            "total": 0,
            "pros": [],
            "cons": [],
            "verdict": "",
        }

        # 각 기준의 점수 계산
        for criterion in criteria:
            crit_name = criterion["name"]
            weight = criterion["weight"]

            # 이 기준에 대한 해당 선택지의 점수 가져오기(1-10)
            score = option.get(crit_name, 5)
            weighted = score * weight

            option_scores["scores"][crit_name] = score
            option_scores["weighted_scores"][crit_name] = round(weighted, 2)
            option_scores["total"] += weighted

            # 장단점 추적
            if score >= 8:
                option_scores["pros"].append(f"Excellent {crit_name}")
            elif score >= 6:
                option_scores["pros"].append(f"Good {crit_name}")
            elif score <= 3:
                option_scores["cons"].append(f"Poor {crit_name}")
            elif score <= 5:
                option_scores["cons"].append(f"Weak {crit_name}")

        option_scores["total"] = round(option_scores["total"], 2)

        # 판단 생성
        if option_scores["total"] >= 8:
            option_scores["verdict"] = "STRONGLY RECOMMENDED"
        elif option_scores["total"] >= 6.5:
            option_scores["verdict"] = "RECOMMENDED"
        elif option_scores["total"] >= 5:
            option_scores["verdict"] = "ACCEPTABLE"
        else:
            option_scores["verdict"] = "NOT RECOMMENDED"

        results["options"].append(option_scores)

    # 최선의 선택지 찾기
    results["options"].sort(key=lambda x: x["total"], reverse=True)
    results["winner"] = results["options"][0]["name"]

    # 분석 생성
    results["analysis"] = generate_analysis(results["options"])

    return results


def generate_analysis(options: list[OptionScore]) -> Analysis:
    """결정에 대한 전략적 분석을 생성합니다"""

    analysis: Analysis = {
        "clear_winner": False,
        "margin": 0,
        "recommendation": "",
        "key_differentiators": [],
        "risks": [],
    }

    if len(options) >= 2:
        margin = options[0]["total"] - options[1]["total"]
        analysis["margin"] = round(margin, 2)
        analysis["clear_winner"] = margin > 1.5

        if analysis["clear_winner"]:
            analysis["recommendation"] = (
                f"Strongly recommend {options[0]['name']} with {margin:.1f} point advantage"
            )
        elif margin > 0.5:
            analysis["recommendation"] = (
                f"Recommend {options[0]['name']} but consider {options[1]['name']} as viable alternative"
            )
        else:
            analysis["recommendation"] = (
                f"Close decision between {options[0]['name']} and {options[1]['name']} - consider additional factors"
            )

        # 핵심 차별점 찾기
        top = options[0]
        for criterion in top["scores"]:
            if top["scores"][criterion] >= 8:
                analysis["key_differentiators"].append(criterion)

        # 위험 식별
        if top["total"] < 6:
            analysis["risks"].append("Overall score below recommended threshold")
        if len(top["cons"]) > len(top["pros"]):
            analysis["risks"].append("More weaknesses than strengths")

    return analysis


def main() -> None:
    parser = argparse.ArgumentParser(description="Strategic decision matrix tool")
    parser.add_argument("--scenario", type=str, help="Predefined scenario")
    parser.add_argument("--input", type=str, help="JSON file with options and criteria")
    parser.add_argument("--format", choices=["json", "text"], default="text")

    args = parser.parse_args()

    # 기본 시나리오: 직접 구축, 구매, 제휴
    if args.scenario == "build-buy-partner":
        options = [
            {
                "name": "Build In-House",
                "cost": 3,  # 1-10, 높을수록 좋음(따라서 3 = 높은 비용)
                "time_to_market": 2,  # 2 = 느림
                "control": 10,  # 10 = 완전한 제어
                "quality": 8,  # 8 = 높은 품질 잠재력
                "scalability": 9,  # 9 = 매우 높은 확장성
                "risk": 3,  # 3 = 높은 위험
            },
            {
                "name": "Buy Solution",
                "cost": 5,
                "time_to_market": 9,
                "control": 4,
                "quality": 7,
                "scalability": 6,
                "risk": 7,
            },
            {
                "name": "Strategic Partnership",
                "cost": 7,
                "time_to_market": 7,
                "control": 6,
                "quality": 7,
                "scalability": 8,
                "risk": 5,
            },
        ]

        criteria = [
            {"name": "cost", "weight": 0.20},
            {"name": "time_to_market", "weight": 0.25},
            {"name": "control", "weight": 0.15},
            {"name": "quality", "weight": 0.20},
            {"name": "scalability", "weight": 0.10},
            {"name": "risk", "weight": 0.10},
        ]
    elif args.input:
        with open(args.input) as f:
            data = json.load(f)
            options = data["options"]
            criteria = data["criteria"]
    else:
        # 기본 채용 시나리오
        options = [
            {
                "name": "Hire 3 Senior Engineers",
                "cost": 4,
                "productivity": 9,
                "time_to_impact": 8,
                "team_growth": 7,
                "runway_impact": 3,
            },
            {
                "name": "Hire 5 Junior Engineers",
                "cost": 7,
                "productivity": 5,
                "time_to_impact": 4,
                "team_growth": 9,
                "runway_impact": 5,
            },
        ]
        criteria = [
            {"name": "cost", "weight": 0.25},
            {"name": "productivity", "weight": 0.30},
            {"name": "time_to_impact", "weight": 0.20},
            {"name": "team_growth", "weight": 0.15},
            {"name": "runway_impact", "weight": 0.10},
        ]

    matrix = create_decision_matrix(options, criteria)

    if args.format == "json":
        print(json.dumps(matrix, indent=2))
    else:
        # Text 출력
        print("🎯 STRATEGIC DECISION MATRIX")
        print("=" * 60)

        print("\nOPTIONS EVALUATED:")
        for i, opt in enumerate(matrix["options"], 1):
            print(f"\n{i}. {opt['name']}")
            print("-" * 40)
            print(f"   Total Score: {opt['total']}/10 - {opt['verdict']}")

            print("   Strengths:")
            for pro in opt["pros"][:3]:
                print(f"   ✓ {pro}")

            if opt["cons"]:
                print("   Weaknesses:")
                for con in opt["cons"][:3]:
                    print(f"   ✗ {con}")

        print("\n" + "=" * 60)
        print("RECOMMENDATION:")
        print("-" * 40)
        analysis = matrix["analysis"]
        print(f"Winner: {matrix['winner']}")
        print(f"Margin: {analysis['margin']} points")
        print(f"\n{analysis['recommendation']}")

        if analysis["key_differentiators"]:
            print(f"\nKey advantages: {', '.join(analysis['key_differentiators'])}")

        if analysis["risks"]:
            print("\n⚠️  Risks to consider:")
            for risk in analysis["risks"]:
                print(f"   - {risk}")


if __name__ == "__main__":
    main()
