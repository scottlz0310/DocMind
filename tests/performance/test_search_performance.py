"""
検索パフォーマンステスト

大規模データでの検索性能検証
"""

import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.index_manager import IndexManager
from src.data.models import Document, FileType


@pytest.mark.skip(reason="パフォーマンステストは時間がかかるためスキップ")
class TestSearchPerformance:
    """検索パフォーマンステスト"""

    @pytest.fixture
    def temp_dir(self):
        """テスト用一時ディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def large_index(self, temp_dir):
        """大規模インデックス"""
        index_path = temp_dir / "large_index"
        manager = IndexManager(str(index_path))

        # 10,000ドキュメントのインデックス作成
        with patch("src.data.models.Document._validate_fields"):
            for i in range(10000):
                doc = Document(
                    id=f"doc_{i}",
                    file_path=f"/test/sample_{i}.txt",
                    title=f"テストドキュメント{i}",
                    content=f"テストコンテンツ{i} 検索対象テキスト",
                    file_type=FileType.TEXT,
                    size=100,
                    created_date=datetime.now(),
                    modified_date=datetime.now(),
                    indexed_date=datetime.now(),
                    content_hash=f"hash_{i}",
                )
                manager.add_document(doc)

        return manager

    def test_large_index_search_speed(self, benchmark, large_index):
        """大規模インデックス検索速度テスト"""

        def search_operation():
            return large_index.search_text("テストクエリ", limit=100)

        result = benchmark(search_operation)

        # 5秒以内での検索完了を確認
        assert benchmark.stats["mean"] < 5.0
        assert len(result) > 0

    def test_concurrent_search_performance(self, large_index):
        """並行検索パフォーマンステスト"""
        queries = ["クエリ1", "クエリ2", "クエリ3", "クエリ4", "クエリ5"]

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(large_index.search_text, query) for query in queries
            ]
            results = [future.result() for future in futures]

        end_time = time.time()

        # 並行実行でも10秒以内
        assert (end_time - start_time) < 10.0
        assert all(len(result) >= 0 for result in results)

    def test_search_memory_usage(self, large_index):
        """検索メモリ使用量テスト"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 200回検索実行
        for i in range(200):
            large_index.search_text(f"テスト{i}")

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # メモリ増加量が300MB以下
        assert memory_increase < 300 * 1024 * 1024

    def test_index_creation_performance(self, temp_dir, benchmark):
        """インデックス作成パフォーマンステスト"""
        index_path = temp_dir / "perf_index"

        def create_index():
            manager = IndexManager(str(index_path))

            with patch("src.data.models.Document._validate_fields"):
                for i in range(1000):
                    doc = Document(
                        id=f"perf_doc_{i}",
                        file_path=f"/test/perf_{i}.txt",
                        title=f"パフォーマンステスト{i}",
                        content=f"パフォーマンステストコンテンツ{i}",
                        file_type=FileType.TEXT,
                        size=100,
                        created_date=datetime.now(),
                        modified_date=datetime.now(),
                        indexed_date=datetime.now(),
                        content_hash=f"perf_hash_{i}",
                    )
                    manager.add_document(doc)

            return manager

        result = benchmark(create_index)

        # 1000ドキュメントのインデックス作成が60秒以内
        assert benchmark.stats["mean"] < 60.0
        assert result.get_document_count() == 1000

    def test_search_result_ranking_performance(self, large_index, benchmark):
        """検索結果ランキングパフォーマンステスト"""

        def ranking_operation():
            results = large_index.search_text("テスト", limit=1000)
            # ランキング確認
            scores = [result.score for result in results]
            return scores

        scores = benchmark(ranking_operation)

        # ランキング処理が2秒以内
        assert benchmark.stats["mean"] < 2.0

        # スコア順序確認
        if len(scores) > 1:
            assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    def test_batch_indexing_performance(self, temp_dir):
        """バッチインデックスパフォーマンステスト"""
        index_path = temp_dir / "batch_index"
        manager = IndexManager(str(index_path))

        # 5000ドキュメントのバッチ処理
        documents = []
        with patch("src.data.models.Document._validate_fields"):
            for i in range(5000):
                doc = Document(
                    id=f"batch_doc_{i}",
                    file_path=f"/test/batch_{i}.txt",
                    title=f"バッチテスト{i}",
                    content=f"バッチテストコンテンツ{i}",
                    file_type=FileType.TEXT,
                    size=100,
                    created_date=datetime.now(),
                    modified_date=datetime.now(),
                    indexed_date=datetime.now(),
                    content_hash=f"batch_hash_{i}",
                )
                documents.append(doc)

        start_time = time.time()
        manager.rebuild_index(documents)
        end_time = time.time()

        # バッチ処理が120秒以内
        assert (end_time - start_time) < 120.0
        assert manager.get_document_count() == 5000
