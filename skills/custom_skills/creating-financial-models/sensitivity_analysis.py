"""
재무 model의 sensitivity analysis module입니다.
변수 변경이 핵심 output에 미치는 영향을 테스트합니다.
"""

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd


class SensitivityAnalyzer:
    """재무 model의 sensitivity analysis를 수행합니다."""

    def __init__(self, base_model: Any):
        """
        sensitivity analyzer를 초기화합니다.

        Args:
            base_model: 분석할 기본 재무 model
        """
        self.base_model = base_model
        self.base_output = None
        self.sensitivity_results = {}

    def one_way_sensitivity(
        self,
        variable_name: str,
        base_value: float,
        range_pct: float,
        steps: int,
        output_func: Callable,
        model_update_func: Callable,
    ) -> pd.DataFrame:
        """
        one-way sensitivity analysis를 수행합니다.

        Args:
            variable_name: 테스트할 변수 이름
            base_value: 기본 사례 값
            range_pct: 테스트할 +/- 백분율 범위
            steps: 범위의 단계 수
            output_func: output metric 계산 함수
            model_update_func: 새 값으로 model 갱신 함수

        Returns:
            sensitivity 결과 DataFrame
        """
        # 범위 계산
        min_val = base_value * (1 - range_pct)
        max_val = base_value * (1 + range_pct)
        test_values = np.linspace(min_val, max_val, steps)

        results = []
        for value in test_values:
            # model 갱신
            model_update_func(value)

            # output 계산
            output = output_func()

            results.append(
                {
                    "variable": variable_name,
                    "value": value,
                    "pct_change": (value - base_value) / base_value * 100,
                    "output": output,
                    "output_change": output - self.base_output if self.base_output else 0,
                }
            )

        # 기준값으로 초기화
        model_update_func(base_value)

        return pd.DataFrame(results)

    def two_way_sensitivity(
        self,
        var1_name: str,
        var1_base: float,
        var1_range: list[float],
        var2_name: str,
        var2_base: float,
        var2_range: list[float],
        output_func: Callable,
        model_update_func: Callable,
    ) -> pd.DataFrame:
        """
        two-way sensitivity analysis를 수행합니다.

        Args:
            var1_name: 첫 변수 이름
            var1_base: 첫 변수 기준값
            var1_range: 첫 변수 값 범위
            var2_name: 두 번째 변수 이름
            var2_base: 두 번째 변수 기준값
            var2_range: 두 번째 변수 값 범위
            output_func: output 계산 함수
            model_update_func: model 갱신 함수(var1, var2 받음)

        Returns:
            two-way sensitivity table이 있는 DataFrame
        """
        results = np.zeros((len(var1_range), len(var2_range)))

        for i, val1 in enumerate(var1_range):
            for j, val2 in enumerate(var2_range):
                # 두 변수 모두 갱신
                model_update_func(val1, val2)

                # output 계산
                results[i, j] = output_func()

        # 기준값으로 초기화
        model_update_func(var1_base, var2_base)

        # DataFrame 생성
        df = pd.DataFrame(
            results,
            index=[f"{var1_name}={v:.2%}" if v < 1 else f"{var1_name}={v:.1f}" for v in var1_range],
            columns=[
                f"{var2_name}={v:.2%}" if v < 1 else f"{var2_name}={v:.1f}" for v in var2_range
            ],
        )

        return df

    def tornado_analysis(
        self, variables: dict[str, dict[str, Any]], output_func: Callable
    ) -> pd.DataFrame:
        """
        변수의 상대적 영향을 보여 주는 tornado diagram data를 만듭니다.

        Args:
            variables: base, low, high 값이 있는 변수 dictionary
            output_func: output 계산 함수

        Returns:
            영향 크기로 정렬한 DataFrame
        """
        # 기준 output 저장
        self.base_output = output_func()

        tornado_data = []

        for var_name, var_info in variables.items():
            # 낮은 값 테스트
            var_info["update_func"](var_info["low"])
            low_output = output_func()

            # 높은 값 테스트
            var_info["update_func"](var_info["high"])
            high_output = output_func()

            # 기준값으로 초기화
            var_info["update_func"](var_info["base"])

            # 영향 계산
            impact = high_output - low_output
            low_delta = low_output - self.base_output
            high_delta = high_output - self.base_output

            tornado_data.append(
                {
                    "variable": var_name,
                    "base_value": var_info["base"],
                    "low_value": var_info["low"],
                    "high_value": var_info["high"],
                    "low_output": low_output,
                    "high_output": high_output,
                    "low_delta": low_delta,
                    "high_delta": high_delta,
                    "impact": abs(impact),
                    "impact_pct": abs(impact) / self.base_output * 100,
                }
            )

        # 영향으로 정렬
        df = pd.DataFrame(tornado_data)
        df = df.sort_values("impact", ascending=False)

        return df

    def scenario_analysis(
        self,
        scenarios: dict[str, dict[str, float]],
        variable_updates: dict[str, Callable],
        output_func: Callable,
        probability_weights: dict[str, float] | None = None,
    ) -> pd.DataFrame:
        """
        서로 다른 변수 조합의 여러 scenario를 분석합니다.

        Args:
            scenarios: 변수 값이 있는 scenario dictionary
            variable_updates: 각 변수 갱신 함수
            output_func: output 계산 함수
            probability_weights: 각 scenario의 선택적 확률

        Returns:
            scenario 결과 DataFrame
        """
        results = []

        for scenario_name, variables in scenarios.items():
            # 이 scenario의 모든 변수 갱신
            for var_name, value in variables.items():
                if var_name in variable_updates:
                    variable_updates[var_name](value)

            # output 계산
            output = output_func()

            # 제공된 확률 얻기
            prob = (
                probability_weights.get(scenario_name, 1 / len(scenarios))
                if probability_weights
                else 1 / len(scenarios)
            )

            results.append(
                {
                    "scenario": scenario_name,
                    "probability": prob,
                    "output": output,
                    **variables,  # 모든 변수 값 포함
                }
            )

            # model 초기화(간소화 - 모든 기준값을 복원해야 함)

        df = pd.DataFrame(results)

        # 기대값 계산
        df["weighted_output"] = df["output"] * df["probability"]
        expected_value = df["weighted_output"].sum()

        # 요약 행 추가
        summary = pd.DataFrame(
            [
                {
                    "scenario": "Expected Value",
                    "probability": 1.0,
                    "output": expected_value,
                    "weighted_output": expected_value,
                }
            ]
        )

        df = pd.concat([df, summary], ignore_index=True)

        return df

    def breakeven_analysis(
        self,
        variable_name: str,
        variable_update: Callable,
        output_func: Callable,
        target_value: float,
        min_search: float,
        max_search: float,
        tolerance: float = 0.01,
    ) -> float:
        """
        output이 목표와 같은 breakeven point를 찾습니다.

        Args:
            variable_name: 조정할 변수
            variable_update: 변수 갱신 함수
            output_func: output 계산 함수
            target_value: 목표 output 값
            min_search: 최소 검색 범위
            max_search: 최대 검색 범위
            tolerance: 수렴 허용 오차

        Returns:
            변수의 breakeven 값
        """
        # breakeven의 binary search
        low = min_search
        high = max_search

        while (high - low) > tolerance:
            mid = (low + high) / 2
            variable_update(mid)
            output = output_func()

            if abs(output - target_value) < tolerance:
                return mid
            elif output < target_value:
                low = mid
            else:
                high = mid

        return (low + high) / 2


