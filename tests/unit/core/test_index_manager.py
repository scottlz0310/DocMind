"""
IndexManagerのテストモジュール

Whoosh全文検索インデックス管理機能の包括的なテストを提供します。
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.index_manager import IndexManager
from src.data.models import Document, FileType, SearchType
from src.utils.exceptions import IndexingError, SearchError


class TestIndexManager:
    """IndexManagerのテストクラス"""

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
        return Document(
            id="test_doc_1",
            file_path="/test/sample.txt",
            title="テストドキュメント",
            content="これはテスト用のドキュメントです。検索機能をテストします。",
            file_type=FileType.TEXT,
            size=1024,
            created_date=datetime.now(),
            modified_date=datetime.now(),
            indexed_date=datetime.now(),
            content_hash="test_hash_123"
        )

    @pytest.fixture
    def multiple_documents(self):
        """複数のサンプルドキュメントを作成"""
        docs = []
        for i in range(5):
            doc = Document(
                id=f"test_doc_{i}",
                file_path=f"/test/sample_{i}.txt",
                title=f"テストドキュメント{i}",
                content=f"これは{i}番目のテストドキュメントです。検索テスト用データ。",
                file_type=FileType.TEXT,
                size=1024 + i * 100,
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=f"test_hash_{i}"
            )
            docs.append(doc)
        return docs

    def test_initialization(self, index_manager):
        """初期化テスト"""
        assert index_manager is not None
        assert index_manager._index is not None
        assert index_manager.index_path.exists()

    def test_create_index(self, index_manager):
        """インデックス作成テスト"""
        # 既存のインデックスを削除して新規作成
        index_manager.create_index()
        
        assert index_manager._index is not None
        assert index_manager.get_document_count() == 0

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
        base_date = datetime(2024, 1, 1)
        for i, doc in enumerate(multiple_documents):
            doc.modified_date = datetime(2024, 1, i + 1)
            index_manager.add_document(doc)
        
        # 特定の日付範囲で検索
        date_from = datetime(2024, 1, 2)
        date_to = datetime(2024, 1, 4)
        
        results = index_manager.search_text("テスト", date_from=date_from, date_to=date_to)
        
        # 日付範囲内のドキュメントのみが返されることを確認
        assert len(results) == 3

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

    def test_get_index_stats(self, index_manager, multiple_documents):
        """インデックス統計情報取得テスト"""
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        stats = index_manager.get_index_stats()
        
        assert isinstance(stats, dict)
        assert stats["document_count"] == 5
        assert "index_size" in stats
        assert "last_modified" in stats

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