#!/usr/bin/env python3
"""
Notebook 테스트용 CLI runner입니다.

사용법:
    # 모든 구조 테스트 실행(빠름, API 호출 없음)
    python scripts/test_notebooks.py

    # 특정 Notebook 테스트 실행
    python scripts/test_notebooks.py --notebook tool_use/calculator_tool.ipynb

    # 디렉터리 테스트 실행
    python scripts/test_notebooks.py --dir capabilities

    # Notebook 실행을 포함하여 실행(느림, API key 필요)
    python scripts/test_notebooks.py --execute

    # 격리된 환경을 위해 tox로 실행
    python scripts/test_notebooks.py --tox

    # 사용 가능한 모든 Notebook 나열
    python scripts/test_notebooks.py --list
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Path에 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

from tests.notebook_tests.utils import find_all_notebooks, validate_notebook_structure  # noqa: E402

console = Console()


def list_notebooks(directory: str | None = None) -> None:
    """프로젝트의 모든 Notebook을 나열합니다."""
    root = PROJECT_ROOT
    if directory:
        root = PROJECT_ROOT / directory

    notebooks = find_all_notebooks(root)

    table = Table(
        title=f"Notebooks in {root.relative_to(PROJECT_ROOT) if directory else 'project'}"
    )
    table.add_column("Path", style="cyan")
    table.add_column("Cells", justify="right")
    table.add_column("Code Cells", justify="right")

    for nb_path in notebooks:
        try:
            result = validate_notebook_structure(nb_path)
            total_cells = len(result.cells)
            code_cells = len([c for c in result.cells if c.cell_type == "code"])
            rel_path = nb_path.relative_to(PROJECT_ROOT)
            table.add_row(str(rel_path), str(total_cells), str(code_cells))
        except Exception as e:
            rel_path = nb_path.relative_to(PROJECT_ROOT)
            table.add_row(str(rel_path), "Error", str(e))

    console.print(table)
    console.print(f"\nTotal: {len(notebooks)} notebooks")


def run_quick_validation(notebook_path: Path) -> bool:
    """단일 Notebook에 빠른 검증을 실행합니다."""
    console.print(f"\n[bold]Validating:[/bold] {notebook_path.relative_to(PROJECT_ROOT)}")

    result = validate_notebook_structure(notebook_path)

    if result.errors:
        console.print("[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  [red]- {error}[/red]")

    if result.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  [yellow]- {warning}[/yellow]")

    if result.is_valid:
        console.print("[green]Passed[/green]")
    else:
        console.print("[red]Failed[/red]")

    return result.is_valid


def run_pytest(args: list[str]) -> int:
    """주어진 인수로 pytest를 실행합니다."""
    cmd = [sys.executable, "-m", "pytest", "tests/notebook_tests/test_notebooks.py"] + args
    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")
    return subprocess.call(cmd, cwd=PROJECT_ROOT)  # noqa: S603


def run_tox(env: str, extra_args: list[str]) -> int:
    """지정된 환경으로 tox를 실행합니다."""
    cmd = ["tox", "-e", env] + extra_args
    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")
    return subprocess.call(cmd, cwd=PROJECT_ROOT)  # noqa: S603


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run notebook tests for Anthropic Cookbook",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--notebook",
        "-n",
        help="Test a specific notebook (relative path)",
    )
    parser.add_argument(
        "--dir",
        "-d",
        help="Test all notebooks in a directory",
    )
    parser.add_argument(
        "--execute",
        "-x",
        action="store_true",
        help="Actually execute notebooks (slow, requires API key)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for notebook execution (default: 300)",
    )
    parser.add_argument(
        "--tox",
        "-t",
        action="store_true",
        help="Run tests in isolated tox environment",
    )
    parser.add_argument(
        "--tox-env",
        default="structure",
        help="Tox environment to use (default: structure)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all notebooks",
    )
    parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Run quick validation without pytest",
    )
    parser.add_argument(
        "--registry-only",
        action="store_true",
        help="Only test notebooks listed in registry.yaml",
    )
    parser.add_argument(
        "--skip-third-party",
        action="store_true",
        help="Skip third-party integration notebooks",
    )
    parser.add_argument(
        "extra_args",
        nargs="*",
        help="Additional arguments to pass to pytest/tox",
    )

    args = parser.parse_args()

    # --list 처리
    if args.list:
        list_notebooks(args.dir)
        return 0

    # 단일 Notebook 검증을 위한 --quick 처리
    if args.quick:
        if args.notebook:
            nb_path = PROJECT_ROOT / args.notebook
            return 0 if run_quick_validation(nb_path) else 1
        elif args.dir:
            notebooks = find_all_notebooks(PROJECT_ROOT / args.dir)
            failed = 0
            for nb_path in notebooks:
                if not run_quick_validation(nb_path):
                    failed += 1
            console.print(
                f"\n[bold]Results:[/bold] {len(notebooks) - failed}/{len(notebooks)} passed"
            )
            return 1 if failed else 0
        else:
            console.print("[red]Error: --quick requires --notebook or --dir[/red]")
            return 1

    # Pytest 인수 구성
    pytest_args = list(args.extra_args)

    if args.notebook:
        pytest_args.extend(["--notebook", args.notebook])

    if args.dir:
        pytest_args.extend(["--notebook-dir", args.dir])

    if args.execute:
        pytest_args.append("--execute-notebooks")
        pytest_args.extend(["--notebook-timeout", str(args.timeout)])

    if args.registry_only:
        pytest_args.append("--registry-only")

    if args.skip_third_party:
        pytest_args.append("--skip-third-party")

    # Tox로 또는 직접 실행
    if args.tox:
        tox_env = args.tox_env
        if args.execute:
            tox_env = "execution"
        if args.notebook:
            tox_env = f"{tox_env}-single"

        # Tox에 추가 인수 전달
        tox_extra = []
        if pytest_args:
            tox_extra = ["--"] + pytest_args

        return run_tox(tox_env, tox_extra)
    else:
        return run_pytest(pytest_args)


if __name__ == "__main__":
    sys.exit(main())
