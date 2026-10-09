"""
기업 문서 styling용 brand 적용 module입니다.
Excel, PowerPoint, PDF 문서에 일관된 branding을 적용합니다.
"""

from typing import Any


class BrandFormatter:
    """문서에 기업 brand 지침을 적용합니다."""

    # Brand 색상 정의
    COLORS = {
        "primary": {
            "acme_blue": {"hex": "#0066CC", "rgb": (0, 102, 204)},
            "acme_navy": {"hex": "#003366", "rgb": (0, 51, 102)},
            "white": {"hex": "#FFFFFF", "rgb": (255, 255, 255)},
        },
        "secondary": {
            "success_green": {"hex": "#28A745", "rgb": (40, 167, 69)},
            "warning_amber": {"hex": "#FFC107", "rgb": (255, 193, 7)},
            "error_red": {"hex": "#DC3545", "rgb": (220, 53, 69)},
            "neutral_gray": {"hex": "#6C757D", "rgb": (108, 117, 125)},
            "light_gray": {"hex": "#F8F9FA", "rgb": (248, 249, 250)},
        },
    }

    # Font 정의
    FONTS = {
        "primary": "Segoe UI",
        "fallback": ["system-ui", "-apple-system", "sans-serif"],
        "sizes": {"h1": 32, "h2": 24, "h3": 18, "body": 11, "caption": 9},
        "weights": {"regular": 400, "semibold": 600, "bold": 700},
    }

    # 회사 정보
    COMPANY = {
        "name": "Acme Corporation",
        "tagline": "Innovation Through Excellence",
        "copyright": "© 2025 Acme Corporation. All rights reserved.",
        "website": "www.acmecorp.example",
        "logo_path": "assets/acme_logo.png",
    }

    def __init__(self):
        """표준 설정으로 brand formatter를 초기화합니다."""
        self.colors = self.COLORS
        self.fonts = self.FONTS
        self.company = self.COMPANY

    def format_excel(self, workbook_config: dict[str, Any]) -> dict[str, Any]:
        """
        Excel workbook 설정에 brand 서식을 적용합니다.

        Args:
            workbook_config: Excel workbook 설정 dictionary

        Returns:
            brand가 적용된 workbook 설정
        """
        branded_config = workbook_config.copy()

        # header 서식 적용
        branded_config["header_style"] = {
            "font": {
                "name": self.fonts["primary"],
                "size": self.fonts["sizes"]["body"],
                "bold": True,
                "color": self.colors["primary"]["white"]["hex"],
            },
            "fill": {"type": "solid", "color": self.colors["primary"]["acme_blue"]["hex"]},
            "alignment": {"horizontal": "center", "vertical": "center"},
            "border": {"style": "thin", "color": self.colors["secondary"]["neutral_gray"]["hex"]},
        }

        # data cell 서식 적용
        branded_config["cell_style"] = {
            "font": {
                "name": self.fonts["primary"],
                "size": self.fonts["sizes"]["body"],
                "color": self.colors["primary"]["acme_navy"]["hex"],
            },
            "alignment": {"horizontal": "left", "vertical": "center"},
        }

        # 교대 행 색상 적용
        branded_config["alternating_rows"] = {
            "enabled": True,
            "color": self.colors["secondary"]["light_gray"]["hex"],
        }

        # Chart 색상 구성
        branded_config["chart_colors"] = [
            self.colors["primary"]["acme_blue"]["hex"],
            self.colors["secondary"]["success_green"]["hex"],
            self.colors["secondary"]["warning_amber"]["hex"],
            self.colors["secondary"]["neutral_gray"]["hex"],
        ]

        return branded_config

    def format_powerpoint(self, presentation_config: dict[str, Any]) -> dict[str, Any]:
        """
        PowerPoint presentation 설정에 brand 서식을 적용합니다.

        Args:
            presentation_config: PowerPoint 설정 dictionary

        Returns:
            brand가 적용된 presentation 설정
        """
        branded_config = presentation_config.copy()

        # Slide master 설정
        branded_config["master"] = {
            "background_color": self.colors["primary"]["white"]["hex"],
            "title_area": {
                "font": self.fonts["primary"],
                "size": self.fonts["sizes"]["h1"],
                "color": self.colors["primary"]["acme_blue"]["hex"],
                "bold": True,
                "position": {"x": 0.5, "y": 0.15, "width": 9, "height": 1},
            },
            "content_area": {
                "font": self.fonts["primary"],
                "size": self.fonts["sizes"]["body"],
                "color": self.colors["primary"]["acme_navy"]["hex"],
                "position": {"x": 0.5, "y": 2, "width": 9, "height": 5},
            },
            "footer": {
                "show_slide_number": True,
                "show_date": True,
                "company_name": self.company["name"],
            },
        }

        # Title slide template
        branded_config["title_slide"] = {
            "background": self.colors["primary"]["acme_blue"]["hex"],
            "title_color": self.colors["primary"]["white"]["hex"],
            "subtitle_color": self.colors["primary"]["white"]["hex"],
            "include_logo": True,
            "logo_position": {"x": 0.5, "y": 0.5, "width": 2},
        }

        # Content slide template
        branded_config["content_slide"] = {
            "title_bar": {
                "background": self.colors["primary"]["acme_blue"]["hex"],
                "text_color": self.colors["primary"]["white"]["hex"],
                "height": 1,
            },
            "bullet_style": {"level1": "•", "level2": "○", "level3": "▪", "indent": 0.25},
        }

        # Chart 기본값
        branded_config["charts"] = {
            "color_scheme": [
                self.colors["primary"]["acme_blue"]["hex"],
                self.colors["secondary"]["success_green"]["hex"],
                self.colors["secondary"]["warning_amber"]["hex"],
                self.colors["secondary"]["neutral_gray"]["hex"],
            ],
            "gridlines": {"color": self.colors["secondary"]["neutral_gray"]["hex"], "width": 0.5},
            "font": {"name": self.fonts["primary"], "size": self.fonts["sizes"]["caption"]},
        }

        return branded_config

    def format_pdf(self, document_config: dict[str, Any]) -> dict[str, Any]:
        """
        PDF 문서 설정에 brand 서식을 적용합니다.

        Args:
            document_config: PDF 문서 설정 dictionary

        Returns:
            brand가 적용된 문서 설정
        """
        branded_config = document_config.copy()

        # Page layout
        branded_config["page"] = {
            "margins": {"top": 1, "bottom": 1, "left": 1, "right": 1},
            "size": "letter",
            "orientation": "portrait",
        }

        # Header 설정
        branded_config["header"] = {
            "height": 0.75,
            "content": {
                "left": {"type": "logo", "width": 1.5},
                "center": {
                    "type": "text",
                    "content": document_config.get("title", "Document"),
                    "font": self.fonts["primary"],
                    "size": self.fonts["sizes"]["body"],
                    "color": self.colors["primary"]["acme_navy"]["hex"],
                },
                "right": {"type": "page_number", "format": "Page {page} of {total}"},
            },
        }

        # Footer 설정
        branded_config["footer"] = {
            "height": 0.5,
            "content": {
                "left": {
                    "type": "text",
                    "content": self.company["copyright"],
                    "font": self.fonts["primary"],
                    "size": self.fonts["sizes"]["caption"],
                    "color": self.colors["secondary"]["neutral_gray"]["hex"],
                },
                "center": {"type": "date", "format": "%B %d, %Y"},
                "right": {"type": "text", "content": "Confidential"},
            },
        }

        # 텍스트 스타일
        branded_config["styles"] = {
            "heading1": {
                "font": self.fonts["primary"],
                "size": self.fonts["sizes"]["h1"],
                "color": self.colors["primary"]["acme_blue"]["hex"],
                "bold": True,
                "spacing_after": 12,
            },
            "heading2": {
                "font": self.fonts["primary"],
                "size": self.fonts["sizes"]["h2"],
                "color": self.colors["primary"]["acme_navy"]["hex"],
                "bold": True,
                "spacing_after": 10,
            },
            "heading3": {
                "font": self.fonts["primary"],
                "size": self.fonts["sizes"]["h3"],
                "color": self.colors["primary"]["acme_navy"]["hex"],
                "bold": False,
                "spacing_after": 8,
            },
            "body": {
                "font": self.fonts["primary"],
                "size": self.fonts["sizes"]["body"],
                "color": self.colors["primary"]["acme_navy"]["hex"],
                "line_spacing": 1.15,
                "paragraph_spacing": 12,
            },
            "caption": {
                "font": self.fonts["primary"],
                "size": self.fonts["sizes"]["caption"],
                "color": self.colors["secondary"]["neutral_gray"]["hex"],
                "italic": True,
            },
        }

        # Table 서식
        branded_config["table_style"] = {
            "header": {
                "background": self.colors["primary"]["acme_blue"]["hex"],
                "text_color": self.colors["primary"]["white"]["hex"],
                "bold": True,
            },
            "rows": {
                "alternating_color": self.colors["secondary"]["light_gray"]["hex"],
                "border_color": self.colors["secondary"]["neutral_gray"]["hex"],
            },
        }

        return branded_config

    def validate_colors(self, colors_used: list[str]) -> dict[str, Any]:
        """
        색상이 brand 지침과 일치하는지 검증합니다.

        Args:
            colors_used: 문서에서 사용한 색상 코드 목록

        Returns:
            필요한 수정이 포함된 검증 결과
        """
        results = {"valid": True, "corrections": [], "warnings": []}

        approved_colors = []
        for category in self.colors.values():
            for color in category.values():
                approved_colors.append(color["hex"].upper())

        for color in colors_used:
            color_upper = color.upper()
            if color_upper not in approved_colors:
                results["valid"] = False
                # 가장 가까운 brand 색상 찾기
                closest = self._find_closest_brand_color(color)
                results["corrections"].append(
                    {
                        "original": color,
                        "suggested": closest,
                        "message": f"Non-brand color {color} should be replaced with {closest}",
                    }
                )

        return results

    def _find_closest_brand_color(self, color: str) -> str:
        """주어진 색상에 가장 가까운 brand 색상을 찾습니다."""
        # 간소화 - 실제로는 색상 거리를 계산
        return self.colors["primary"]["acme_blue"]["hex"]

    def apply_watermark(self, document_type: str) -> dict[str, Any]:
        """
        문서의 watermark 설정을 생성합니다.

        Args:
            document_type: 문서 유형(draft, confidential 등)

        Returns:
            Watermark 설정
        """
        watermarks = {
            "draft": {
                "text": "DRAFT",
                "color": self.colors["secondary"]["neutral_gray"]["hex"],
                "opacity": 0.1,
                "angle": 45,
                "font_size": 72,
            },
            "confidential": {
                "text": "CONFIDENTIAL",
                "color": self.colors["secondary"]["error_red"]["hex"],
                "opacity": 0.1,
                "angle": 45,
                "font_size": 60,
            },
            "sample": {
                "text": "SAMPLE",
                "color": self.colors["secondary"]["warning_amber"]["hex"],
                "opacity": 0.15,
                "angle": 45,
                "font_size": 72,
            },
        }

        return watermarks.get(document_type, watermarks["draft"])

    def get_chart_palette(self, num_series: int = 4) -> list[str]:
        """
        chart의 color palette를 얻습니다.

        Args:
            num_series: data series 수

        Returns:
            hex 색상 코드 목록
        """
        palette = [
            self.colors["primary"]["acme_blue"]["hex"],
            self.colors["secondary"]["success_green"]["hex"],
            self.colors["secondary"]["warning_amber"]["hex"],
            self.colors["secondary"]["neutral_gray"]["hex"],
            self.colors["primary"]["acme_navy"]["hex"],
            self.colors["secondary"]["error_red"]["hex"],
        ]

        return palette[:num_series]

    def format_number(self, value: float, format_type: str = "general") -> str:
        """
        brand 기준에 따라 숫자 형식을 지정합니다.

        Args:
            value: 형식을 지정할 숫자 값
            format_type: 서식 유형(currency, percentage, general)

        Returns:
            서식 지정 문자열
        """
        if format_type == "currency":
            return f"${value:,.2f}"
        elif format_type == "percentage":
            return f"{value:.1f}%"
        elif format_type == "large_number":
            if value >= 1_000_000:
                return f"{value / 1_000_000:.1f}M"
            elif value >= 1_000:
                return f"{value / 1_000:.1f}K"
            else:
                return f"{value:.0f}"
        else:
            return f"{value:,.0f}" if value >= 1000 else f"{value:.2f}"