def create_data_table(
    row_variable: tuple[str, list[float], Callable],
    col_variable: tuple[str, list[float], Callable],
    output_func: Callable,
) -> pd.DataFrame:
    """
    두 변수의 Excel-style data table을 만듭니다.

    Args:
        row_variable: (name, values, update_function)
        col_variable: (name, values, update_function)
        output_func: output 계산 함수

    Returns:
        data table 형식의 DataFrame
    """
    row_name, row_values, row_update = row_variable
    col_name, col_values, col_update = col_variable

    results = np.zeros((len(row_values), len(col_values)))

    for i, row_val in enumerate(row_values):
        for j, col_val in enumerate(col_values):
            row_update(row_val)
            col_update(col_val)
            results[i, j] = output_func()

    df = pd.DataFrame(
        results,
        index=pd.Index(row_values, name=row_name),
        columns=pd.Index(col_values, name=col_name),
    )

    return df


# 사용 예제
if __name__ == "__main__":
    # 시연용 mock model
    class SimpleModel:
        def __init__(self):
            self.revenue = 1000
            self.margin = 0.20
            self.multiple = 10

        def calculate_value(self):
            ebitda = self.revenue * self.margin
            return ebitda * self.multiple

    # model과 analyzer 생성
    model = SimpleModel()
    analyzer = SensitivityAnalyzer(model)

    # One-way sensitivity
    results = analyzer.one_way_sensitivity(
        variable_name="Revenue",
        base_value=model.revenue,
        range_pct=0.20,
        steps=5,
        output_func=model.calculate_value,
        model_update_func=lambda x: setattr(model, "revenue", x),
    )

    print("One-Way Sensitivity Analysis:")
    print(results)

    # Tornado 분석
    variables = {
        "Revenue": {
            "base": 1000,
            "low": 800,
            "high": 1200,
            "update_func": lambda x: setattr(model, "revenue", x),
        },
        "Margin": {
            "base": 0.20,
            "low": 0.15,
            "high": 0.25,
            "update_func": lambda x: setattr(model, "margin", x),
        },
        "Multiple": {
            "base": 10,
            "low": 8,
            "high": 12,
            "update_func": lambda x: setattr(model, "multiple", x),
        },
    }

    tornado = analyzer.tornado_analysis(variables, model.calculate_value)
    print("\nTornado Analysis:")
    print(tornado[["variable", "impact", "impact_pct"]])
