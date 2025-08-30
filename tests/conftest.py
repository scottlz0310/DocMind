"""
Phase5 テスト環境 - pytest設定

新しいテストアーキテクチャ用の基本設定
- ユニットテスト: 各コンポーネントの独立テスト
- 統合テスト: コンポーネント間の接続確認のみ
"""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_main_window():
    """メインウィンドウのモック"""
    return Mock()


@pytest.fixture
def mock_index_manager():
    """インデックスマネージャーのモック"""
    return Mock()


@pytest.fixture
def mock_search_manager():
    """検索マネージャーのモック"""
    return Mock()


@pytest.fixture
def minimal_test_data():
    """最小限のテストデータ"""
    return {
        "documents": ["test1.txt", "test2.pdf"],
        "queries": ["basic query", "advanced query"],
        "expected_results": []
    }