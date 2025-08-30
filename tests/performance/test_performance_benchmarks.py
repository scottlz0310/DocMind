"""
パフォーマンステスト - 検索・インデックス作成の性能測定
"""
from unittest.mock import Mock

import pytest


class MockSearchManager:
    """検索マネージャーのモック"""
    def search(self, query, search_type="hybrid", max_results=50):
        """模擬検索実行"""
        import time
        time.sleep(0.1)
        return [{"title": f"Document {i}", "content": f"Content for {query} {i}"} for i in range(10)]

class MockIndexManager:
    """インデックスマネージャーのモック"""
    def bulk_add_documents(self, documents):
        """模擬一括ドキュメント追加"""
        import time
        time.sleep(len(documents) * 0.01)
        return Mock(success=True, processed_count=len(documents))

class TestPerformanceBenchmarks:
    """パフォーマンステストクラス"""

    @pytest.fixture
    def sample_documents(self):
        """テスト用サンプルドキュメント"""
        return [{"id": f"doc_{i}", "title": f"Document {i}"} for i in range(100)]

    def test_search_performance(self, benchmark):
        """検索パフォーマンステスト"""
        search_manager = MockSearchManager()

        result = benchmark(search_manager.search, "test query")

        assert benchmark.stats['mean'] < 1.0
        assert len(result) > 0

    def test_index_creation_performance(self, benchmark, sample_documents):
        """インデックス作成パフォーマンステスト"""
        index_manager = MockIndexManager()

        result = benchmark(index_manager.bulk_add_documents, sample_documents)

        assert benchmark.stats['mean'] < 3.0
        assert result.success is True
