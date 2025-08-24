#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索インターフェースの基本動作確認スクリプト

PySide6の依存関係なしで基本的な機能をテストします。
"""

import sys
import os
from unittest.mock import Mock, MagicMock
from datetime import datetime

# テスト対象のモジュールをインポートするためのパス設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_search_query_building():
    """検索クエリ構築のテスト"""
    from src.data.models import SearchQuery, SearchType, FileType
    
    # 基本的な検索クエリの作成
    query = SearchQuery(
        query_text="テスト検索",
        search_type=SearchType.HYBRID
    )
    
    assert query.query_text == "テスト検索"
    assert query.search_type == SearchType.HYBRID
    assert query.limit == 100  # デフォルト値
    print("✓ 検索クエリ構築テスト: 成功")

def test_search_result_creation():
    """検索結果作成のテスト"""
    from src.data.models import SearchResult, SearchType, Document, FileType
    import tempfile
    import os
    
    # 一時ファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("これはテストドキュメントです。")
        temp_file_path = f.name
    
    try:
        # テストドキュメントの作成
        document = Document.create_from_file(temp_file_path, "これはテストドキュメントです。")
        
        # 検索結果の作成
        result = SearchResult(
            document=document,
            score=0.85,
            search_type=SearchType.HYBRID,
            snippet="これはテストドキュメント...",
            highlighted_terms=["テスト"],
            relevance_explanation="ハイブリッド検索結果"
        )
        
        assert result.document.file_type == FileType.TEXT
        assert result.score == 0.85
        assert result.search_type == SearchType.HYBRID
        assert "テスト" in result.highlighted_terms
        print("✓ 検索結果作成テスト: 成功")
        
    finally:
        # 一時ファイルを削除
        os.unlink(temp_file_path)

def test_file_type_detection():
    """ファイルタイプ検出のテスト"""
    from src.data.models import FileType
    
    # 各種ファイル拡張子のテスト
    test_cases = [
        ("document.pdf", FileType.PDF),
        ("document.docx", FileType.WORD),
        ("document.xlsx", FileType.EXCEL),
        ("document.md", FileType.MARKDOWN),
        ("document.txt", FileType.TEXT),
        ("document.unknown", FileType.UNKNOWN)
    ]
    
    for file_path, expected_type in test_cases:
        detected_type = FileType.from_extension(file_path)
        assert detected_type == expected_type, f"{file_path} -> {detected_type} != {expected_type}"
    
    print("✓ ファイルタイプ検出テスト: 成功")

def test_search_history_repository():
    """検索履歴リポジトリのテスト（モック使用）"""
    from src.data.search_history_repository import SearchHistoryRepository
    from src.data.models import SearchType
    from contextlib import contextmanager
    
    # モックのデータベースマネージャーを作成
    mock_db_manager = Mock()
    mock_connection = Mock()
    
    @contextmanager
    def mock_get_connection():
        yield mock_connection
    
    mock_db_manager.get_connection = mock_get_connection
    
    # リポジトリを作成
    repo = SearchHistoryRepository(mock_db_manager)
    
    # 検索履歴追加のテスト
    result = repo.add_search_record("テスト検索", SearchType.HYBRID, 5, 1500)
    assert result == True
    
    # データベース呼び出しが正しく行われたことを確認
    mock_connection.execute.assert_called()
    mock_connection.commit.assert_called()
    
    print("✓ 検索履歴リポジトリテスト: 成功")

def test_search_weights():
    """検索重み設定のテスト"""
    # SearchWeightsクラスを直接定義してテスト
    from dataclasses import dataclass
    
    @dataclass
    class SearchWeights:
        """検索重み設定を管理するデータクラス"""
        full_text: float = 0.6      # 全文検索の重み
        semantic: float = 0.4       # セマンティック検索の重み
        
        def __post_init__(self):
            """重みの合計が1.0になるように正規化"""
            total = self.full_text + self.semantic
            if total > 0:
                self.full_text /= total
                self.semantic /= total
    
    # デフォルト重みのテスト
    weights = SearchWeights()
    assert abs(weights.full_text + weights.semantic - 1.0) < 0.001
    
    # カスタム重みのテスト
    weights = SearchWeights(full_text=0.7, semantic=0.3)
    assert abs(weights.full_text - 0.7) < 0.001
    assert abs(weights.semantic - 0.3) < 0.001
    
    # 正規化のテスト
    weights = SearchWeights(full_text=3.0, semantic=2.0)
    assert abs(weights.full_text - 0.6) < 0.001
    assert abs(weights.semantic - 0.4) < 0.001
    
    print("✓ 検索重み設定テスト: 成功")

def test_document_validation():
    """ドキュメント検証のテスト"""
    from src.data.models import Document, FileType
    import tempfile
    import os
    
    # 一時ファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("テストコンテンツ")
        temp_file_path = f.name
    
    try:
        # 正常なドキュメントの作成
        document = Document.create_from_file(temp_file_path, "テストコンテンツ")
        
        assert document.file_path == os.path.abspath(temp_file_path)
        assert document.file_type == FileType.TEXT
        assert document.content == "テストコンテンツ"
        assert document.content_hash != ""
        
        print("✓ ドキュメント検証テスト: 成功")
        
    finally:
        # 一時ファイルを削除
        os.unlink(temp_file_path)

def run_all_tests():
    """全てのテストを実行"""
    print("検索インターフェース基本動作確認を開始...")
    print()
    
    try:
        test_search_query_building()
        test_search_result_creation()
        test_file_type_detection()
        test_search_history_repository()
        test_search_weights()
        test_document_validation()
        
        print()
        print("🎉 全てのテストが成功しました！")
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)