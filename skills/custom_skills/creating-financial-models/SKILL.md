---
name: creating-financial-models
description: 이 skill은 투자 결정을 위한 DCF 분석, sensitivity testing, Monte Carlo simulation, scenario planning을 포함한 고급 재무 modeling suite를 제공합니다
---

# 재무 Modeling Suite

업계 표준 방법론을 사용하는 투자 분석, valuation, risk 평가용 종합 재무 modeling toolkit입니다.

## 핵심 기능

### 1. Discounted Cash Flow(DCF) 분석
- 여러 성장 scenario로 완전한 DCF model 구축
- perpetuity growth와 exit multiple 방법으로 terminal value 계산
- weighted average cost of capital(WACC) 결정
- enterprise 및 equity valuation 생성

### 2. Sensitivity Analysis
- 핵심 가정의 valuation 영향 테스트
- 여러 변수용 data table 생성
- sensitivity 순위용 tornado chart 생성
- 핵심 value driver 식별

### 3. Monte Carlo Simulation
- 확률분포로 수천 scenario 실행
- 핵심 input의 불확실성 model화
- valuation의 신뢰구간 생성
- 목표 달성 확률 계산

### 4. Scenario Planning
- 최선/기본/최악 scenario 구축
- 서로 다른 경제 환경 model화
- 전략적 대안 테스트
- 결과 확률 비교

## 입력 요구 사항

### DCF 분석
- 과거 재무제표(3~5년)
- 매출 성장 가정
- 영업이익률 전망
- 자본 지출 예측
- 운전자본 요구
- terminal growth rate 또는 exit multiple
- discount rate 구성 요소(risk-free rate, beta, market premium)

### Sensitivity Analysis
- 기본 사례 model
- 테스트할 변수 범위
- 추적할 핵심 metric

### Monte Carlo Simulation
- 불확실한 변수의 확률분포
- 변수 사이의 상관관계 가정
- iteration 수(보통 1,000~10,000)

### Scenario Planning
- scenario 정의와 가정
- scenario 확률 가중치
- 추적할 핵심 성과 지표

## 출력 형식

### DCF Model 출력
- 완전한 재무 전망
- free cash flow 계산
- terminal value 계산
- enterprise 및 equity value 요약
- 내재 valuation multiple
- 전체 model이 있는 Excel workbook

### Sensitivity Analysis 출력
- 값 범위를 보여 주는 sensitivity table
- 핵심 driver의 tornado chart
- break-even 분석
- 관계를 보여 주는 chart

### Monte Carlo 출력
- valuation의 확률분포
- 신뢰구간(예: 90%, 95%)
- 통계 요약(평균, 중앙값, 표준편차)
- risk metric(VaR, 손실 확률)

### Scenario Planning 출력
- scenario 비교 table
- 확률 가중 기대값
- decision tree 시각화
- risk-return profile

## 지원하는 Model 유형

1. **Corporate Valuation**
   - 안정적인 현금흐름의 성숙 기업
   - J-curve 전망을 가진 성장 기업
   - Turnaround 상황

2. **Project Finance**
   - infra 프로젝트
   - 부동산 개발
   - 에너지 프로젝트

3. **M&A 분석**
   - 인수 valuation
   - synergy modeling
   - accretion/dilution 분석

4. **LBO Model**
   - leveraged buyout 분석
   - 수익 분석(IRR, MOIC)
   - 부채 수용 능력 평가

## 적용하는 모범 사례

### Modeling 기준
- 일관된 서식과 구조
- 명확한 가정 문서화
- input, 계산, output 분리
- 오류 확인 및 검증
- version control과 변경 추적

### Valuation 원칙
- 교차 확인을 위해 여러 valuation 방법 사용
- 적절한 risk 조정 적용
- 시장 비교 대상 고려
- trading multiple에 대조하여 검증
- 핵심 가정을 명확히 문서화

### Risk 관리
- 핵심 risk 식별 및 정량화
- 확률 가중 scenario 사용
- 극단적 사례의 stress test
- 상관관계 효과 고려
- 신뢰구간 제공

## 사용 예제

"첨부 재무 자료로 이 기술 회사의 DCF model을 구축하세요"

"이 인수 model에 iteration 5,000회의 Monte Carlo simulation을 실행하세요"

"성장률과 WACC가 valuation에 미치는 영향을 보여 주는 sensitivity analysis를 만드세요"

"이 확장 프로젝트에 확률 가중치를 포함한 세 scenario를 개발하세요"

## 포함된 Script

- `dcf_model.py`: 완전한 DCF valuation engine
- `sensitivity_analysis.py`: sensitivity testing framework

## 제약 및 면책 사항

- model의 품질은 가정의 품질을 넘을 수 없음
- 과거 성과는 미래 결과를 보장하지 않음
- 시장 상황은 빠르게 변할 수 있음
- 규제와 세금 변경이 결과에 영향을 줄 수 있음
- 해석에 전문적인 판단 필요
- 전문적인 재무 조언을 대체하지 않음

## 품질 확인

model이 자동으로 수행하는 것:
1. 재무상태표 균형 확인
2. 현금흐름 reconciliation
3. circular reference 해결
4. sensitivity 범위 확인
5. Monte Carlo 결과의 통계 검증

## 갱신 및 유지 관리

- 최신 재무 이론과 실무 사용
- 시장 parameter 기본값 정기 갱신
- 규제 변경 반영
- 사용 패턴 기반 지속적 개선
