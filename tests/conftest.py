"""Notebook 테스트용 Pytest 설정과 fixture입니다."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.notebook_tests.utils import (
    find_all_notebooks,
    load_notebook,
    parse_notebook_cells,
    validate_notebook_structure,
)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Notebook 테스트를 위한 custom 명령줄 option을 추가합니다."""
    parser.addoption(
        "--notebook",
        action="store",
        default=None,
        help="Run tests for a specific notebook path",
    )
    parser.addoption(
        "--notebook-dir",
        action="store",
        default=None,
        help="Run tests for all notebooks in a directory",
    )
    parser.addoption(
        "--execute-notebooks",
        action="store_true",
        default=False,
        help="Actually execute notebooks (requires API keys, slower)",
    )
    parser.addoption(
        "--notebook-timeout",
        action="store",
        default=300,
        type=int,
        help="Timeout in seconds for notebook execution (default: 300)",
    )
    parser.addoption(
        "--skip-third-party",
        action="store_true",
        default=False,
        help="Skip notebooks in third_party directory",
    )
    parser.addoption(
        "--registry-only",
        action="store_true",
        default=False,
        help="Only test notebooks listed in registry.yaml",
    )


def get_project_root() -> Path:
    """프로젝트 루트 디렉터리를 가져옵니다."""
    return Path(__file__).parent.parent


def load_registry() -> list[dict[str, Any]]:
    """Notebook registry를 불러옵니다."""
    registry_path = get_project_root() / "registry.yaml"
    if not registry_path.exists():
        return []

    with open(registry_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("notebooks", []) if data else []


def get_notebooks_to_test(config: pytest.Config) -> list[Path]:
    """Config option을 기준으로 테스트할 Notebook을 결정합니다."""
    root = get_project_root()
    notebooks = []

    # 특정 Notebook
    if config.getoption("--notebook"):
        nb_path = Path(config.getoption("--notebook"))
        if not nb_path.is_absolute():
            nb_path = root / nb_path
        if nb_path.exists():
            return [nb_path]
        return []

    # 특정 디렉터리
    if config.getoption("--notebook-dir"):
        nb_dir = Path(config.getoption("--notebook-dir"))
        if not nb_dir.is_absolute():
            nb_dir = root / nb_dir
        return find_all_notebooks(nb_dir)

    # Registry만
    if config.getoption("--registry-only"):
        registry = load_registry()
        for entry in registry:
            nb_path = root / entry.get("path", "")
            if nb_path.exists():
                notebooks.append(nb_path)
        return notebooks

    # 모든 Notebook
    exclude_patterns = [".ipynb_checkpoints/*"]
    if config.getoption("--skip-third-party"):
        exclude_patterns.append("third_party/*")

    return find_all_notebooks(root, exclude_patterns)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Notebook에 대한 parameterized test를 생성합니다."""
    if "notebook_path" in metafunc.fixturenames:
        notebooks = get_notebooks_to_test(metafunc.config)
        if notebooks:
            # 깔끔한 테스트 이름을 위해 상대 경로 사용
            root = get_project_root()
            ids = [str(nb.relative_to(root)) for nb in notebooks]
            metafunc.parametrize("notebook_path", notebooks, ids=ids)


@pytest.fixture
def project_root() -> Path:
    """프로젝트 루트 디렉터리를 제공하는 fixture입니다."""
    return get_project_root()


@pytest.fixture
def notebook_data(notebook_path: Path) -> dict[str, Any]:
    """불러온 Notebook 데이터를 제공하는 fixture입니다."""
    return load_notebook(notebook_path)


@pytest.fixture
def notebook_cells(notebook_data: dict[str, Any]) -> list:
    """파싱된 Notebook 셀을 제공하는 fixture입니다."""
    return parse_notebook_cells(notebook_data)


@pytest.fixture
def validation_result(notebook_path: Path):
    """Notebook 검증 결과를 제공하는 fixture입니다."""
    return validate_notebook_structure(notebook_path)


@pytest.fixture
def execute_notebooks(request: pytest.FixtureRequest) -> bool:
    """Notebook 실행 여부를 나타내는 fixture입니다."""
    return request.config.getoption("--execute-notebooks")


@pytest.fixture
def notebook_timeout(request: pytest.FixtureRequest) -> int:
    """Notebook 실행 timeout을 제공하는 fixture입니다."""
    return request.config.getoption("--notebook-timeout")


@pytest.fixture
def has_api_key() -> bool:
    """Anthropic API key 사용 가능 여부를 나타내는 fixture입니다."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


@pytest.fixture
def registry() -> list[dict[str, Any]]:
    """Notebook registry를 제공하는 fixture입니다."""
    return load_registry()
