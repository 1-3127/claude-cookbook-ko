"""
Discounted Cash Flow(DCF) valuation model입니다.
free cash flow 전망을 사용하는 enterprise valuation을 구현합니다.
"""

from typing import Any

import numpy as np


class DCFModel:
    """DCF valuation model을 구축하고 계산합니다."""

    def __init__(self, company_name: str = "Company"):
        """
        DCF model을 초기화합니다.

        Args:
            company_name: 가치 평가할 회사 이름
        """
        self.company_name = company_name
        self.historical_financials = {}
        self.projections = {}
        self.assumptions = {}
        self.wacc_components = {}
        self.valuation_results = {}

    def set_historical_financials(
        self,
        revenue: list[float],
        ebitda: list[float],
        capex: list[float],
        nwc: list[float],
        years: list[int],
    ):
        """
        과거 재무 data를 설정합니다.

        Args:
            revenue: 과거 매출
            ebitda: 과거 EBITDA
            capex: 과거 자본 지출
            nwc: 과거 net working capital
            years: 과거 연도
        """
        self.historical_financials = {
            "years": years,
            "revenue": revenue,
            "ebitda": ebitda,
            "capex": capex,
            "nwc": nwc,
            "ebitda_margin": [ebitda[i] / revenue[i] for i in range(len(revenue))],
            "capex_percent": [capex[i] / revenue[i] for i in range(len(revenue))],
        }

    def set_assumptions(
        self,
        projection_years: int = 5,
        revenue_growth: list[float] = None,
        ebitda_margin: list[float] = None,
        tax_rate: float = 0.25,
        capex_percent: list[float] = None,
        nwc_percent: list[float] = None,
        terminal_growth: float = 0.03,
    ):
        """
        전망 가정을 설정합니다.

        Args:
            projection_years: 전망할 연도 수
            revenue_growth: 연간 매출 성장률
            ebitda_margin: 연도별 EBITDA margin
            tax_rate: 법인세율
            capex_percent: 매출 대비 Capex 비율
            nwc_percent: 매출 대비 NWC 비율
            terminal_growth: Terminal growth rate
        """
        if revenue_growth is None:
            revenue_growth = [0.10] * projection_years  # 기본 성장률 10%

        if ebitda_margin is None:
            # 가능하면 과거 평균 사용
            if self.historical_financials:
                avg_margin = np.mean(self.historical_financials["ebitda_margin"])
                ebitda_margin = [avg_margin] * projection_years
            else:
                ebitda_margin = [0.20] * projection_years  # 기본 margin 20%

        if capex_percent is None:
            capex_percent = [0.05] * projection_years  # 기본 매출의 5%

        if nwc_percent is None:
            nwc_percent = [0.10] * projection_years  # 기본 매출의 10%

        self.assumptions = {
            "projection_years": projection_years,
            "revenue_growth": revenue_growth,
            "ebitda_margin": ebitda_margin,
            "tax_rate": tax_rate,
            "capex_percent": capex_percent,
            "nwc_percent": nwc_percent,
            "terminal_growth": terminal_growth,
        }

    def calculate_wacc(
        self,
        risk_free_rate: float,
        beta: float,
        market_premium: float,
        cost_of_debt: float,
        debt_to_equity: float,
        tax_rate: float | None = None,
    ) -> float:
        """
        Weighted Average Cost of Capital(WACC)을 계산합니다.

        Args:
            risk_free_rate: Risk-free rate(예: 10년 국채)
            beta: Equity beta
            market_premium: Equity market risk premium
            cost_of_debt: 세전 cost of debt
            debt_to_equity: Debt-to-equity ratio
            tax_rate: 세율(없으면 가정 사용)

        Returns:
            소수 형식의 WACC
        """
        if tax_rate is None:
            tax_rate = self.assumptions.get("tax_rate", 0.25)

        # CAPM으로 cost of equity 계산
        cost_of_equity = risk_free_rate + beta * market_premium

        # 가중치 계산
        equity_weight = 1 / (1 + debt_to_equity)
        debt_weight = debt_to_equity / (1 + debt_to_equity)

        # WACC 계산
        wacc = equity_weight * cost_of_equity + debt_weight * cost_of_debt * (1 - tax_rate)

        self.wacc_components = {
            "risk_free_rate": risk_free_rate,
            "beta": beta,
            "market_premium": market_premium,
            "cost_of_equity": cost_of_equity,
            "cost_of_debt": cost_of_debt,
            "debt_to_equity": debt_to_equity,
            "equity_weight": equity_weight,
            "debt_weight": debt_weight,
            "tax_rate": tax_rate,
            "wacc": wacc,
        }

        return wacc

    def project_cash_flows(self) -> dict[str, list[float]]:
        """
        가정을 바탕으로 미래 현금흐름을 전망합니다.

        Returns:
            재무 전망 dictionary
        """
        years = self.assumptions["projection_years"]

        # 가능하면 마지막 과거 매출부터 시작
        if self.historical_financials and "revenue" in self.historical_financials:
            base_revenue = self.historical_financials["revenue"][-1]
        else:
            base_revenue = 1000  # 기본 기준값

        projections = {
            "year": list(range(1, years + 1)),
            "revenue": [],
            "ebitda": [],
            "ebit": [],
            "tax": [],
            "nopat": [],
            "capex": [],
            "nwc_change": [],
            "fcf": [],
        }

        prev_revenue = base_revenue
        prev_nwc = base_revenue * 0.10  # 초기 NWC 가정

        for i in range(years):
            # 매출
            revenue = prev_revenue * (1 + self.assumptions["revenue_growth"][i])
            projections["revenue"].append(revenue)

            # EBITDA
            ebitda = revenue * self.assumptions["ebitda_margin"][i]
            projections["ebitda"].append(ebitda)

            # EBIT(단순화를 위해 depreciation = capex 가정)
            depreciation = revenue * self.assumptions["capex_percent"][i]
            ebit = ebitda - depreciation
            projections["ebit"].append(ebit)

            # 세금
            tax = ebit * self.assumptions["tax_rate"]
            projections["tax"].append(tax)

            # NOPAT
            nopat = ebit - tax
            projections["nopat"].append(nopat)

            # Capex
            capex = revenue * self.assumptions["capex_percent"][i]
            projections["capex"].append(capex)

            # NWC 변경
            nwc = revenue * self.assumptions["nwc_percent"][i]
            nwc_change = nwc - prev_nwc
            projections["nwc_change"].append(nwc_change)

            # Free Cash Flow
            fcf = nopat + depreciation - capex - nwc_change
            projections["fcf"].append(fcf)

            prev_revenue = revenue
            prev_nwc = nwc

        self.projections = projections
        return projections

    def calculate_terminal_value(
        self, method: str = "growth", exit_multiple: float | None = None
    ) -> float:
        """
        perpetuity growth나 exit multiple로 terminal value를 계산합니다.

        Args:
            method: perpetuity growth는 'growth', exit multiple은 'multiple'
            exit_multiple: EV/EBITDA exit multiple(multiple 방법 사용 시)

        Returns:
            Terminal value
        """
        if not self.projections:
            raise ValueError("Must project cash flows first")

        if method == "growth":
            # Gordon growth model
            final_fcf = self.projections["fcf"][-1]
            terminal_growth = self.assumptions["terminal_growth"]
            wacc = self.wacc_components["wacc"]

            # terminal year의 FCF
            terminal_fcf = final_fcf * (1 + terminal_growth)

            # Terminal value
            terminal_value = terminal_fcf / (wacc - terminal_growth)

        elif method == "multiple":
            if exit_multiple is None:
                exit_multiple = 10  # 기본 EV/EBITDA multiple

            final_ebitda = self.projections["ebitda"][-1]
            terminal_value = final_ebitda * exit_multiple

        else:
            raise ValueError("Method must be 'growth' or 'multiple'")

        return terminal_value

    def calculate_enterprise_value(
        self, terminal_method: str = "growth", exit_multiple: float | None = None
    ) -> dict[str, Any]:
        """
        현금흐름을 할인해 enterprise value를 계산합니다.

        Args:
            terminal_method: terminal value 계산 방법
            exit_multiple: multiple 방법 사용 시 exit multiple

        Returns:
            Valuation 결과 dictionary
        """
        if not self.projections:
            self.project_cash_flows()

        if "wacc" not in self.wacc_components:
            raise ValueError("Must calculate WACC first")

        wacc = self.wacc_components["wacc"]
        years = self.assumptions["projection_years"]

        # 예상 현금흐름의 PV 계산
        pv_fcf = []
        for i, fcf in enumerate(self.projections["fcf"]):
            discount_factor = (1 + wacc) ** (i + 1)
            pv = fcf / discount_factor
            pv_fcf.append(pv)

        total_pv_fcf = sum(pv_fcf)

        # terminal value 계산
        terminal_value = self.calculate_terminal_value(terminal_method, exit_multiple)

        # terminal value 할인
        terminal_discount = (1 + wacc) ** years
        pv_terminal = terminal_value / terminal_discount

        # Enterprise value
        enterprise_value = total_pv_fcf + pv_terminal

        self.valuation_results = {
            "enterprise_value": enterprise_value,
            "pv_fcf": total_pv_fcf,
            "pv_terminal": pv_terminal,
            "terminal_value": terminal_value,
            "terminal_method": terminal_method,
            "pv_fcf_detail": pv_fcf,
            "terminal_percent": pv_terminal / enterprise_value * 100,
        }

        return self.valuation_results

    def calculate_equity_value(
        self, net_debt: float, cash: float = 0, shares_outstanding: float = 100
    ) -> dict[str, Any]:
        """
        enterprise value에서 equity value를 계산합니다.

        Args:
            net_debt: 총부채에서 현금을 뺀 값
            cash: 현금 및 현금성 자산(상계하지 않은 경우)
            shares_outstanding: 주식 수(백만 단위)

        Returns:
            Equity valuation metric
        """
        if "enterprise_value" not in self.valuation_results:
            raise ValueError("Must calculate enterprise value first")

        ev = self.valuation_results["enterprise_value"]

        # Equity value = EV - Net Debt
        equity_value = ev - net_debt + cash

        # 주당 가치
        value_per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0

        equity_results = {
            "equity_value": equity_value,
            "shares_outstanding": shares_outstanding,
            "value_per_share": value_per_share,
            "net_debt": net_debt,
            "cash": cash,
        }

        self.valuation_results.update(equity_results)
        return equity_results

    def sensitivity_analysis(
        self, variable1: str, range1: list[float], variable2: str, range2: list[float]
    ) -> np.ndarray:
        """
        valuation의 two-way sensitivity analysis를 수행합니다.

        Args:
            variable1: 테스트할 첫 변수('wacc', 'growth', 'margin')
            range1: variable1 값 범위
            variable2: 테스트할 두 번째 변수
            range2: variable2 값 범위

        Returns:
            valuation의 2D array
        """
        results = np.zeros((len(range1), len(range2)))

        # 원래 값 저장
        orig_wacc = self.wacc_components.get("wacc", 0.10)
        orig_growth = self.assumptions.get("terminal_growth", 0.03)
        orig_margin = self.assumptions.get("ebitda_margin", [0.20] * 5)

        for i, val1 in enumerate(range1):
            for j, val2 in enumerate(range2):
                # 첫 변수 갱신
                if variable1 == "wacc":
                    self.wacc_components["wacc"] = val1
                elif variable1 == "growth":
                    self.assumptions["terminal_growth"] = val1
                elif variable1 == "margin":
                    self.assumptions["ebitda_margin"] = [val1] * len(orig_margin)

                # 두 번째 변수 갱신
                if variable2 == "wacc":
                    self.wacc_components["wacc"] = val2
                elif variable2 == "growth":
                    self.assumptions["terminal_growth"] = val2
                elif variable2 == "margin":
                    self.assumptions["ebitda_margin"] = [val2] * len(orig_margin)

                # 재계산
                self.project_cash_flows()
                valuation = self.calculate_enterprise_value()
                results[i, j] = valuation["enterprise_value"]

        # 원래 값 복원
        self.wacc_components["wacc"] = orig_wacc
        self.assumptions["terminal_growth"] = orig_growth
        self.assumptions["ebitda_margin"] = orig_margin

        return results

    def generate_summary(self) -> str:
        """
        valuation 결과의 텍스트 요약을 생성합니다.

        Returns:
            서식 지정 요약 문자열
        """
        if not self.valuation_results:
            return "No valuation results available. Run valuation first."

        summary = [
            f"DCF Valuation Summary - {self.company_name}",
            "=" * 50,
            "",
            "Key Assumptions:",
            f"  Projection Period: {self.assumptions['projection_years']} years",
            f"  Revenue Growth: {np.mean(self.assumptions['revenue_growth']) * 100:.1f}% avg",
            f"  EBITDA Margin: {np.mean(self.assumptions['ebitda_margin']) * 100:.1f}% avg",
            f"  Terminal Growth: {self.assumptions['terminal_growth'] * 100:.1f}%",
            f"  WACC: {self.wacc_components['wacc'] * 100:.1f}%",
            "",
            "Valuation Results:",
            f"  Enterprise Value: ${self.valuation_results['enterprise_value']:,.0f}M",
            f"    PV of FCF: ${self.valuation_results['pv_fcf']:,.0f}M",
            f"    PV of Terminal: ${self.valuation_results['pv_terminal']:,.0f}M",
            f"    Terminal % of Value: {self.valuation_results['terminal_percent']:.1f}%",
            "",
        ]

        if "equity_value" in self.valuation_results:
            summary.extend(
                [
                    "Equity Valuation:",
                    f"  Equity Value: ${self.valuation_results['equity_value']:,.0f}M",
                    f"  Shares Outstanding: {self.valuation_results['shares_outstanding']:.0f}M",
                    f"  Value per Share: ${self.valuation_results['value_per_share']:.2f}",
                    "",
                ]
            )

        return "\n".join(summary)


