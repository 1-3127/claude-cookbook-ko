---
name: analyzing-financial-statements
description: 이 skill은 투자 분석을 위해 재무제표 data에서 핵심 재무 비율과 metric을 계산합니다
---

# 재무 비율 계산기 Skill

이 skill은 회사 성과, 수익성, 유동성, valuation을 평가하는 종합적인 재무 비율 분석을 제공합니다.

## 기능

계산 및 해석:
- **수익성 비율**: ROE, ROA, Gross Margin, Operating Margin, Net Margin
- **유동성 비율**: Current Ratio, Quick Ratio, Cash Ratio
- **Leverage 비율**: Debt-to-Equity, Interest Coverage, Debt Service Coverage
- **효율성 비율**: Asset Turnover, Inventory Turnover, Receivables Turnover
- **Valuation 비율**: P/E, P/B, P/S, EV/EBITDA, PEG
- **주당 Metric**: EPS, Book Value per Share, Dividend per Share

## 사용 방법

1. **입력 Data**: 재무제표 data 제공(손익계산서, 재무상태표, 현금흐름)
2. **비율 선택**: 계산할 비율을 지정하거나 종합 분석에 "all" 사용
3. **해석**: skill이 비율을 계산하고 업계 표준 해석 제공

## 입력 형식

재무 data는 다음으로 제공할 수 있습니다.
- 재무 항목이 있는 CSV
- 구조화된 재무제표 JSON
- 핵심 재무 수치의 텍스트 설명
- 재무제표가 있는 Excel 파일

## 출력 형식

결과에 포함되는 것:
- 계산한 비율과 값
- 업계 benchmark 비교(가능한 경우)
- 추세 분석(여러 기간이 제공되면)
- 해석과 insight
- 서식 지정 결과가 있는 Excel 보고서

## 사용 예제

"첨부 재무제표를 바탕으로 이 회사의 핵심 재무 비율을 계산하세요"

"주가가 $50이고 연간 주당 이익이 $2.50이면 P/E ratio는 얼마인가요?"

"재무상태표 data로 유동성 상태를 분석하세요"

## Script

- `calculate_ratios.py`: 모든 재무 비율의 주요 계산 engine
- `interpret_ratios.py`: 해석과 benchmarking 제공

## 모범 사례

1. 계산 전에 항상 data 완전성 검증
2. 결측값을 적절히 처리(업계 평균 사용 또는 제외)
3. 비율 해석 시 업계 맥락 고려
4. 추세 분석에 기간 비교 포함
5. 비정상적이거나 우려되는 비율 표시

## 제약

- 정확한 재무 data 필요
- 업계 benchmark는 일반적인 지침
- 일부 비율은 모든 업계에 적용되지 않을 수 있음
- 과거 data가 미래 성과를 보장하지 않음
