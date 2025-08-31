# DocMind プロジェクト管理用Makefile

.PHONY: help install test test-unit test-integration test-performance test-gui clean lint format

# デフォルトターゲット
help:
	@echo "DocMind プロジェクト管理コマンド"
	@echo "================================"
	@echo "install          - 依存関係のインストール"
	@echo "test             - 全テスト実行"
	@echo "test-unit        - ユニットテスト実行"
	@echo "test-integration - 統合テスト実行"
	@echo "test-performance - パフォーマンステスト実行"
	@echo "test-gui         - GUIテスト実行"
	@echo "lint             - コード品質チェック"
	@echo "format           - コード自動整形"
	@echo "clean            - 一時ファイル削除"

# 仮想環境の確認
check-venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "❌ 仮想環境がアクティベートされていません"; \
		echo "以下のコマンドで仮想環境をアクティベートしてください:"; \
		echo "source venv/bin/activate"; \
		exit 1; \
	fi

# 依存関係のインストール
install: check-venv
	@echo "📦 依存関係をインストール中..."
	pip install --upgrade pip
	pip install -e ."[build,dev]"
	pip install pytest-qt pytest-benchmark pytest-cov ruff black isort

# 全テスト実行
test: check-venv
	@echo "🧪 全テスト実行中..."
	python scripts/run_tests.py

# ユニットテスト実行
test-unit: check-venv
	@echo "🔬 ユニットテスト実行中..."
	python scripts/run_tests.py unit

# 統合テスト実行
test-integration: check-venv
	@echo "🔗 統合テスト実行中..."
	python scripts/run_tests.py integration

# パフォーマンステスト実行
test-performance: check-venv
	@echo "⚡ パフォーマンステスト実行中..."
	python scripts/run_tests.py performance

# GUIテスト実行
test-gui: check-venv
	@echo "🖥️ GUIテスト実行中..."
	python scripts/run_tests.py gui

# コード品質チェック
lint: check-venv
	@echo "🔍 コード品質チェック中..."
	ruff check src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

# コード自動整形
format: check-venv
	@echo "✨ コード自動整形中..."
	black src/ tests/
	isort src/ tests/
	ruff check --fix src/ tests/

# 一時ファイル削除
clean:
	@echo "🧹 一時ファイル削除中..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	@echo "✅ クリーンアップ完了"

# 開発環境セットアップ
setup: check-venv install
	@echo "🚀 開発環境セットアップ完了"
	@echo "以下のコマンドでテストを実行できます:"
	@echo "make test"
