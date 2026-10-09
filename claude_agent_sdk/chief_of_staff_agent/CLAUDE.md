# CLAUDE.md - Chief of Staff Context

## 회사 개요
- **회사**: TechStart Inc
- **단계**: Series A(2024년 1월 $10M 유치 완료)
- **산업**: B2B SaaS - AI 기반 developer tool
- **설립**: 2022년
- **본사**: San Francisco, CA

## 재무 현황
- **월 Burn Rate**: 약 $500,000
- **현재 Runway**: 20개월(2025년 9월까지)
- **ARR**: $2.4M(MoM 15% 성장)
- **은행 현금**: $10M
- **직원당 매출**: $48K

## 팀 구조
- **총 인원**: 50
- **Engineering**: 25(50%)
  - Backend: 12
  - Frontend: 8
  - DevOps/SRE: 5
- **영업 및 Marketing**: 12(24%)
- **Product**: 5(10%)
- **운영**: 5(10%)
- **경영진**: 3(6%)

## 핵심 Metrics
- **고객 수**: Enterprise 고객 120개
- **NPS 점수**: 72
- **월 Churn**: 2.5%
- **CAC**: $15,000
- **LTV**: $85,000
- **CAC 회수 기간**: 10개월

## 현재 우선순위(2024년 Q2)
1. **채용**: 제품 개발을 가속하기 위해 engineer 10명 추가
2. **제품**: Q2 말까지 AI code review 기능 출시
3. **영업**: 유럽 시장 진출
4. **자금 조달**: Series B 논의 시작(목표: $30M)

## 보상 기준
- **Senior Engineer**: $180K - $220K + 지분 0.1-0.3%
- **Junior Engineer**: $100K - $130K + 지분 0.05-0.1%
- **Engineering Manager**: $200K - $250K + 지분 0.3-0.5%
- **VP Engineering**: $250K - $300K + 지분 0.5-1%

## 이사회 구성
- **CEO**: Sarah Chen(창업자)
- **투자자 1**: Mark Williams(Sequoia Capital)
- **투자자 2**: Jennifer Park(Andreessen Horowitz)
- **독립 이사**: Michael Torres(전 GitHub CTO)

## 경쟁 환경
- **주요 경쟁사**: DevTools AI, CodeAssist Pro, SmartDev Inc
- **차별점**: 우수한 AI 정확도, 10배 빠른 처리
- **시장 규모**: $5B(연 25% 성장)

## 최근 결정
- Senior backend engineer 3명 채용 승인(2024년 3월)
- Freemium tier 출시(2024년 2월)
- 유럽 법인 설립(2024년 1월)
- Series A 자금 조달 완료(2024년 1월)

## 예정된 결정
- 경쟁사 SmartDev Inc 인수 여부(요구 가격 $8M)
- Q3 채용 계획(engineering과 영업 중 어디에 집중할지)
- 사무실 확장과 remote-first 전략 중 선택
- 초기 직원의 stock option 갱신

## 위험 요인
- 높은 AWS 의존도(COGS의 70%)
- 핵심 engineer 유지(중요 팀원 3명)
- Big Tech의 경쟁 심화
- 경기 침체가 enterprise 영업에 미칠 잠재적 영향

## 사용 가능한 Script

### simple_calculation.py
Runway 및 burn rate 분석을 위한 빠른 재무 metrics 계산기입니다.
Script 위치: `./scripts/simple_calculation.py`

**사용법:**
```bash
python scripts/simple_calculation.py <total_runway> <monthly_burn>
```

**예제:**
```bash
python scripts/simple_calculation.py 10000000 500000
```

**출력:** monthly_burn, runway_months, total_runway_dollars, quarterly_burn, burn_rate_daily를 포함하는 JSON

기억하세요: Chief of Staff로서 financial_data/ 디렉터리의 재무 data에 접근할 수 있으며 전문 분석을 subagent(financial-analyst 및 recruiter)에 위임할 수 있습니다.
