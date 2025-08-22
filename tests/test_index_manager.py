# -*- coding: utf-8 -*-
"""
IndexManagerクラスのユニットテスト

Whoosh全文検索エンジンの機能をテストします。
"""

import os
import tempfile
import shutil
import pytest
from datetime import datetime
from pathlib import Path

from src.core.index_manager import IndexManager
from src.data.models import Document, FileType, SearchType
from src.utils.exceptions import IndexingError, SearchError


class TestIndexManager:
    """IndexManagerクラスのテストクラス"""
    
    @pytest.fixture
    def temp_index_dir(self):
        """テスト用の一時インデックスディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # テスト後にクリーンアップ
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def index_manager(self, temp_index_dir):
        """テスト用のIndexManagerインスタンスを作成"""
        return IndexManager(temp_index_dir)
    
    @pytest.fixture
    def sample_document(self):
        """テスト用のサンプルドキュメントを作成"""
        # 一時ファイルを作成
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write("これはテスト用のドキュメントです。検索機能をテストします。")
        temp_file.close()
        
        doc = Document.create_from_file(
            temp_file.name,
            "これはテスト用のドキュメントです。検索機能をテストします。"
        )
        
        yield doc
        
        # テスト後にファイルを削除
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    @pytest.fixture
    def multiple_documents(self):
        """複数のテスト用ドキュメントを作成"""
        documents = []
        temp_files = []
        
        contents = [
            "Python プログラミング言語について説明します。",
            "機械学習とAIの基礎概念を学びます。",
            "データベース設計の重要なポイントを解説します。",
            "ウェブ開発のベストプラクティスを紹介します。",
            "セキュリティ対策の基本的な考え方を説明します。"
        ]
        
        for i, content in enumerate(contents):
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt', delete=False, encoding='utf-8'
            )
            temp_file.write(content)
            temp_file.close()
            temp_files.append(temp_file.name)
            
            doc = Document.create_from_file(temp_file.name, content)
            documents.append(doc)
        
        yield documents
        
        # テスト後にファイルを削除
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_index_initialization(self, temp_index_dir):
        """インデックスの初期化をテスト"""
        # インデックスマネージャーを作成
        index_manager = IndexManager(temp_index_dir)
        
        # インデックスディレクトリが作成されることを確認
        assert os.path.exists(temp_index_dir)
        
        # ドキュメント数が0であることを確認
        assert index_manager.get_document_count() == 0
    
    def test_create_index(self, index_manager):
        """新しいインデックスの作成をテスト"""
        # インデックスを作成
        index_manager.create_index()
        
        # ドキュメント数が0であることを確認
        assert index_manager.get_document_count() == 0
    
    def test_add_document(self, index_manager, sample_document):
        """ドキュメントの追加をテスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        
        # ドキュメント数が1になることを確認
        assert index_manager.get_document_count() == 1
        
        # ドキュメントが存在することを確認
        assert index_manager.document_exists(sample_document.id)
    
    def test_update_document(self, index_manager, sample_document):
        """ドキュメントの更新をテスト"""
        # 最初にドキュメントを追加
        index_manager.add_document(sample_document)
        
        # ドキュメントの内容を変更
        sample_document.content = "更新されたコンテンツです。新しい情報が含まれています。"
        sample_document.indexed_date = datetime.now()
        
        # ドキュメントを更新
        index_manager.update_document(sample_document)
        
        # ドキュメント数は1のまま
        assert index_manager.get_document_count() == 1
        
        # 更新されたドキュメントが検索できることを確認
        results = index_manager.search_text("更新された")
        assert len(results) == 1
        assert "更新された" in results[0].document.content
    
    def test_remove_document(self, index_manager, sample_document):
        """ドキュメントの削除をテスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        assert index_manager.get_document_count() == 1
        
        # ドキュメントを削除
        index_manager.remove_document(sample_document.id)
        
        # ドキュメント数が0になることを確認
        assert index_manager.get_document_count() == 0
        
        # ドキュメントが存在しないことを確認
        assert not index_manager.document_exists(sample_document.id)
    
    def test_search_text_basic(self, index_manager, sample_document):
        """基本的な全文検索をテスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        
        # 検索を実行
        results = index_manager.search_text("テスト")
        
        # 結果が1件返されることを確認
        assert len(results) == 1
        
        # 検索結果の内容を確認
        result = results[0]
        assert result.document.id == sample_document.id
        assert result.search_type == SearchType.FULL_TEXT
        assert result.score > 0
        assert "テスト" in result.highlighted_terms
    
    def test_search_text_multiple_documents(self, index_manager, multiple_documents):
        """複数ドキュメントでの検索をテスト"""
        # 複数のドキュメントを追加
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        # 検索を実行
        results = index_manager.search_text("プログラミング")
        
        # 結果が1件返されることを確認
        assert len(results) == 1
        assert "プログラミング" in results[0].document.content
        
        # より一般的な用語で検索
        results = index_manager.search_text("説明")
        
        # 複数の結果が返されることを確認
        assert len(results) >= 2
    
    def test_search_text_no_results(self, index_manager, sample_document):
        """検索結果がない場合をテスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        
        # 存在しない用語で検索
        results = index_manager.search_text("存在しない用語")
        
        # 結果が0件であることを確認
        assert len(results) == 0
    
    def test_search_text_empty_query(self, index_manager, sample_document):
        """空のクエリでの検索をテスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        
        # 空のクエリで検索
        results = index_manager.search_text("")
        
        # 結果が0件であることを確認
        assert len(results) == 0
        
        # スペースのみのクエリで検索
        results = index_manager.search_text("   ")
        
        # 結果が0件であることを確認
        assert len(results) == 0
    
    def test_search_with_file_type_filter(self, index_manager, multiple_documents):
        """ファイルタイプフィルターでの検索をテスト"""
        # 複数のドキュメントを追加
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        # テキストファイルのみで検索
        results = index_manager.search_text(
            "説明", 
            file_types=[FileType.TEXT]
        )
        
        # すべての結果がテキストファイルであることを確認
        for result in results:
            assert result.document.file_type == FileType.TEXT
    
    def test_search_with_date_filter(self, index_manager, sample_document):
        """日付フィルターでの検索をテスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        
        # 現在日時より前の日付で検索（結果なし）
        from datetime import timedelta
        past_date = datetime.now() - timedelta(days=1)
        results = index_manager.search_text(
            "テスト",
            date_to=past_date
        )
        
        # 結果が0件であることを確認
        assert len(results) == 0
        
        # 現在日時より後の日付で検索（結果あり）
        future_date = datetime.now() + timedelta(days=1)
        results = index_manager.search_text(
            "テスト",
            date_to=future_date
        )
        
        # 結果が1件であることを確認
        assert len(results) == 1
    
    def test_rebuild_index(self, index_manager, multiple_documents):
        """インデックスの再構築をテスト"""
        # 最初にいくつかのドキュメントを追加
        for doc in multiple_documents[:2]:
            index_manager.add_document(doc)
        
        assert index_manager.get_document_count() == 2
        
        # インデックスを再構築
        index_manager.rebuild_index(multiple_documents)
        
        # すべてのドキュメントがインデックスされていることを確認
        assert index_manager.get_document_count() == len(multiple_documents)
        
        # 検索が正常に動作することを確認
        results = index_manager.search_text("説明")
        assert len(results) >= 1
    
    def test_optimize_index(self, index_manager, multiple_documents):
        """インデックスの最適化をテスト"""
        # 複数のドキュメントを追加
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        # インデックスを最適化
        index_manager.optimize_index()
        
        # 最適化後も検索が正常に動作することを確認
        results = index_manager.search_text("プログラミング")
        assert len(results) >= 1
    
    def test_get_index_stats(self, index_manager, multiple_documents):
        """インデックス統計情報の取得をテスト"""
        # 複数のドキュメントを追加
        for doc in multiple_documents:
            index_manager.add_document(doc)
        
        # 統計情報を取得
        stats = index_manager.get_index_stats()
        
        # 統計情報の内容を確認
        assert "document_count" in stats
        assert stats["document_count"] == len(multiple_documents)
        assert "index_size" in stats
        assert stats["index_size"] > 0
        assert "last_modified" in stats
    
    def test_snippet_generation(self, index_manager, sample_document):
        """スニペット生成をテスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        
        # 検索を実行
        results = index_manager.search_text("テスト")
        
        # スニペットが生成されていることを確認
        assert len(results) == 1
        result = results[0]
        assert result.snippet
        assert len(result.snippet) > 0
        assert "テスト" in result.snippet or "テスト" in result.document.content
    
    def test_highlighted_terms_extraction(self, index_manager, sample_document):
        """ハイライト用語の抽出をテスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        
        # 検索を実行
        results = index_manager.search_text("テスト 検索")
        
        # ハイライト用語が抽出されていることを確認
        assert len(results) == 1
        result = results[0]
        assert len(result.highlighted_terms) > 0
        
        # 検索用語が含まれていることを確認
        highlighted_text = " ".join(result.highlighted_terms)
        assert "テスト" in highlighted_text or "検索" in highlighted_text
    
    def test_error_handling_invalid_index_path(self):
        """無効なインデックスパスでのエラーハンドリングをテスト"""
        # 読み取り専用のディレクトリを指定（権限エラーを発生させる）
        invalid_path = "/root/invalid_path"  # Linuxの場合
        
        # Windowsの場合は別のパスを使用
        if os.name == 'nt':
            invalid_path = "C:\\Windows\\System32\\invalid_path"
        
        # IndexingErrorが発生することを確認
        with pytest.raises(IndexingError):
            IndexManager(invalid_path)
    
    def test_search_error_handling(self, index_manager):
        """検索エラーのハンドリングをテスト"""
        # インデックスを閉じる
        index_manager.close()
        
        # 閉じられたインデックスで検索を実行
        with pytest.raises(SearchError):
            index_manager.search_text("テスト")
    
    def test_close_index(self, index_manager, sample_document):
        """インデックスのクローズをテスト"""
        # ドキュメントを追加
        index_manager.add_document(sample_document)
        
        # インデックスを閉じる
        index_manager.close()
        
        # 閉じた後はドキュメント数が取得できない（0が返される）
        assert index_manager.get_document_count() == 0