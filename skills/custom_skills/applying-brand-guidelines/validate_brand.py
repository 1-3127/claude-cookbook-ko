#!/usr/bin/env python3
"""
Brand 검증 Script
색상, font, 어조, 메시지를 포함한 brand 지침에 대조해 content를 검증합니다.
"""

import json
import re
from dataclasses import asdict, dataclass


@dataclass
class BrandGuidelines:
    """Brand 지침 설정"""

    brand_name: str
    primary_colors: list[str]
    secondary_colors: list[str]
    fonts: list[str]
    tone_keywords: list[str]
    prohibited_words: list[str]
    tagline: str | None = None
    logo_usage_rules: dict | None = None


@dataclass
class ValidationResult:
    """brand 검증 결과"""

    passed: bool
    score: float
    violations: list[str]
    warnings: list[str]
    suggestions: list[str]


class BrandValidator:
    """brand 지침에 대조해 content 검증"""

    def __init__(self, guidelines: BrandGuidelines):
        self.guidelines = guidelines

    def validate_colors(self, content: str) -> tuple[list[str], list[str]]:
        """
        content의 색상 사용 검증(hex 코드, RGB, 색상 이름)
        Returns: (violations, warnings)
        """
        violations = []
        warnings = []

        # hex 색상 찾기
        hex_pattern = r"#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3}"
        found_colors = re.findall(hex_pattern, content)

        # RGB 색상 찾기
        rgb_pattern = r"rgb\s*\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)"
        found_colors.extend(re.findall(rgb_pattern, content, re.IGNORECASE))

        approved_colors = self.guidelines.primary_colors + self.guidelines.secondary_colors

        for color in found_colors:
            if color.upper() not in [c.upper() for c in approved_colors]:
                violations.append(f"Unapproved color used: {color}")

        return violations, warnings

    def validate_fonts(self, content: str) -> tuple[list[str], list[str]]:
        """
        content의 font 사용 검증
        Returns: (violations, warnings)
        """
        violations = []
        warnings = []

        # 일반적인 font 지정 패턴
        font_patterns = [
            r'font-family\s*:\s*["\']?([^;"\']+)["\']?',
            r"font:\s*[^;]*\s+([A-Za-z][A-Za-z\s]+)(?:,|;|\s+\d)",
        ]

        found_fonts = []
        for pattern in font_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            found_fonts.extend(matches)

        for font in found_fonts:
            font_clean = font.strip().lower()
            # 찾은 font 문자열에 승인된 font가 있는지 확인
            if not any(approved.lower() in font_clean for approved in self.guidelines.fonts):
                violations.append(f"Unapproved font used: {font}")

        return violations, warnings

    def validate_tone(self, content: str) -> tuple[list[str], list[str]]:
        """
        어조와 메시지 검증
        Returns: (violations, warnings)
        """
        violations = []
        warnings = []

        # 금지 단어 확인
        content_lower = content.lower()
        for word in self.guidelines.prohibited_words:
            if word.lower() in content_lower:
                violations.append(f"Prohibited word/phrase used: '{word}'")

        # 어조 keyword 확인(최소 일부 있어야 함)
        tone_matches = sum(
            1 for keyword in self.guidelines.tone_keywords if keyword.lower() in content_lower
        )

        if tone_matches == 0 and len(content) > 100:
            warnings.append(
                f"Content may not align with brand tone. "
                f"Consider using terms like: {', '.join(self.guidelines.tone_keywords[:5])}"
            )

        return violations, warnings

    def validate_brand_name(self, content: str) -> tuple[list[str], list[str]]:
        """
        brand 이름 사용과 대소문자 검증
        Returns: (violations, warnings)
        """
        violations = []
        warnings = []

        # brand 이름의 모든 변형 찾기
        brand_pattern = re.compile(re.escape(self.guidelines.brand_name), re.IGNORECASE)
        matches = brand_pattern.findall(content)

        for match in matches:
            if match != self.guidelines.brand_name:
                violations.append(
                    f"Incorrect brand name capitalization: '{match}' "
                    f"should be '{self.guidelines.brand_name}'"
                )

        return violations, warnings

    def calculate_score(self, violations: list[str], warnings: list[str]) -> float:
        """준수 점수 계산(0~100)"""
        violation_penalty = len(violations) * 10
        warning_penalty = len(warnings) * 3

        score = max(0, 100 - violation_penalty - warning_penalty)
        return round(score, 2)

    def generate_suggestions(self, violations: list[str], warnings: list[str]) -> list[str]:
        """위반과 경고에 따른 유용한 제안 생성"""
        suggestions = []

        if any("color" in v.lower() for v in violations):
            suggestions.append(
                f"Use approved colors: Primary: {', '.join(self.guidelines.primary_colors[:3])}"
            )

        if any("font" in v.lower() for v in violations):
            suggestions.append(f"Use approved fonts: {', '.join(self.guidelines.fonts)}")

        if any("tone" in w.lower() for w in warnings):
            suggestions.append(
                f"Incorporate brand tone keywords: {', '.join(self.guidelines.tone_keywords[:5])}"
            )

        if any("brand name" in v.lower() for v in violations):
            suggestions.append(f"Always capitalize brand name as: {self.guidelines.brand_name}")

        return suggestions

    def validate(self, content: str) -> ValidationResult:
        """
        전체 brand 검증 수행
        Returns: ValidationResult
        """
        all_violations = []
        all_warnings = []

        # 모든 검증 실행
        color_v, color_w = self.validate_colors(content)
        all_violations.extend(color_v)
        all_warnings.extend(color_w)

        font_v, font_w = self.validate_fonts(content)
        all_violations.extend(font_v)
        all_warnings.extend(font_w)

        tone_v, tone_w = self.validate_tone(content)
        all_violations.extend(tone_v)
        all_warnings.extend(tone_w)

        brand_v, brand_w = self.validate_brand_name(content)
        all_violations.extend(brand_v)
        all_warnings.extend(brand_w)

        # 점수 계산 및 제안 생성
        score = self.calculate_score(all_violations, all_warnings)
        suggestions = self.generate_suggestions(all_violations, all_warnings)

        return ValidationResult(
            passed=len(all_violations) == 0,
            score=score,
            violations=all_violations,
            warnings=all_warnings,
            suggestions=suggestions,
        )


