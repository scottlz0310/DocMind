# DocMind Phase5 テスト環境 Makefile

.PHONY: help test test-unit test-integration test-fast test-slow test-coverage clean-test

help: ## ヘルプ表示
	@echo "Phase5 テスト環境コマンド:"
	@echo ""
	@echo "基本テスト実行:"
	@echo "  test-unit        ユニットテスト実行（品質保証の主力）"
	@echo "  test-integration 統合テスト実行（接続確認のみ）"
	@echo "  test-fast        高速テスト実行（1秒以内）"
	@echo "  test-slow        低速テスト実行（1秒以上）"
	@echo ""
	@echo "カバレッジ測定:"
	@echo "  test-coverage    カバレッジ付きテスト実行"
	@echo "  coverage-report  カバレッジレポート表示"
	@echo ""
	@echo "環境管理:"
	@echo "  clean-test       テスト環境クリーンアップ"
	@echo "  setup-test       テスト環境セットアップ"

# Phase5 テストピラミッド構造実行
test-unit: ## ユニットテスト実行（8,000行目標）
	pytest tests/unit/ -m "unit and fast" -v

test-integration: ## 統合テスト実行（2,000行目標）
	pytest tests/integration/ -m "integration" -v --tb=short

test-fast: ## 高速テスト実行（5分以内目標）
	pytest -m "fast" -v --durations=10

test-slow: ## 低速テスト実行（必要時のみ）
	pytest -m "slow" -v --tb=line

# カバレッジ測定（Phase5目標: ユニット85%、統合100%、全体80%）
test-coverage: ## カバレッジ付きテスト実行
	pytest --cov=src --cov-report=html --cov-report=term-missing tests/

coverage-report: ## カバレッジレポート表示
	@echo "カバレッジレポートをブラウザで開きます..."
	@python -c "import webbrowser; webbrowser.open('htmlcov/index.html')"

# 環境管理
setup-test: ## テスト環境セットアップ
	pip install -e ".[dev]"
	@echo "Phase5テスト環境セットアップ完了"

clean-test: ## テスト環境クリーンアップ
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	@echo "テスト環境クリーンアップ完了"

# 全体テスト実行（Phase5完了後の検証用）
test: test-fast ## デフォルトテスト実行（高速テストのみ）

test-all: ## 全テスト実行（Phase5完了後）
	pytest tests/ -v --tb=short --maxfail=5