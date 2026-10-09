#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "nbconvert",
# ]
# ///
"""
Anthropic Cookbook Notebook의 자동 검증 검사입니다.
일반적인 문제를 발견하도록 수동 검토 전에 실행하세요.

사용법:
    python validate_notebook.py <notebook.ipynb>

Exit code:
    0 - 발견된 문제 없음
    1 - 중대한 문제 발견(반드시 수정)
"""

import json
import re
import subprocess
import sys
from pathlib import Path


class NotebookValidator:
    def __init__(self, notebook_path: str):
        self.notebook_path = Path(notebook_path)
        self.issues: list[str] = []
        self.warnings: list[str] = []
        self.markdown_output: Path | None = None

        if not self.notebook_path.exists():
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")

        with open(self.notebook_path, encoding="utf-8") as f:
            self.nb = json.load(f)

        self.cells = self.nb.get("cells", [])

    def get_cell_source(self, cell: dict) -> str:
        """셀 source를 하나의 문자열로 가져옵니다."""
        source = cell.get("source", [])
        if isinstance(source, list):
            return "".join(source)
        return source

    def convert_to_markdown(self) -> Path:
        """
        검토하기 쉽도록 Notebook을 Markdown으로 변환합니다.
        임시 디렉터리의 Markdown 파일 경로를 반환합니다.
        Context를 절약하도록 코드 셀은 포함하고 출력은 제외합니다.
        Dependency와 함께 jupyter nbconvert를 실행하도록 uv를 사용합니다.
        """
        # Skill 폴더 안에 임시 디렉터리 생성
        skill_dir = Path(__file__).parent
        temp_dir = skill_dir / "tmp"
        temp_dir.mkdir(exist_ok=True)

        # 출력 파일명 생성
        output_file = temp_dir / f"{self.notebook_path.stem}_review.md"

        # Nbconvert dependency와 함께 jupyter nbconvert를 실행하도록 uv 사용
        # 깔끔한 검토를 위해 코드는 포함하고 출력은 제외
        cmd = [
            "uv",
            "run",
            "--with",
            "nbconvert",
            "jupyter",
            "nbconvert",
            "--to",
            "markdown",
            "--output",
            str(output_file.absolute()),
            "--no-prompt",  # 입력/출력 prompt 제거
            "--TemplateExporter.exclude_output=True",  # Exclude cell outputs
            str(self.notebook_path.absolute()),
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603

        self.markdown_output = output_file
        return output_file

    def check_hardcoded_secrets(self):
        """Detect-secrets로 hardcoded API key와 secret을 확인합니다."""
        try:
            # Notebook 파일에 detect-secrets 실행
            # Cwd와 관계없이 작동하도록 절대 경로 사용
            notebook_abs = self.notebook_path.absolute()

            # 프로젝트 루트 찾기(.git을 찾거나 발견할 때까지 상위로 이동)
            project_root = notebook_abs.parent
            while project_root.parent != project_root:
                if (project_root / ".git").exists():
                    break
                project_root = project_root.parent

            # 여러 위치에서 baseline 확인
            baseline_paths = [
                project_root / "scripts" / "detect-secrets" / ".secrets.baseline",
                project_root / ".secrets.baseline",
            ]
            baseline_path = None
            for path in baseline_paths:
                if path.exists():
                    baseline_path = path
                    break

            plugins_path = project_root / "scripts" / "detect-secrets" / "plugins.py"

            # Baseline이 있으면 포함하여 명령 구성
            if baseline_path:
                cmd = [
                    "sh",
                    "-c",
                    f"echo '{notebook_abs}' | tr '\\n' '\\0' | xargs -0 uvx --from detect-secrets detect-secrets-hook --baseline {baseline_path} --plugin {plugins_path} --verbose",
                ]
            else:
                cmd = [
                    "sh",
                    "-c",
                    f"echo '{notebook_abs}' | tr '\\n' '\\0' | xargs -0 uvx --from detect-secrets detect-secrets-hook",
                ]

            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root,  # scripts/detect-secrets에 접근할 수 있도록 repo root에서 실행
            )

            # Detect-secrets는 secret을 발견하면 0이 아닌 exit code 반환
            if result.returncode != 0:
                # Stdout과 stderr 모두에서 출력 확인(detect-secrets는 stdout 사용)
                output = result.stdout.strip() or result.stderr.strip()

                if output:
                    # 출력에서 secret 위치 추출
                    secret_lines = [
                        line
                        for line in output.split("\n")
                        if "Location:" in line or "Secret Type:" in line
                    ]

                    if secret_lines:
                        self.issues.append(
                            "Contains potential hardcoded secrets (see details below)"
                        )
                        # 검토를 위해 전체 detect-secrets 출력 표시
                        print(f"\n{'=' * 60}")
                        print("DETECT-SECRETS OUTPUT:")
                        print(f"{'=' * 60}")
                        print(output)
                        print(f"{'=' * 60}\n")
                    else:
                        self.issues.append(
                            f"Contains potential secrets. "
                            f"Run 'detect-secrets-hook {self.notebook_path}' for details."
                        )
                else:
                    self.issues.append(
                        f"Potential secrets detected. "
                        f"Run 'detect-secrets-hook {self.notebook_path}' for details."
                    )

        except FileNotFoundError:
            # Detect-secrets를 사용할 수 없으면 기본 pattern matching으로 fallback
            self.warnings.append(
                "detect-secrets not found - using basic secret detection. "
                "Install with: pip install detect-secrets"
            )
            self._check_hardcoded_secrets_fallback()
        except Exception as e:
            self.warnings.append(f"Error running detect-secrets: {e}")
            self._check_hardcoded_secrets_fallback()

    def _check_hardcoded_secrets_fallback(self):
        """Detect-secrets를 사용할 수 없으면 기본 secret 감지로 fallback합니다."""
        patterns = {
            "Anthropic API key": r"sk-ant-[a-zA-Z0-9-]+",
            "OpenAI API key": r"sk-[a-zA-Z0-9]{32,}",
            "Generic secret": r'(secret|password|token)\s*=\s*["\'][^"\']{20,}["\']',
        }

        for i, cell in enumerate(self.cells):
            source = self.get_cell_source(cell)
            for secret_type, pattern in patterns.items():
                if re.search(pattern, source, re.IGNORECASE):
                    self.issues.append(f"Cell {i}: Contains hardcoded {secret_type}")

    def check_introduction(self):
        """적절한 도입부가 있는지 확인합니다."""
        if not self.cells:
            self.issues.append("Notebook is empty")
            return

        first_cell = self.cells[0]
        if first_cell.get("cell_type") != "markdown":
            self.issues.append("First cell is not markdown (should be introduction)")
            return

        intro_text = self.get_cell_source(first_cell)

        # 최소 길이 확인
        if len(intro_text) < 200:
            self.warnings.append(
                "Introduction seems too short (< 200 chars). Should include "
                "problem statement, audience, and what will be accomplished"
            )

        # 핵심 요소 확인
        has_prerequisites = bool(
            re.search(r"prerequisite|requirement|need|require", intro_text, re.IGNORECASE)
        )
        if not has_prerequisites:
            self.warnings.append("Introduction doesn't mention prerequisites")

    def check_pip_install_output(self):
        """Pip install 출력이 억제되는지 확인합니다."""
        for i, cell in enumerate(self.cells):
            if cell.get("cell_type") != "code":
                continue

            source = self.get_cell_source(cell)
            has_pip_install = "pip install" in source
            has_capture = "%%capture" in source or "%pip install" in source

            if has_pip_install and not has_capture:
                self.warnings.append(
                    f"Cell {i}: pip install without output suppression (use %%capture or %pip)"
                )

    def check_code_explanations(self):
        """코드 블록 앞에 설명 텍스트가 있는지 확인합니다."""
        prev_cell_type = None

        for i, cell in enumerate(self.cells):
            cell_type = cell.get("cell_type")

            if cell_type == "code" and prev_cell_type == "code":
                # 연속된 두 코드 셀 - 설명이 누락되었을 수 있음
                source = self.get_cell_source(cell)
                # 단순한 연속이면 건너뛰기(예: print 문)
                if source.strip() and not source.strip().startswith("#"):
                    self.warnings.append(
                        f"Cell {i}: Code cell without preceding markdown "
                        "explanation (two code cells in a row)"
                    )

            prev_cell_type = cell_type

    def check_verbose_output(self):
        """장황한 debug 출력을 확인합니다."""
        verbose_patterns = [
            r'print\(["\']debug',
            r"\.debug\(",
            r"verbose\s*=\s*True",
        ]

        for i, cell in enumerate(self.cells):
            if cell.get("cell_type") != "code":
                continue

            source = self.get_cell_source(cell)
            for pattern in verbose_patterns:
                if re.search(pattern, source, re.IGNORECASE):
                    self.warnings.append(f"Cell {i}: Contains verbose debug output")

    def check_variable_names(self):
        """좋지 않은 변수 네이밍을 확인합니다."""
        poor_names = [r"\bx\d*\b", r"\btemp\d*\b", r"\bresult\d*\b", r"\bdata\d*\b"]

        for i, cell in enumerate(self.cells):
            if cell.get("cell_type") != "code":
                continue

            source = self.get_cell_source(cell)
            for pattern in poor_names:
                matches = re.findall(pattern, source)
                if matches:
                    self.warnings.append(
                        f"Cell {i}: Contains unclear variable names: {', '.join(set(matches))}"
                    )
                    break  # cell당 한 번만 경고

    def check_model_constant(self):
        """Model 이름이 상단에 상수로 정의되어 있는지 확인합니다."""
        model_constant_pattern = r'(MODEL|model|MODEL_NAME|model_name)\s*=\s*["\']claude-'

        # 처음 5개 코드 셀에서 model 상수 정의 확인
        code_cells_checked = 0
        found_constant = False

        for cell in self.cells:
            if cell.get("cell_type") != "code":
                continue

            code_cells_checked += 1
            if code_cells_checked > 5:
                break

            source = self.get_cell_source(cell)
            if re.search(model_constant_pattern, source):
                found_constant = True
                break

        if not found_constant:
            # Model 참조가 있는지 확인
            has_model_refs = False
            for cell in self.cells:
                if cell.get("cell_type") != "code":
                    continue
                source = self.get_cell_source(cell)
                if re.search(r'["\']claude-', source):
                    has_model_refs = True
                    break

            if has_model_refs:
                self.warnings.append(
                    "Model name should be defined as a constant at the top of the notebook "
                    "(e.g., MODEL = 'claude-sonnet-4-6') to make future updates easier"
                )

    def check_deprecated_patterns(self):
        """Deprecated API 패턴과 유효하지 않은 model을 확인합니다."""
        # 유효한 model
        valid_models = [
            "claude-fable-5",
            "claude-sonnet-5",
            "claude-opus-4-8",
            "claude-sonnet-4-6",
            "claude-haiku-4-5",
            "claude-opus-4-6",
        ]

        # Model 문자열과 일치하는 pattern
        model_pattern = r'["\']claude-([a-z0-9\.-]+)["\']'

        # Migration해야 하는 deprecated model
        deprecated_models = {
            "claude-opus-4-1": "claude-opus-4-6",
        }

        deprecated_patterns = {
            r"\.completion\(": "Using old completion API (use messages API)",
        }

        for i, cell in enumerate(self.cells):
            if cell.get("cell_type") != "code":
                continue

            source = self.get_cell_source(cell)

            # 날짜가 있는 API model ID 확인(날짜가 필요한 Bedrock ID 제외)
            dated_pattern = r'["\']claude-\w+-[\d.]+-\d{8}["\']'
            dated_matches = re.findall(dated_pattern, source)
            for match in dated_matches:
                # 날짜가 필요한 Bedrock model ID(anthropic.claude-*) 건너뛰기
                if f"anthropic.{match.strip(chr(34)).strip(chr(39))}" not in source:
                    self.issues.append(
                        f"Cell {i}: Dated model ID {match} found. "
                        "Use non-dated aliases instead (e.g., claude-sonnet-4-6)"
                    )

            # 유효하지 않거나 deprecated된 model 확인
            model_matches = re.findall(model_pattern, source)
            for match in model_matches:
                full_model = f"claude-{match}"
                if full_model in deprecated_models:
                    self.warnings.append(
                        f"Cell {i}: Deprecated model '{full_model}'. "
                        f"Please update to '{deprecated_models[full_model]}'"
                    )
                elif full_model not in valid_models:
                    self.issues.append(
                        f"Cell {i}: Invalid model '{full_model}'. "
                        f"Valid models are: {', '.join(valid_models)}"
                    )

            # 기타 deprecated pattern 확인
            for pattern, message in deprecated_patterns.items():
                if re.search(pattern, source):
                    self.warnings.append(f"Cell {i}: {message}")

    def check_conclusion(self):
        """결론 섹션이 있는지 확인합니다."""
        if len(self.cells) < 3:
            return  # 결론을 요구하기에는 너무 짧음

        # 마지막 몇 개 셀에서 결론에 해당하는 내용 확인
        last_markdown = None
        for cell in reversed(self.cells[-5:]):
            if cell.get("cell_type") == "markdown":
                last_markdown = self.get_cell_source(cell)
                break

        if not last_markdown:
            self.warnings.append("No conclusion or summary section found")
        elif len(last_markdown) < 100:
            self.warnings.append("Conclusion section seems too brief")

    def run_all_checks(self):
        """모든 검증 검사를 실행합니다."""
        self.check_hardcoded_secrets()
        self.check_introduction()
        self.check_pip_install_output()
        self.check_code_explanations()
        self.check_verbose_output()
        self.check_variable_names()
        self.check_model_constant()
        self.check_deprecated_patterns()
        self.check_conclusion()

    def print_report(self):
        """검증 보고서를 출력합니다."""
        print(f"\n{'=' * 60}")
        print(f"Validation Report: {self.notebook_path.name}")
        print(f"{'=' * 60}\n")

        if self.markdown_output and self.markdown_output.exists():
            print(f"📄 Markdown review file: {self.markdown_output}")
            print("   (More readable format for detailed review)\n")

        if self.issues:
            print("CRITICAL ISSUES (must fix):")
            for issue in self.issues:
                print(f"  ❌ {issue}")
            print()

        if self.warnings:
            print("WARNINGS (should review):")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
            print()

        if not self.issues and not self.warnings:
            print("✅ No automated issues found!\n")
            print("Note: This doesn't replace manual review for:")
            print("  - Content quality and narrative flow")
            print("  - Technical accuracy of explanations")
            print("  - Appropriateness of examples")
            print("  - Overall pedagogical effectiveness")

        print(f"\n{'=' * 60}")
        print(f"Summary: {len(self.issues)} critical issues, {len(self.warnings)} warnings")
        print(f"{'=' * 60}\n")

    def get_exit_code(self) -> int:
        """적절한 exit code를 반환합니다."""
        return 1 if self.issues else 0


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run --with nbconvert validate_notebook.py <notebook.ipynb>")
        print("\nValidates a Jupyter notebook against Anthropic Cookbook standards.")
        print("Returns exit code 1 if critical issues found, 0 otherwise.")
        print("\nRequires: uv (https://github.com/astral-sh/uv)")
        sys.exit(1)

    notebook_path = sys.argv[1]

    try:
        validator = NotebookValidator(notebook_path)

        # 검토하기 쉽도록 Markdown으로 변환
        print("Converting notebook to markdown for review...")
        validator.convert_to_markdown()

        # 검증 검사 실행
        validator.run_all_checks()
        validator.print_report()
        sys.exit(validator.get_exit_code())

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: {notebook_path} is not a valid JSON file")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