# 일반적인 계산용 helper 함수


def calculate_beta(stock_returns: list[float], market_returns: list[float]) -> float:
    """
    수익률 series에서 beta를 계산합니다.

    Args:
        stock_returns: 과거 주식 수익률
        market_returns: 과거 시장 수익률

    Returns:
        Beta 계수
    """
    covariance = np.cov(stock_returns, market_returns)[0, 1]
    market_variance = np.var(market_returns)
    beta = covariance / market_variance if market_variance != 0 else 1.0
    return beta


def calculate_fcf_cagr(fcf_series: list[float]) -> float:
    """
    FCF의 compound annual growth rate를 계산합니다.

    Args:
        fcf_series: Free cash flow time series

    Returns:
        소수 형식의 CAGR
    """
    if len(fcf_series) < 2:
        return 0

    years = len(fcf_series) - 1
    if fcf_series[0] <= 0 or fcf_series[-1] <= 0:
        return 0

    cagr = (fcf_series[-1] / fcf_series[0]) ** (1 / years) - 1
    return cagr


# 사용 예제
if __name__ == "__main__":
    # model 생성
    model = DCFModel("TechCorp")

    # 과거 data 설정
    model.set_historical_financials(
        revenue=[800, 900, 1000],
        ebitda=[160, 189, 220],
        capex=[40, 45, 50],
        nwc=[80, 90, 100],
        years=[2022, 2023, 2024],
    )

    # 가정 설정
    model.set_assumptions(
        projection_years=5,
        revenue_growth=[0.15, 0.12, 0.10, 0.08, 0.06],
        ebitda_margin=[0.23, 0.24, 0.25, 0.25, 0.25],
        tax_rate=0.25,
        terminal_growth=0.03,
    )

    # WACC 계산
    model.calculate_wacc(
        risk_free_rate=0.04, beta=1.2, market_premium=0.07, cost_of_debt=0.05, debt_to_equity=0.5
    )

    # 현금흐름 추정
    model.project_cash_flows()

    # valuation 계산
    model.calculate_enterprise_value()

    # equity value 계산
    model.calculate_equity_value(net_debt=200, shares_outstanding=50)

    # 요약 출력
    print(model.generate_summary())