def apply_brand_to_document(document_type: str, config: dict[str, Any]) -> dict[str, Any]:
    """
    어떤 문서 유형에든 branding을 적용하는 주요 함수입니다.

    Args:
        document_type: 문서 유형('excel', 'powerpoint', 'pdf')
        config: 문서 설정

    Returns:
        brand가 적용된 설정
    """
    formatter = BrandFormatter()

    if document_type.lower() == "excel":
        return formatter.format_excel(config)
    elif document_type.lower() in ["powerpoint", "pptx"]:
        return formatter.format_powerpoint(config)
    elif document_type.lower() == "pdf":
        return formatter.format_pdf(config)
    else:
        raise ValueError(f"Unsupported document type: {document_type}")


# 사용 예제
if __name__ == "__main__":
    # Excel 설정 예제
    excel_config = {"title": "Quarterly Report", "sheets": ["Summary", "Details"]}

    branded_excel = apply_brand_to_document("excel", excel_config)
    print("Branded Excel Configuration:")
    print(branded_excel)

    # PowerPoint 설정 예제
    ppt_config = {"title": "Business Review", "num_slides": 10}

    branded_ppt = apply_brand_to_document("powerpoint", ppt_config)
    print("\nBranded PowerPoint Configuration:")
    print(branded_ppt)
