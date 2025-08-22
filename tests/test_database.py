"""
データベース層のユニットテスト

このモジュールは、DatabaseManager、DocumentRepository、SearchHistoryRepositoryの
機能をテストし、データの整合性と操作の正確性を検証します。
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from src.data.database import DatabaseManager
from src.data.document_repository import DocumentRepository
from src.data.search_history_repository import SearchHistoryRepository
from src.data.models import Document, FileType, SearchType
from src.utils.exceptions import DatabaseError, DocumentNotFoundError


class TestDatabaseManager:
    """DatabaseManagerクラスのテスト"""
    
    @pytest.fixture
    def temp_db_path(self):
        """テスト用の一時データベースパスを提供"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # クリーンアップ
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """テスト用のDatabaseManagerインスタンスを提供"""
        return DatabaseManager(temp_db_path)
    
    def test_database_initialization(self, db_manager):
        """データベースの初期化をテスト"""
        # データベースファイルが作成されることを確認
        assert db_manager.db_path.exists()
        
        # 健全性チェックが成功することを確認
        assert db_manager.health_check()
    
    def test_schema_creation(self, db_manager):
        """スキーマ作成をテスト"""
        with db_manager.get_connection() as conn:
            # documentsテーブルの存在確認
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='documents'
            """)
            assert cursor.fetchone() is not None
            
            # search_historyテーブルの存在確認
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='search_history'
            """)
            assert cursor.fetchone() is not None
            
            # インデックスの存在確認
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_documents_path'
            """)
            assert cursor.fetchone() is not None
    
    def test_database_stats(self, db_manager):
        """データベース統計情報の取得をテスト"""
        stats = db_manager.get_database_stats()
        
        assert 'document_count' in stats
        assert 'search_history_count' in stats
        assert 'file_type_stats' in stats
        assert 'db_file_size' in stats
        
        # 初期状態では0件
        assert stats['document_count'] == 0
        assert stats['search_history_count'] == 0
    
    def test_vacuum_database(self, db_manager):
        """データベース最適化をテスト"""
        # 例外が発生しないことを確認
        db_manager.vacuum_database()


class TestDocumentRepository:
    """DocumentRepositoryクラスのテスト"""
    
    @pytest.fixture
    def temp_db_path(self):
        """テスト用の一時データベースパスを提供"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """テスト用のDatabaseManagerインスタンスを提供"""
        return DatabaseManager(temp_db_path)
    
    @pytest.fixture
    def doc_repository(self, db_manager):
        """テスト用のDocumentRepositoryインスタンスを提供"""
        return DocumentRepository(db_manager)
    
    @pytest.fixture
    def sample_document(self, tmp_path):
        """テスト用のサンプルドキュメントを作成"""
        # テスト用ファイルを作成
        test_file = tmp_path / "test_document.txt"
        test_file.write_text("これはテスト用のドキュメントです。", encoding='utf-8')
        
        return Document.create_from_file(str(test_file), "テスト用のコンテンツです。")
    
    def test_create_document(self, doc_repository, sample_document):
        """ドキュメント作成をテスト"""
        result = doc_repository.create_document(sample_document)
        assert result is True
        
        # 作成されたドキュメントを取得して確認
        retrieved = doc_repository.get_document_by_id(sample_document.id)
        assert retrieved is not None
        assert retrieved.title == sample_document.title
        assert retrieved.file_path == sample_document.file_path
    
    def test_get_document_by_id(self, doc_repository, sample_document):
        """IDによるドキュメント取得をテスト"""
        # ドキュメントを作成
        doc_repository.create_document(sample_document)
        
        # IDで取得
        retrieved = doc_repository.get_document_by_id(sample_document.id)
        assert retrieved is not None
        assert retrieved.id == sample_document.id
        
        # 存在しないIDの場合
        non_existent = doc_repository.get_document_by_id("non_existent_id")
        assert non_existent is None
    
    def test_get_document_by_path(self, doc_repository, sample_document):
        """パスによるドキュメント取得をテスト"""
        # ドキュメントを作成
        doc_repository.create_document(sample_document)
        
        # パスで取得
        retrieved = doc_repository.get_document_by_path(sample_document.file_path)
        assert retrieved is not None
        assert retrieved.file_path == sample_document.file_path
        
        # 存在しないパスの場合
        non_existent = doc_repository.get_document_by_path("/non/existent/path.txt")
        assert non_existent is None
    
    def test_update_document(self, doc_repository, sample_document, tmp_path):
        """ドキュメント更新をテスト"""
        # ドキュメントを作成
        doc_repository.create_document(sample_document)
        
        # タイトルを更新
        sample_document.title = "更新されたタイトル"
        sample_document.indexed_date = datetime.now()
        
        result = doc_repository.update_document(sample_document)
        assert result is True
        
        # 更新されたドキュメントを取得して確認
        retrieved = doc_repository.get_document_by_id(sample_document.id)
        assert retrieved.title == "更新されたタイトル"
        
        # 存在しないドキュメントの更新（テスト用の一時ファイルを作成）
        temp_file = tmp_path / "non_existent.txt"
        temp_file.write_text("テスト", encoding='utf-8')
        
        non_existent_doc = Document(
            id="non_existent",
            file_path=str(temp_file),
            title="存在しない",
            content="",
            file_type=FileType.TEXT,
            size=0,
            created_date=datetime.now(),
            modified_date=datetime.now(),
            indexed_date=datetime.now()
        )
        
        with pytest.raises(DocumentNotFoundError):
            doc_repository.update_document(non_existent_doc)
    
    def test_delete_document(self, doc_repository, sample_document):
        """ドキュメント削除をテスト"""
        # ドキュメントを作成
        doc_repository.create_document(sample_document)
        
        # 削除
        result = doc_repository.delete_document(sample_document.id)
        assert result is True
        
        # 削除されたことを確認
        retrieved = doc_repository.get_document_by_id(sample_document.id)
        assert retrieved is None
        
        # 存在しないドキュメントの削除
        with pytest.raises(DocumentNotFoundError):
            doc_repository.delete_document("non_existent_id")
    
    def test_get_all_documents(self, doc_repository, tmp_path):
        """全ドキュメント取得をテスト"""
        # 複数のドキュメントを作成
        documents = []
        for i in range(5):
            test_file = tmp_path / f"test_{i}.txt"
            test_file.write_text(f"テストファイル{i}", encoding='utf-8')
            doc = Document.create_from_file(str(test_file), f"コンテンツ{i}")
            documents.append(doc)
            doc_repository.create_document(doc)
        
        # 全ドキュメントを取得
        all_docs = doc_repository.get_all_documents()
        assert len(all_docs) == 5
        
        # 制限付きで取得
        limited_docs = doc_repository.get_all_documents(limit=3)
        assert len(limited_docs) == 3
    
    def test_get_documents_by_type(self, doc_repository, tmp_path):
        """ファイルタイプ別ドキュメント取得をテスト"""
        # 異なるタイプのファイルを作成
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("テキストファイル", encoding='utf-8')
        txt_doc = Document.create_from_file(str(txt_file), "テキストコンテンツ")
        
        md_file = tmp_path / "test.md"
        md_file.write_text("# マークダウンファイル", encoding='utf-8')
        md_doc = Document.create_from_file(str(md_file), "マークダウンコンテンツ")
        
        doc_repository.create_document(txt_doc)
        doc_repository.create_document(md_doc)
        
        # テキストファイルのみ取得
        txt_docs = doc_repository.get_documents_by_type(FileType.TEXT)
        assert len(txt_docs) == 1
        assert txt_docs[0].file_type == FileType.TEXT
        
        # マークダウンファイルのみ取得
        md_docs = doc_repository.get_documents_by_type(FileType.MARKDOWN)
        assert len(md_docs) == 1
        assert md_docs[0].file_type == FileType.MARKDOWN
    
    def test_search_documents_by_title(self, doc_repository, tmp_path):
        """タイトル検索をテスト"""
        # 異なるタイトルのドキュメントを作成
        titles = ["プロジェクト計画書", "設計書", "テスト計画書", "ユーザーマニュアル"]
        
        for title in titles:
            test_file = tmp_path / f"{title}.txt"
            test_file.write_text(title, encoding='utf-8')
            doc = Document.create_from_file(str(test_file), title)
            doc.title = title
            doc_repository.create_document(doc)
        
        # "計画書"を含むドキュメントを検索
        results = doc_repository.search_documents_by_title("計画書")
        assert len(results) == 2
        
        # "設計"を含むドキュメントを検索
        results = doc_repository.search_documents_by_title("設計")
        assert len(results) == 1
        assert results[0].title == "設計書"
    
    def test_get_document_count(self, doc_repository, tmp_path):
        """ドキュメント数取得をテスト"""
        # 初期状態では0件
        assert doc_repository.get_document_count() == 0
        
        # ドキュメントを追加
        for i in range(3):
            test_file = tmp_path / f"test_{i}.txt"
            test_file.write_text(f"テスト{i}", encoding='utf-8')
            doc = Document.create_from_file(str(test_file), f"コンテンツ{i}")
            doc_repository.create_document(doc)
        
        assert doc_repository.get_document_count() == 3
    
    def test_bulk_insert_documents(self, doc_repository, tmp_path):
        """一括挿入をテスト"""
        # 複数のドキュメントを準備
        documents = []
        for i in range(10):
            test_file = tmp_path / f"bulk_{i}.txt"
            test_file.write_text(f"一括テスト{i}", encoding='utf-8')
            doc = Document.create_from_file(str(test_file), f"一括コンテンツ{i}")
            documents.append(doc)
        
        # 一括挿入
        result = doc_repository.bulk_insert_documents(documents)
        assert result == 10
        
        # 挿入されたことを確認
        assert doc_repository.get_document_count() == 10
    
    def test_get_index_stats(self, doc_repository, tmp_path):
        """インデックス統計取得をテスト"""
        # 初期状態の統計
        stats = doc_repository.get_index_stats()
        assert stats.total_documents == 0
        assert stats.total_size == 0
        
        # ドキュメントを追加
        test_file = tmp_path / "stats_test.txt"
        test_content = "統計テスト用のコンテンツです。"
        test_file.write_text(test_content, encoding='utf-8')
        
        doc = Document.create_from_file(str(test_file), test_content)
        doc_repository.create_document(doc)
        
        # 統計を再取得
        stats = doc_repository.get_index_stats()
        assert stats.total_documents == 1
        assert stats.total_size > 0
        assert FileType.TEXT in stats.file_type_counts
        assert stats.file_type_counts[FileType.TEXT] == 1


class TestSearchHistoryRepository:
    """SearchHistoryRepositoryクラスのテスト"""
    
    @pytest.fixture
    def temp_db_path(self):
        """テスト用の一時データベースパスを提供"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """テスト用のDatabaseManagerインスタンスを提供"""
        return DatabaseManager(temp_db_path)
    
    @pytest.fixture
    def history_repository(self, db_manager):
        """テスト用のSearchHistoryRepositoryインスタンスを提供"""
        return SearchHistoryRepository(db_manager)
    
    def test_add_search_record(self, history_repository):
        """検索履歴記録をテスト"""
        result = history_repository.add_search_record(
            query="テスト検索",
            search_type=SearchType.FULL_TEXT,
            result_count=5,
            execution_time_ms=150
        )
        assert result is True
    
    def test_get_recent_searches(self, history_repository):
        """最近の検索履歴取得をテスト"""
        # 複数の検索履歴を追加
        searches = [
            ("Python プログラミング", SearchType.FULL_TEXT, 10, 120),
            ("機械学習 入門", SearchType.SEMANTIC, 8, 200),
            ("データベース 設計", SearchType.HYBRID, 15, 180)
        ]
        
        for query, search_type, result_count, exec_time in searches:
            history_repository.add_search_record(query, search_type, result_count, exec_time)
        
        # 最近の検索履歴を取得
        recent = history_repository.get_recent_searches(limit=5)
        assert len(recent) == 3
        
        # 最新のものが最初に来ることを確認
        assert recent[0]['query'] == "データベース 設計"
        assert recent[0]['search_type'] == SearchType.HYBRID
    
    def test_get_popular_queries(self, history_repository):
        """人気クエリ取得をテスト"""
        # 同じクエリを複数回記録
        for _ in range(3):
            history_repository.add_search_record("人気クエリ", SearchType.FULL_TEXT, 5, 100)
        
        for _ in range(2):
            history_repository.add_search_record("普通のクエリ", SearchType.SEMANTIC, 3, 150)
        
        history_repository.add_search_record("一回だけのクエリ", SearchType.HYBRID, 1, 200)
        
        # 人気クエリを取得
        popular = history_repository.get_popular_queries(days=30, limit=10)
        assert len(popular) >= 2
        
        # 最も人気のあるクエリが最初に来ることを確認
        assert popular[0]['query'] == "人気クエリ"
        assert popular[0]['search_count'] == 3
    
    def test_get_search_suggestions(self, history_repository):
        """検索提案取得をテスト"""
        # 類似したクエリを記録
        queries = [
            "Python プログラミング基礎",
            "Python 入門",
            "Python データ分析",
            "Java プログラミング"
        ]
        
        for query in queries:
            history_repository.add_search_record(query, SearchType.FULL_TEXT, 5, 100)
        
        # "Python"で始まる提案を取得
        suggestions = history_repository.get_search_suggestions("Python", limit=5)
        assert len(suggestions) == 3
        
        # すべて"Python"で始まることを確認
        for suggestion in suggestions:
            assert suggestion.startswith("Python")
    
    def test_get_search_statistics(self, history_repository):
        """検索統計取得をテスト"""
        # 異なるタイプの検索を記録
        history_repository.add_search_record("クエリ1", SearchType.FULL_TEXT, 10, 100)
        history_repository.add_search_record("クエリ2", SearchType.SEMANTIC, 5, 200)
        history_repository.add_search_record("クエリ3", SearchType.HYBRID, 8, 150)
        
        # 統計を取得
        stats = history_repository.get_search_statistics(days=30)
        
        assert stats['total_searches'] == 3
        assert 'by_search_type' in stats
        assert 'daily_counts' in stats
        assert 'performance' in stats
        
        # 検索タイプ別統計を確認
        assert 'full_text' in stats['by_search_type']
        assert 'semantic' in stats['by_search_type']
        assert 'hybrid' in stats['by_search_type']
    
    def test_clear_old_history(self, history_repository):
        """古い履歴削除をテスト"""
        # 現在の検索を記録
        history_repository.add_search_record("新しい検索", SearchType.FULL_TEXT, 5, 100)
        
        # 古い検索を直接データベースに挿入（テスト用）
        old_date = datetime.now() - timedelta(days=100)
        with history_repository.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO search_history (query, search_type, timestamp, result_count, execution_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """, ("古い検索", "full_text", old_date, 3, 120))
            conn.commit()
        
        # 古い履歴を削除（90日より古いもの）
        deleted_count = history_repository.clear_old_history(days_to_keep=90)
        assert deleted_count == 1
        
        # 新しい検索は残っていることを確認
        recent = history_repository.get_recent_searches(limit=10)
        assert len(recent) == 1
        assert recent[0]['query'] == "新しい検索"
    
    def test_get_failed_searches(self, history_repository):
        """失敗した検索の取得をテスト"""
        # 成功した検索と失敗した検索を記録
        history_repository.add_search_record("成功検索", SearchType.FULL_TEXT, 5, 100)
        history_repository.add_search_record("失敗検索1", SearchType.FULL_TEXT, 0, 50)
        history_repository.add_search_record("失敗検索2", SearchType.SEMANTIC, 0, 80)
        history_repository.add_search_record("失敗検索1", SearchType.FULL_TEXT, 0, 60)  # 重複
        
        # 失敗した検索を取得
        failed = history_repository.get_failed_searches(days=7, limit=10)
        assert len(failed) == 2
        
        # 失敗回数の多い順に並んでいることを確認
        assert failed[0]['query'] == "失敗検索1"
        assert failed[0]['failure_count'] == 2
        assert failed[1]['query'] == "失敗検索2"
        assert failed[1]['failure_count'] == 1