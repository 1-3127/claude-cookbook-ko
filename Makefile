.PHONY: help format lint check fix test clean install sort-authors \
        test-notebooks test-notebooks-exec test-notebooks-tox test-notebooks-quick

# 기본 target
help:
	@echo "Available targets:"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make format              - Format code with ruff"
	@echo "    make lint                - Run ruff linting checks"
	@echo "    make check               - Run all checks (format check + lint)"
	@echo "    make fix                 - Auto-fix issues with ruff"
	@echo ""
	@echo "  Testing:"
	@echo "    make test                - Run all pytest tests"
	@echo "    make test-notebooks      - Run notebook structure tests (fast)"
	@echo "    make test-notebooks-exec - Run notebook execution tests (slow, needs API key)"
	@echo "    make test-notebooks-tox  - Run notebook tests in isolated tox environment"
	@echo "    make test-notebooks-quick- Quick validation of all notebooks"
	@echo ""
	@echo "  Setup:"
	@echo "    make install             - Install dependencies"
	@echo "    make clean               - Remove cache files"
	@echo "    make sort-authors        - Sort authors.yaml alphabetically"
	@echo ""
	@echo "  Notebook test options (via environment variables):"
	@echo "    NOTEBOOK=path/to/notebook.ipynb  - Test specific notebook"
	@echo "    NOTEBOOK_DIR=capabilities        - Test notebooks in directory"
	@echo ""
	@echo "  Examples:"
	@echo "    make test-notebooks NOTEBOOK=tool_use/calculator_tool.ipynb"
	@echo "    make test-notebooks-tox NOTEBOOK_DIR=capabilities"

# Ruff로 코드 포맷팅
format:
	@echo "Formatting code with ruff..."
	uv run ruff format .

# 변경하지 않고 코드가 포맷팅되어 있는지 확인
format-check:
	@echo "Checking code formatting with ruff..."
	uv run ruff format --check .

# Ruff lint 실행
lint:
	@echo "Running ruff linting..."
	uv run ruff check .

# 모든 검사 실행
check: format-check lint
	@echo "All checks completed!"

# Ruff로 문제 자동 수정
fix:
	@echo "Auto-fixing issues with ruff..."
	uv run ruff check --fix .
	uv run ruff format .

# 테스트 실행
test:
	@echo "Running tests..."
	uv run pytest

# Dependency 설치
install:
	@echo "Installing dependencies..."
	uv sync --all-extras

# Cache 파일 정리
clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cache cleaned!"

# authors.yaml을 알파벳순으로 정렬
sort-authors:
	@echo "Sorting authors.yaml..."
	uv run python scripts/validate_authors_sorted.py --fix

# Notebook 테스트 target
# ========================

# Notebook 구조 테스트 실행(빠름, API 호출 없음)
test-notebooks:
	@echo "Running notebook structure tests..."
ifdef NOTEBOOK
	uv run pytest tests/notebook_tests/test_notebooks.py -v --tb=short -rf --notebook $(NOTEBOOK)
else ifdef NOTEBOOK_DIR
	uv run pytest tests/notebook_tests/test_notebooks.py -v --tb=short -rf --notebook-dir $(NOTEBOOK_DIR)
else
	uv run pytest tests/notebook_tests/test_notebooks.py -v --tb=short -rf -m "not slow"
endif

# Notebook 실행 테스트 수행(느림, API key 필요)
test-notebooks-exec:
	@echo "Running notebook execution tests (this may take a while)..."
ifdef NOTEBOOK
	uv run pytest tests/notebook_tests/test_notebooks.py -v --tb=long --execute-notebooks --notebook $(NOTEBOOK)
else ifdef NOTEBOOK_DIR
	uv run pytest tests/notebook_tests/test_notebooks.py -v --tb=long --execute-notebooks --notebook-dir $(NOTEBOOK_DIR)
else
	uv run pytest tests/notebook_tests/test_notebooks.py -v --tb=long --execute-notebooks
endif

# 격리된 tox 환경에서 Notebook 테스트 실행
test-notebooks-tox:
	@echo "Running notebook tests in tox environment..."
ifdef NOTEBOOK
	uv run tox -e structure-single -- $(NOTEBOOK)
else ifdef NOTEBOOK_DIR
	uv run tox -e structure -- --notebook-dir $(NOTEBOOK_DIR)
else
	uv run tox -e structure
endif

# Pytest 없이 모든 Notebook 빠른 검증
test-notebooks-quick:
	@echo "Running quick notebook validation..."
ifdef NOTEBOOK
	uv run python scripts/test_notebooks.py --quick --notebook $(NOTEBOOK)
else ifdef NOTEBOOK_DIR
	uv run python scripts/test_notebooks.py --quick --dir $(NOTEBOOK_DIR)
else
	uv run python scripts/test_notebooks.py --list
endif
