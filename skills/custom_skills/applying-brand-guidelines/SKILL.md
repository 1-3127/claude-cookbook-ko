---
name: applying-brand-guidelines
description: 이 skill은 색상, font, layout, 메시지를 포함해 생성되는 모든 문서에 일관된 기업 branding과 styling을 적용합니다
---

# 기업 Brand 지침 Skill

이 skill은 일관되고 전문적인 소통을 위해 생성되는 모든 문서가 기업 brand 기준을 따르도록 합니다.

## Brand Identity

### 회사: Acme Corporation
**Tagline**: "탁월함을 통한 혁신"
**업종**: 기술 솔루션

## 시각적 기준

### Color Palette

**주요 색상**:
- **Acme Blue**: #0066CC (RGB: 0, 102, 204) - header, 주요 button
- **Acme Navy**: #003366 (RGB: 0, 51, 102) - 텍스트, 강조
- **White**: #FFFFFF - 배경, 반전 텍스트

**보조 색상**:
- **Success Green**: #28A745 (RGB: 40, 167, 69) - 긍정적 metric
- **Warning Amber**: #FFC107 (RGB: 255, 193, 7) - 주의
- **Error Red**: #DC3545 (RGB: 220, 53, 69) - 음수 값
- **Neutral Gray**: #6C757D (RGB: 108, 117, 125) - 보조 텍스트

### Typography

**주요 Font Family**: Segoe UI, system-ui, -apple-system, sans-serif

**Font 계층**:
- **H1**: 32pt, Bold, Acme Blue
- **H2**: 24pt, Semibold, Acme Navy
- **H3**: 18pt, Semibold, Acme Navy
- **본문**: 11pt, Regular, Acme Navy
- **Caption**: 9pt, Regular, Neutral Gray

### Logo 사용

- 위치: 첫 페이지/slide의 왼쪽 위
- 크기: 너비 120px(종횡비 유지)
- 여백: 모든 방향 최소 20px padding
- 변형, 회전, 효과 적용 금지

## 문서 기준

### PowerPoint Presentation

**Slide Template**:
1. **Title Slide**: 회사 logo, presentation 제목, 날짜, 발표자
2. **Section 구분**: 파란 배경의 section 제목
3. **Content Slide**: 파란 배경 title bar, 흰 content 영역
4. **Data Slide**: chart/graph용, color palette 유지

**Layout 규칙**:
- margin: 모든 방향 0.5 inch
- 제목 위치: slide 상단 15%
- bullet 들여쓰기: level당 0.25 inch
- slide당 최대 6개의 bullet point
- chart에는 brand 색상만 사용

### Excel Spreadsheet

**서식 기준**:
- **Header**: 1행, Bold, Acme Blue 배경의 흰 텍스트
- **Subheader**: Bold, Acme Navy 텍스트
- **Data cell**: Regular, Acme Navy 텍스트
- **테두리**: 얇게, Neutral Gray
- **교대 행**: 가독성을 위한 밝은 회색(#F8F9FA)

**Chart 기본값**:
- 주요 series: Acme Blue
- 보조 series: Success Green
- gridline: Neutral Gray, 0.5pt
- 3D 효과나 gradient 없음

### PDF 문서

**Page Layout**:
- **Header**: 왼쪽 회사 logo, 가운데 문서 제목, 오른쪽 페이지 번호
- **Footer**: 왼쪽 저작권 고지, 가운데 날짜, 오른쪽 분류
- **Margin**: 모든 방향 1 inch
- **줄 간격**: 1.15
- **문단 간격**: 뒤에 12pt

**Section 서식**:
- 주요 heading: Acme Blue, 16pt, bold
- subheading: Acme Navy, 14pt, semibold
- 본문: Acme Navy, 11pt, regular

## Content 지침

### 어조

- **전문적**: 격식을 갖추되 다가가기 쉽게
- **명확함**: jargon을 피하고 쉬운 언어 사용
- **능동적**: 능동태 사용, 행동 중심
- **긍정적**: 해결책과 이점에 집중

### 표준 문구

**시작 문구**:
- "Acme Corporation에서 우리는..."
- "혁신에 대한 우리의 약속..."
- "...을 통해 탁월함을 제공..."

**마무리 문구**:
- "지속적인 협력에 감사드립니다."
- "여러분의 요구에 부응하기를 기대합니다."
- "함께 탁월함을 이룹니다."

### Data 표현

**숫자**:
- 천 단위 쉼표 구분자 사용
- 통화: $X,XXX.XX 형식
- 백분율: XX.X%(소수점 한 자리)
- 날짜: Month DD, YYYY

**Table**:
- header는 brand blue
- 교대 행 색상
- 숫자 오른쪽 정렬
- 텍스트 왼쪽 정렬

## 품질 기준

### 완료 전

항상 확인:
1. Logo 위치와 크기가 적절함
2. 모든 색상이 brand palette와 정확히 일치
3. 전체 font 일관성
4. 오타나 문법 오류 없음
5. Data가 정확히 표현됨
6. 전문적인 어조 유지

### 금지 요소

사용 금지:
- 승인 없는 clip art나 stock photo
- Comic Sans, Papyrus, 장식 font
- 무지개색이나 gradient
- animation이나 transition(지정하지 않는 한)
- 경쟁사 branding이나 언급

## 적용 지시

어떤 문서든 생성할 때:
1. brand 색상과 font로 시작
2. 적절한 template 구조 적용
3. 첫 페이지/slide에 logo 포함
4. 전체에서 일관된 서식 사용
5. brand 기준에 대조해 검토
6. 전문적인 외관 보장

## Script

- `apply_brand.py`: 문서에 brand 서식 자동 적용
- `validate_brand.py`: 문서의 brand 준수 확인

## 참고

- 모든 외부 소통에 이 지침 적용
- 내부 문서는 간소한 서식 사용 가능
- 특별 프로젝트에 예외가 있을 수 있음(승인 요청)
- Brand 지침은 분기별 갱신 - 최신 버전 확인
