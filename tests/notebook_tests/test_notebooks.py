"""
Anthropic Cookbook용 Notebook 테스트 scaffold입니다.

이 module은 Jupyter Notebook에 대해 다음을 포함한 종합적인 테스트를 제공합니다.
- 구조 검증(유효한 JSON, 적절한 Notebook 형식)
- 셀 실행 순서 검증
- 모든 셀 실행 여부 검증
- 오류 출력 감지
- 보안 검사(hardcoded API key 없음)
- Dependency 감지
- 선택 사항: 격리된 환경에서 전체 Notebook 실행
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.notebook_tests.utils import (
    CellInfo,
    execute_notebook,
    extract_pip_dependencies,
    get_notebook_kernel_info,
    validate_all_cells_executed,
    validate_cell_execution_order,
    validate_no_error_outputs,
    validate_no_hardcoded_secrets,
)


class TestNotebookStructure:
    """Notebook 구조와 형식 유효성 테스트입니다."""

    def test_valid_json(self, notebook_path: Path) -> None:
        """Notebook이 유효한 JSON인지 테스트합니다."""
        try:
            with open(notebook_path, encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {notebook_path}: {e}")

    def test_has_cells(self, notebook_data: dict[str, Any]) -> None:
        """Notebook에 셀이 하나 이상 있는지 테스트합니다."""
        cells = notebook_data.get("cells", [])
        assert len(cells) > 0, "Notebook has no cells"

    def test_has_code_cells(self, notebook_data: dict[str, Any]) -> None:
        """Notebook에 코드 셀이 하나 이상 있는지 테스트합니다."""
        cells = notebook_data.get("cells", [])
        code_cells = [c for c in cells if c.get("cell_type") == "code"]
        assert len(code_cells) > 0, "Notebook has no code cells"

    def test_valid_cell_types(self, notebook_data: dict[str, Any]) -> None:
        """모든 셀이 유효한 cell type을 가지는지 테스트합니다."""
        valid_types = {"code", "markdown", "raw"}
        cells = notebook_data.get("cells", [])

        for i, cell in enumerate(cells):
            cell_type = cell.get("cell_type")
            assert cell_type in valid_types, f"Cell {i} has invalid type: {cell_type}"

    def test_has_kernel_spec(self, notebook_data: dict[str, Any]) -> None:
        """Notebook에 kernel specification이 있는지 테스트합니다."""
        metadata = notebook_data.get("metadata", {})
        kernelspec = metadata.get("kernelspec", {})

        assert kernelspec, "Notebook missing kernelspec in metadata"
        assert kernelspec.get("name"), "Kernel name not specified"

    def test_python_kernel(self, notebook_data: dict[str, Any]) -> None:
        """Notebook이 Python kernel을 사용하는지 테스트합니다."""
        kernel_info = get_notebook_kernel_info(notebook_data)
        language = kernel_info.get("language", "").lower()

        assert language == "python", f"Expected Python kernel, got: {language}"


class TestCellExecution:
    """셀 실행 상태와 순서 테스트입니다."""

    def test_all_cells_executed(self, notebook_cells: list[CellInfo]) -> None:
        """모든 코드 셀이 실행되었는지 테스트합니다."""
        issues = validate_all_cells_executed(notebook_cells)

        if issues:
            pytest.fail(
                f"Found {len(issues)} unexecuted cell(s):\n" + "\n".join(f"  - {i}" for i in issues)
            )

    def test_cells_executed_in_order(self, notebook_cells: list[CellInfo]) -> None:
        """셀이 순서대로 실행되었는지 테스트합니다."""
        issues = validate_cell_execution_order(notebook_cells)

        if issues:
            pytest.fail("Cell execution order issues:\n" + "\n".join(f"  - {i}" for i in issues))

    def test_execution_counts_start_from_one(self, notebook_cells: list[CellInfo]) -> None:
        """Execution count가 1부터 시작하는지 테스트합니다(fresh kernel)."""
        code_cells = [c for c in notebook_cells if c.cell_type == "code"]
        exec_counts = [c.execution_count for c in code_cells if c.execution_count is not None]

        if exec_counts:
            min_count = min(exec_counts)
            assert min_count == 1, (
                f"Execution counts should start from 1, but minimum is {min_count}. "
                "This suggests the notebook wasn't run from a fresh kernel."
            )


class TestCellOutputs:
    """셀 출력과 오류 테스트입니다."""

    def test_no_error_outputs(self, notebook_cells: list[CellInfo]) -> None:
        """오류 출력이 있는 셀이 없는지 테스트합니다."""
        issues = validate_no_error_outputs(notebook_cells)

        if issues:
            pytest.fail("Found error outputs:\n" + "\n".join(f"  - {i}" for i in issues))

    def test_no_empty_code_cells(self, notebook_cells: list[CellInfo]) -> None:
        """빈 코드 셀이 없는지 테스트합니다(경고만)."""
        empty_code_cells = [c for c in notebook_cells if c.cell_type == "code" and c.is_empty]

        if empty_code_cells:
            indices = [str(c.index) for c in empty_code_cells]
            pytest.skip(
                f"Found {len(empty_code_cells)} empty code cell(s) at indices: {', '.join(indices)}"
            )


class TestSecurity:
    """보안 모범 사례 테스트입니다."""

    def test_no_hardcoded_api_keys(self, notebook_cells: list[CellInfo]) -> None:
        """Hardcoded API key가 포함된 셀이 없는지 테스트합니다."""
        issues = validate_no_hardcoded_secrets(notebook_cells)

        if issues:
            pytest.fail(
                "Security issue - hardcoded API keys detected:\n"
                + "\n".join(f"  - {i}" for i in issues)
            )

    def test_api_key_from_environment(self, notebook_cells: list[CellInfo]) -> None:
        """API key를 환경 변수에서 불러오는지 테스트합니다."""
        # Notebook이 Anthropic을 사용하는지 확인
        uses_anthropic = False
        for cell in notebook_cells:
            if cell.cell_type == "code" and "anthropic" in cell.source.lower():
                uses_anthropic = True
                break

        if not uses_anthropic:
            pytest.skip("Notebook doesn't use Anthropic API")

        # Hardcoded api_key parameter 확인
        for cell in notebook_cells:
            if cell.cell_type != "code":
                continue
            source = cell.source
            # api_key="..." pattern 확인(hardcoded)
            if 'api_key="sk-' in source or "api_key='sk-" in source:
                pytest.fail(
                    f"Cell {cell.index}: Hardcoded API key in Anthropic client constructor. "
                    "Use environment variables instead."
                )


class TestDependencies:
    """Dependency 선언 테스트입니다."""

    def test_pip_installs_at_top(self, notebook_cells: list[CellInfo]) -> None:
        """Pip install 명령이 Notebook 초반에 나오는지 테스트합니다."""
        code_cells = [c for c in notebook_cells if c.cell_type == "code"]

        pip_install_indices = []
        for i, cell in enumerate(code_cells):
            if "%pip install" in cell.source or "!pip install" in cell.source:
                pip_install_indices.append(i)

        if not pip_install_indices:
            pytest.skip("No pip install commands found")

        # 모든 pip install은 처음 3개 코드 셀에 있어야 함
        for idx in pip_install_indices:
            if idx > 2:
                pytest.skip(
                    f"pip install found at code cell {idx}. "
                    "Consider moving dependency installation to the beginning of the notebook."
                )

    def test_dependencies_documented(self, notebook_cells: list[CellInfo]) -> None:
        """Dependency가 문서화되어 있는지 테스트합니다(pip install 또는 Markdown 언급)."""
        deps = extract_pip_dependencies(notebook_cells)

        if not deps:
            # Markdown에 requirements 언급이 있는지 확인
            for cell in notebook_cells:
                if cell.cell_type == "markdown":
                    if (
                        "requirements" in cell.source.lower()
                        or "dependencies" in cell.source.lower()
                    ):
                        return

            # Dependency와 언급이 없음 - 단순한 Notebook으로 보이므로 건너뛰기
            pytest.skip("No explicit dependencies found")


class TestNotebookExecution:
    """실제로 Notebook을 실행하는 테스트입니다(선택 사항, 느림)."""

    @pytest.mark.slow
    def test_notebook_executes_successfully(
        self,
        notebook_path: Path,
        execute_notebooks: bool,
        notebook_timeout: int,
        has_api_key: bool,
    ) -> None:
        """Notebook이 오류 없이 실행되는지 테스트합니다."""
        if not execute_notebooks:
            pytest.skip("Use --execute-notebooks to run execution tests")

        if not has_api_key:
            pytest.skip("ANTHROPIC_API_KEY not set, skipping execution test")

        success, message, output_path = execute_notebook(
            notebook_path,
            timeout=notebook_timeout,
            allow_errors=False,
        )

        # 출력 파일 정리
        if output_path and output_path.exists():
            output_path.unlink()

        assert success, f"Notebook execution failed: {message}"


class TestNotebookMetadata:
    """Notebook metadata 품질 테스트입니다."""

    def test_has_title(self, notebook_cells: list[CellInfo]) -> None:
        """Notebook이 제목(Markdown heading)으로 시작하는지 테스트합니다."""
        if not notebook_cells:
            pytest.skip("No cells in notebook")

        first_cell = notebook_cells[0]
        if first_cell.cell_type != "markdown":
            pytest.skip("First cell is not markdown")

        # Heading 확인
        source = first_cell.source.strip()
        if not source.startswith("#"):
            pytest.skip("First markdown cell doesn't start with a heading")

    def test_nbformat_version(self, notebook_data: dict[str, Any]) -> None:
        """Notebook이 지원되는 nbformat 버전을 사용하는지 테스트합니다."""
        nbformat = notebook_data.get("nbformat", 0)
        assert nbformat >= 4, f"Notebook uses old nbformat {nbformat}, expected 4+"


class TestModelUsage:
    """Claude model 사용 테스트입니다."""

    # 현재 지원되는 model
    CURRENT_MODELS = {
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "claude-opus-4-6",
    }

    # Claude model 식별자와 일치하는 pattern
    CLAUDE_MODEL_PATTERN = r"claude-[a-z0-9-]+-\d{8}"

    def test_no_deprecated_models(self, notebook_cells: list[CellInfo]) -> None:
        """Deprecated Claude model을 사용하지 않는지 테스트합니다."""
        import re

        issues = []

        for cell in notebook_cells:
            if cell.cell_type != "code":
                continue

            source = cell.source
            matches = re.findall(self.CLAUDE_MODEL_PATTERN, source)

            for match in matches:
                if match not in self.CURRENT_MODELS:
                    issues.append(f"Cell {cell.index}: Found deprecated model '{match}'")

        if issues:
            pytest.fail(
                "Deprecated Claude models detected:\n"
                + "\n".join(f"  - {i}" for i in issues)
                + f"\n\nPlease use one of the current models: {', '.join(sorted(self.CURRENT_MODELS))}"
            )


class TestCookbookAttribution:
    """Managed Agent의 anthropic_cookbook tag 테스트입니다."""

    # Attribution에는 이 형식에 맞는 tag만 집계됩니다. 그 외는
    # 오류 없이 무시되므로 오타가 있으면 알아차리지 못한 채 attribution을 잃습니다.
    SLUG_PATTERN = r"[a-z0-9][a-z0-9-]{0,63}"

    def test_agents_carry_cookbook_tag(
        self, notebook_path: Path, notebook_cells: list[CellInfo]
    ) -> None:
        """모든 agents.create 호출이 이 cookbook으로 agent에 tag를 지정하는지 테스트합니다."""
        import ast
        import re

        name = re.sub(r"[^a-z0-9]+", "-", notebook_path.stem.lower()).strip("-")
        expected = f"claude-cookbooks/{name}"

        calls = 0
        issues = []

        for cell in notebook_cells:
            if cell.cell_type != "code" or "agents.create" not in cell.source:
                continue

            # IPython magic과 shell escape는 Python이 아니므로 비웁니다.
            source = re.sub(r"^(\s*)[%!].*$", r"\1pass", cell.source, flags=re.MULTILINE)
            try:
                tree = ast.parse(source)
            except SyntaxError as e:
                issues.append(f"Cell {cell.index}: could not parse the cell ({e.msg})")
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not ast.unparse(node.func).endswith("agents.create"):
                    continue

                calls += 1
                where = f"Cell {cell.index}, line {node.lineno}"
                metadata = next((kw.value for kw in node.keywords if kw.arg == "metadata"), None)
                if metadata is None:
                    issues.append(f"{where}: no metadata argument")
                    continue

                try:
                    value = ast.literal_eval(metadata)
                except ValueError:
                    value = None
                if not isinstance(value, dict):
                    # 셀을 실행하지 않으면 변수나 spread를 확인할 수 없습니다.
                    issues.append(f"{where}: metadata must be a plain dict literal")
                    continue

                tag = value.get("anthropic_cookbook")
                if tag != expected:
                    issues.append(f"{where}: anthropic_cookbook is {tag!r}")

        if calls:
            assert re.fullmatch(self.SLUG_PATTERN, name), f"Notebook name makes a bad slug: {name}"

        if issues:
            pytest.fail(
                f'agents.create calls need metadata={{"anthropic_cookbook": "{expected}"}}:\n'
                + "\n".join(f"  - {i}" for i in issues)
            )
