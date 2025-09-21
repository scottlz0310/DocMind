# DocMind Makefile - uv最適化版

.PHONY: help install test lint format type-check security clean build ci dev sync

# デフォルトターゲット
help:
	@echo "DocMind Development Commands (uv-optimized)"
	@echo ""
	@echo "Setup:"
	@echo "  sync        Sync dependencies with uv"
	@echo "  install     Install project in development mode"
	@echo "  dev         Install with dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test        Run all tests"
	@echo "  test-unit   Run unit tests only"
	@echo "  test-int    Run integration tests only"
	@echo "  test-cov    Run tests with coverage report"
	@echo "  test-fast   Run tests with fail-fast"
	@echo ""
	@echo "Code Quality:"
	@echo "  format      Format code with ruff"
	@echo "  lint        Lint code with ruff"
	@echo "  type-check  Type check with mypy"
	@echo "  security    Run security checks"
	@echo ""
	@echo "Workflows:"
	@echo "  check       Run all quality checks"
	@echo "  fix         Auto-fix code issues"
	@echo "  ci          Run full CI pipeline"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  build       Build package"
	@echo "  clean       Clean build artifacts"
	@echo "  reset       Reset environment"
	@echo ""
	@echo "Development Tools:"
	@echo "  test-tools    Run comprehensive test suite"
	@echo "  test-coverage Measure and report test coverage"

# セットアップ
sync:
	uv sync

install: sync
	uv pip install -e .

dev:
	uv sync --extra dev --extra security

# テスト
test:
	uv run pytest

test-unit:
	uv run pytest tests/unit -v

test-int:
	uv run pytest tests/integration -v

test-cov:
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html

test-fast:
	uv run pytest -x --ff --tb=short

# コード品質
format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check --fix .

type-check:
	uv run mypy src tests

# セキュリティ
security:
	uv run bandit -r src/
	uv run safety check

# ワークフロー
check: format-check lint type-check

fix: format lint-fix

ci: check security test-cov

# ビルド・クリーンアップ
build:
	uv build

clean:
	rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# 環境管理
reset: clean
	rm -rf .venv/
	uv sync --extra dev

# 開発用ショートカット
run:
	uv run python main.py

debug:
	uv run python -m pdb main.py

# パッケージ管理
add:
	@echo "Usage: make add PACKAGE=package_name"
	@if [ -n "$(PACKAGE)" ]; then uv add $(PACKAGE); fi

add-dev:
	@echo "Usage: make add-dev PACKAGE=package_name"
	@if [ -n "$(PACKAGE)" ]; then uv add --dev $(PACKAGE); fi

remove:
	@echo "Usage: make remove PACKAGE=package_name"
	@if [ -n "$(PACKAGE)" ]; then uv remove $(PACKAGE); fi

# 情報表示
info:
	@echo "=== uv Environment Info ==="
	uv --version
	uv python list
	@echo ""
	@echo "=== Project Info ==="
	uv tree --depth 1
	@echo ""
	@echo "=== Virtual Environment ==="
	uv venv --help | head -5

# 開発ツール
test-tools:
	uv run python scripts/tools/run_tests.py

test-coverage:
	uv run python scripts/tools/measure_test_coverage.py

# プロジェクト初期化（新規開発者向け）
bootstrap: dev
	@echo "=== DocMind Development Environment Setup Complete ==="
	@echo "Next steps:"
	@echo "  1. Run 'make test' to verify setup"
	@echo "  2. Run 'make run' to start the application"
	@echo "  3. See 'make help' for available commands"