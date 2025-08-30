"""
Phase7 IndexManagerの強化テストモジュール

コアロジック強化テストとして、IndexManagerの包括的なテストを提供します。
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.index_manager import IndexManager
from src.data.models import FileType, SearchType
from src.utils.exceptions import IndexingError, SearchError
from tests.fixtures.mock_models import MockDocument, create_mock_document, create_mock_documents


class TestIndexManagerPhase7:
    """Phase7 IndexManagerの強化テストクラス"""

    @pytest.fixture
    def temp_index_dir(self):
        """一時インデックスディレクトリを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_dir = Path(temp_dir) / "test_index"
            yield str(index_dir)

    @pytest.fixture
    def index_manager(self, temp_index_dir):
        """IndexManagerインスタンスを作成"""
        return IndexManager(temp_index_dir)

    @pytest.fixture
    def sample_document(self):
        """サンプルドキュメントを作成"""
        return create_mock_document(
            doc_id="test_doc_1",
            file_path="/test/sample.txt",
            title="テストドキュメント",
            content="これはテスト用のドキュメントです。検索機能をテストします。",
            file_type=FileType.TEXT,
            size=1024
        )

    @pytest.fixture
    def multiple_documents(self):
        """複数のサンプルドキュメントを作成"""
        return create_mock_documents(5)

    @pytest.fixture
    def large_document_set(self):
        """大規模ドキュメントセットを作成"""
        return create_mock_documents(100)

    def test_initialization(self, index_manager):
        """初期化テスト"""
        assert index_manager is not None
        assert index_manager._index is not None
        assert index_manager.index_path.exists()

    def test_add_document(self, index_manager, sample_document):
        """ドキュメント追加テスト"""
        index_manager.add_document(sample_document)
        
        assert index_manager.get_document_count() == 1
        assert index_manager.document_exists(sample_document.id)

    def test_update_document(self, index_manager, sample_document):
        """ドキュメント更新テスト"""
        # 最初にドキュメントを追加
        index_manager.add_document(sample_document)
        
        # ドキュメントを更新
        sample_document.content = "更新されたコンテンツです。"
        index_manager.update_document(sample_document)
        
        assert index_manager.get_document_count() == 1
        
        # 更新されたコンテンツで検索できることを確認
        results = index_manager.search_text("更新された")
        assert len(results) == 1

    def test_remove_document(self, index_manager, sample_document):
        """ドキュメント削除テスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        assert index_manager.get_document_count() == 1
        
        # ドキュメントを削除
        index_manager.remove_document(sample_document.id)
        assert index_manager.get_document_count() == 0
        assert not index_manager.document_exists(sample_document.id)

    def test_search_text_basic(self, index_manager, sample_document):
        """基本的なテキスト検索テスト"""
        index_manager.add_document(sample_document)
        
        results = index_manager.search_text("テスト")
        
        assert len(results) == 1
        assert results[0].document.id == sample_document.id
        assert results[0].search_type == SearchType.FULL_TEXT

    def test_search_text_multiple_results(self, index_manager, multiple_documents):
        """複数結果のテキスト検索テスト"""
        # 複数ドキュメントを追加
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        results = index_manager.search_text("テスト")
        
        assert len(results) == 5
        # スコア順でソートされていることを確認
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_large_scale_indexing(self, index_manager, large_document_set):
        """大規模インデックス作成テスト"""
        import time
        
        start_time = time.time()
        
        # バッチでドキュメントを追加
        for doc in large_document_set:
            index_manager.add_document(doc)
        
        end_time = time.time()
        
        # パフォーマンス検証
        assert (end_time - start_time) < 60  # 1分以内
        assert index_manager.get_document_count() == 100
        
        # 検索機能が正常に動作することを確認
        results = index_manager.search_text("テスト")
        assert len(results) > 0

    def test_incremental_update_performance(self, index_manager, multiple_documents):
        """増分更新パフォーマンステスト"""
        import time
        
        # 初期ドキュメントを追加
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        # 新しいドキュメントを追加
        new_documents = create_mock_documents(10)
        
        start_time = time.time()
        for doc in new_documents:
            index_manager.add_document(doc)
        end_time = time.time()
        
        # 増分更新が10秒以内に完了することを確認
        assert (end_time - start_time) < 10
        assert index_manager.get_document_count() == 15

    def test_search_with_file_type_filter(self, index_manager, multiple_documents):
        """ファイルタイプフィルター付き検索テスト"""
        # 異なるファイルタイプのドキュメントを作成
        multiple_documents[0].file_type = FileType.PDF
        multiple_documents[1].file_type = FileType.WORD
        
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        # PDFファイルのみを検索
        results = index_manager.search_text("テスト", file_types=[FileType.PDF])
        
        assert len(results) == 1
        assert results[0].document.file_type == FileType.PDF

    def test_search_with_date_range(self, index_manager, multiple_documents):
        """日付範囲フィルター付き検索テスト"""
        # 異なる日付のドキュメントを作成
        for i, doc in enumerate(multiple_documents):
            doc.modified_date = datetime(2024, 1, i + 1)
            index_manager.add_document(doc)
        
        # 特定の日付範囲で検索
        date_from = datetime(2024, 1, 2)
        date_to = datetime(2024, 1, 4)
        
        results = index_manager.search_text("テスト", date_from=date_from, date_to=date_to)
        
        # 日付範囲内のドキュメントのみが返されることを確認
        assert len(results) == 3

    def test_batch_add_documents(self, index_manager, multiple_documents):
        """バッチドキュメント追加テスト"""
        index_manager._add_documents_batch(multiple_documents)
        
        assert index_manager.get_document_count() == 5

    def test_snippet_generation(self, index_manager, sample_document):
        """スニペット生成テスト"""
        index_manager.add_document(sample_document)
        
        results = index_manager.search_text("テスト")
        
        assert len(results) == 1
        assert len(results[0].snippet) > 0
        assert isinstance(results[0].highlighted_terms, list)

    def test_get_index_stats(self, index_manager, multiple_documents):
        """インデックス統計情報取得テスト"""
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        stats = index_manager.get_index_stats()
        
        assert isinstance(stats, dict)
        assert stats["document_count"] == 5
        assert "index_size" in stats
        assert "last_modified" in stats

    def test_clear_index(self, index_manager, multiple_documents):
        """インデックスクリアテスト"""
        # 複数ドキュメントを追加
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        assert index_manager.get_document_count() == 5
        
        # インデックスをクリア
        index_manager.clear_index()
        
        assert index_manager.get_document_count() == 0

    def test_rebuild_index(self, index_manager, multiple_documents):
        """インデックス再構築テスト"""
        index_manager.rebuild_index(multiple_documents)
        
        assert index_manager.get_document_count() == 5
        
        # 検索が正常に動作することを確認
        results = index_manager.search_text("テスト")
        assert len(results) == 5

    def test_optimize_index(self, index_manager, sample_document):
        """インデックス最適化テスト"""
        index_manager.add_document(sample_document)
        
        # 最適化が正常に実行されることを確認
        index_manager.optimize_index()
        
        # 最適化後も検索が正常に動作することを確認
        results = index_manager.search_text("テスト")
        assert len(results) == 1

    def test_document_exists(self, index_manager, sample_document):
        """ドキュメント存在確認テスト"""
        assert not index_manager.document_exists(sample_document.id)
        
        index_manager.add_document(sample_document)
        assert index_manager.document_exists(sample_document.id)

    def test_search_empty_query(self, index_manager, sample_document):
        """空クエリ検索テスト"""
        index_manager.add_document(sample_document)
        
        results = index_manager.search_text("")
        
        assert len(results) == 0

    def test_search_no_results(self, index_manager, sample_document):
        """結果なし検索テスト"""
        index_manager.add_document(sample_document)
        
        results = index_manager.search_text("存在しない単語")
        
        assert len(results) == 0

    def test_error_handling_invalid_index_path(self):
        """無効なインデックスパスのエラーハンドリングテスト"""
        with patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied")):
            with pytest.raises(IndexingError):
                IndexManager("/invalid/path")

    def test_error_handling_add_document_failure(self, index_manager):
        """ドキュメント追加失敗のエラーハンドリングテスト"""
        # 無効なドキュメントオブジェクト
        invalid_doc = Mock()
        invalid_doc.id = None  # 無効なID
        
        with pytest.raises(IndexingError):
            index_manager.add_document(invalid_doc)

    def test_search_error_handling(self, index_manager):
        """検索エラーハンドリングテスト"""
        # インデックスを閉じて検索エラーを発生させる
        index_manager.close()
        
        with pytest.raises(SearchError):
            index_manager.search_text("テスト")

    def test_close_index(self, index_manager):
        """インデックス終了テスト"""
        index_manager.close()
        
        assert index_manager._index is None

    def test_concurrent_access_safety(self, index_manager, multiple_documents):
        """並行アクセス安全性テスト"""
        import threading
        import time
        
        def add_documents(docs):
            for doc in docs:
                index_manager.add_document(doc)
                time.sleep(0.01)  # 少し待機
        
        # 複数スレッドで同時にドキュメントを追加
        threads = []
        doc_chunks = [multiple_documents[:2], multiple_documents[2:4], multiple_documents[4:]]
        
        for chunk in doc_chunks:
            thread = threading.Thread(target=add_documents, args=(chunk,))
            threads.append(thread)
            thread.start()
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 全ドキュメントが正常に追加されたことを確認
        assert index_manager.get_document_count() == 5

    def test_memory_usage_monitoring(self, index_manager, large_document_set):
        """メモリ使用量監視テスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 大量のドキュメントを追加
        for doc in large_document_set:
            index_manager.add_document(doc)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加量が合理的な範囲内であることを確認（100MB以下）
        assert memory_increase < 100 * 1024 * 1024

    def test_search_performance_benchmark(self, index_manager, large_document_set):
        """検索パフォーマンスベンチマークテスト"""
        import time
        
        # 大量のドキュメントを追加
        for doc in large_document_set:
            index_manager.add_document(doc)
        
        # 検索パフォーマンスを測定
        queries = ["テスト", "ドキュメント", "検索", "データ", "機能"]
        
        for query in queries:
            start_time = time.time()
            results = index_manager.search_text(query)
            end_time = time.time()
            
            # 各検索が1秒以内に完了することを確認
            assert (end_time - start_time) < 1.0
            assert len(results) > 0