def load_guidelines_from_json(filepath: str) -> BrandGuidelines:
    """
    JSON 파일에서 brand 지침 로딩

    Args:
        filepath: brand 지침이 있는 JSON 파일 경로

    Returns:
        BrandGuidelines 객체

    Raises:
        FileNotFoundError: 파일이 없으면
        json.JSONDecodeError: 파일에 유효하지 않은 JSON이 있으면
        TypeError: 필수 field가 누락되면
    """
    try:
        with open(filepath) as f:
            data = json.load(f)
        return BrandGuidelines(**data)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Brand guidelines file not found: {filepath}") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in brand guidelines file: {e.msg}", e.doc, e.pos
        ) from e
    except TypeError as e:
        raise TypeError(f"Missing required fields in brand guidelines: {e}") from e


def get_acme_corporation_guidelines() -> BrandGuidelines:
    """
    기본 Acme Corporation brand 지침을 얻습니다.

    이 지침은 SKILL.md reference에 정의된 기준과 일치합니다.
    사용자는 자신의 조직에 맞게 사용자 지정해야 합니다.

    Returns:
        Acme Corporation 기준이 있는 BrandGuidelines 객체
    """
    return BrandGuidelines(
        brand_name="Acme Corporation",
        primary_colors=["#0066CC", "#003366", "#FFFFFF"],  # Acme Blue, Acme Navy, White
        secondary_colors=[
            "#28A745",
            "#FFC107",
            "#DC3545",
            "#6C757D",
            "#F8F9FA",
        ],  # Success Green, Warning Amber, Error Red, Neutral Gray, Light Gray
        fonts=["Segoe UI", "system-ui", "-apple-system", "sans-serif"],
        tone_keywords=[
            "innovation",
            "excellence",
            "professional",
            "solutions",
            "trusted",
            "reliable",
        ],
        prohibited_words=["cheap", "outdated", "inferior", "unprofessional", "sloppy"],
        tagline="Innovation Through Excellence",
    )


def main():
    """brand 검증을 보여 주는 사용 예제"""
    # Acme Corporation brand 지침 불러오기
    # 사용자는 자신의 조직에 맞게 사용자 지정해야 함
    guidelines = get_acme_corporation_guidelines()

    # 검증할 예제 content(시연용으로 의도적인 위반 포함)
    test_content = """
    Welcome to acme corporation!

    We are a cheap solution provider with outdated technology.

    Our innovation and excellence in professional solutions are trusted by many.

    Contact us at: font-family: 'Comic Sans MS'
    Color scheme: #FF0000
    Background: rgb(255, 0, 0)
    """

    # 검증
    validator = BrandValidator(guidelines)
    result = validator.validate(test_content)

    # 결과 출력
    print("=" * 60)
    print("BRAND VALIDATION REPORT")
    print("=" * 60)
    print(f"\nOverall Status: {'✓ PASSED' if result.passed else '✗ FAILED'}")
    print(f"Compliance Score: {result.score}/100")

    if result.violations:
        print(f"\n❌ VIOLATIONS ({len(result.violations)}):")
        for i, violation in enumerate(result.violations, 1):
            print(f"  {i}. {violation}")

    if result.warnings:
        print(f"\n⚠️  WARNINGS ({len(result.warnings)}):")
        for i, warning in enumerate(result.warnings, 1):
            print(f"  {i}. {warning}")

    if result.suggestions:
        print("\n💡 SUGGESTIONS:")
        for i, suggestion in enumerate(result.suggestions, 1):
            print(f"  {i}. {suggestion}")

    print("\n" + "=" * 60)

    # programmatic 사용을 위해 JSON 반환
    return asdict(result)


if __name__ == "__main__":
    main()
