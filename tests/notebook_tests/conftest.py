"""Notebook별 테스트 보고를 위한 Pytest hook입니다."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.reports import TestReport
    from _pytest.terminal import TerminalReporter


# Notebook별로 묶어 실패 저장
_notebook_failures: dict[str, set[str]] = defaultdict(set)

# 사람이 읽기 쉬운 테스트 category 이름
_ISSUE_NAMES = {
    "all_cells_executed": "unexecuted cells",
    "cells_executed_in_order": "out-of-order execution",
    "execution_counts_start_from_one": "stale kernel",
    "no_error_outputs": "error outputs",
    "no_hardcoded_api_keys": "hardcoded API key",
    "api_key_from_environment": "API key not from env",
    "python_kernel": "non-Python kernel",
    "valid_json": "invalid JSON",
    "has_cells": "no cells",
    "has_code_cells": "no code cells",
    "no_deprecated_models": "deprecated model",
}


def _extract_notebook_path(nodeid: str) -> str | None:
    """테스트 node ID에서 Notebook 경로를 추출합니다."""
    match = re.search(r"\[([^\]]+\.ipynb)\]", nodeid)
    return match.group(1) if match else None


def _extract_test_name(nodeid: str) -> str:
    """테스트 node ID에서 테스트 함수 이름을 추출합니다."""
    match = re.search(r"::test_(\w+)\[", nodeid)
    return match.group(1) if match else "unknown"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """Notebook별로 묶어 실패를 수집합니다."""
    outcome = yield
    report: TestReport = outcome.get_result()

    if report.when == "call" and report.failed:
        notebook = _extract_notebook_path(item.nodeid)
        if notebook:
            test_name = _extract_test_name(item.nodeid)
            issue = _ISSUE_NAMES.get(test_name, test_name.replace("_", " "))
            _notebook_failures[notebook].add(issue)


def pytest_terminal_summary(
    terminalreporter: TerminalReporter, exitstatus: int, config: Config
) -> None:
    """Notebook별로 묶인 실패 요약을 출력합니다."""
    if not _notebook_failures:
        return

    tr = terminalreporter
    tr.write_sep("=", "NOTEBOOK FAILURE SUMMARY", bold=True, yellow=True)
    tr.write("\n")

    # 합계 집계
    total_notebooks = len(_notebook_failures)
    total_issues = sum(len(issues) for issues in _notebook_failures.values())

    tr.write(
        f"Found issues in {total_notebooks} notebook(s) ({total_issues} total issue types)\n\n"
    )

    # 빠른 개요를 위해 문제 유형별로 묶기
    issue_counts: dict[str, list[str]] = defaultdict(list)
    for notebook, issues in _notebook_failures.items():
        for issue in issues:
            issue_counts[issue].append(notebook)

    tr.write("Issue breakdown:\n", bold=True)
    for issue, notebooks in sorted(issue_counts.items(), key=lambda x: -len(x[1])):
        tr.write(f"  {issue}: {len(notebooks)} notebook(s)\n")
    tr.write("\n")

    # 깔끔한 출력을 위해 디렉터리별로 Notebook 묶기
    by_directory: dict[str, list[tuple[str, set[str]]]] = defaultdict(list)
    for notebook in sorted(_notebook_failures.keys()):
        parts = notebook.split("/")
        if len(parts) > 1:
            directory = parts[0]
            filename = "/".join(parts[1:])
        else:
            directory = "."
            filename = notebook
        by_directory[directory].append((filename, _notebook_failures[notebook]))

    tr.write("By notebook:\n", bold=True)
    for directory in sorted(by_directory.keys()):
        tr.write(f"\n  {directory}/\n", bold=True)
        for filename, issues in by_directory[directory]:
            issue_list = ", ".join(sorted(issues))
            tr.write(f"    {filename}\n")
            tr.write(f"      -> {issue_list}\n", red=True)

    tr.write("\n")
    _notebook_failures.clear()


def pytest_configure(config: Config) -> None:
    """테스트 실행 시작 시 실패 추적을 초기화합니다."""
    _notebook_failures.clear()
