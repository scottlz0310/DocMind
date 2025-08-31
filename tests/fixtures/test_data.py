"""
Phase5テスト環境 - テストデータフィクスチャ

最小限のテストデータセットを提供
"""

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def sample_documents() -> list[dict[str, Any]]:
    """サンプルドキュメントデータ"""
    return [
        {
            "title": "テストドキュメント1",
            "path": "/test/documents/doc1.txt",
            "content": "これはテスト用のドキュメントです。",
            "file_type": "txt",
            "size": 1024,
            "modified": "2024-01-01T00:00:00",
        },
        {
            "title": "テストドキュメント2",
            "path": "/test/documents/doc2.pdf",
            "content": "PDFファイルのテスト内容です。",
            "file_type": "pdf",
            "size": 2048,
            "modified": "2024-01-02T00:00:00",
        },
        {
            "title": "テストドキュメント3",
            "path": "/test/documents/doc3.docx",
            "content": "Wordドキュメントのテスト内容です。",
            "file_type": "docx",
            "size": 4096,
            "modified": "2024-01-03T00:00:00",
        },
    ]


@pytest.fixture
def sample_search_queries() -> list[str]:
    """サンプル検索クエリ"""
    return ["テスト", "ドキュメント", "PDF ファイル", "Word 文書", "検索テスト"]


@pytest.fixture
def sample_search_results() -> list[dict[str, Any]]:
    """サンプル検索結果"""
    return [
        {
            "title": "検索結果1",
            "path": "/test/results/result1.txt",
            "score": 0.95,
            "snippet": "検索にマッチしたテキストの抜粋...",
            "file_type": "txt",
        },
        {
            "title": "検索結果2",
            "path": "/test/results/result2.pdf",
            "score": 0.87,
            "snippet": "PDFファイルからの抜粋...",
            "file_type": "pdf",
        },
    ]


@pytest.fixture
def sample_folder_structure() -> dict[str, Any]:
    """サンプルフォルダ構造"""
    return {
        "name": "test_root",
        "path": "/test/root",
        "type": "folder",
        "children": [
            {
                "name": "documents",
                "path": "/test/root/documents",
                "type": "folder",
                "children": [
                    {
                        "name": "file1.txt",
                        "path": "/test/root/documents/file1.txt",
                        "type": "file",
                    },
                    {
                        "name": "file2.pdf",
                        "path": "/test/root/documents/file2.pdf",
                        "type": "file",
                    },
                ],
            },
            {
                "name": "images",
                "path": "/test/root/images",
                "type": "folder",
                "children": [],
            },
        ],
    }


@pytest.fixture
def sample_index_data() -> dict[str, Any]:
    """サンプルインデックスデータ"""
    return {
        "total_files": 100,
        "indexed_files": 95,
        "failed_files": 5,
        "index_size": 1024000,
        "last_updated": "2024-01-01T12:00:00",
        "status": "completed",
    }


@pytest.fixture
def sample_progress_data() -> dict[str, Any]:
    """サンプル進捗データ"""
    return {
        "current": 50,
        "total": 100,
        "percentage": 50.0,
        "message": "処理中...",
        "elapsed_time": 30.5,
        "estimated_remaining": 30.5,
    }


@pytest.fixture
def sample_error_data() -> dict[str, Any]:
    """サンプルエラーデータ"""
    return {
        "error_type": "FileNotFoundError",
        "error_message": "ファイルが見つかりません",
        "file_path": "/test/missing_file.txt",
        "timestamp": "2024-01-01T12:00:00",
        "stack_trace": "Traceback (most recent call last)...",
    }


@pytest.fixture
def sample_settings_data() -> dict[str, Any]:
    """サンプル設定データ"""
    return {
        "search_type": "hybrid",
        "max_results": 50,
        "enable_preview": True,
        "theme": "light",
        "language": "ja",
        "auto_index": True,
        "index_extensions": [".txt", ".pdf", ".docx", ".md"],
    }


@pytest.fixture
def mock_file_paths() -> list[Path]:
    """モックファイルパス"""
    return [
        Path("/test/file1.txt"),
        Path("/test/file2.pdf"),
        Path("/test/file3.docx"),
        Path("/test/folder1"),
        Path("/test/folder2"),
    ]


@pytest.fixture
def empty_search_result() -> dict[str, Any]:
    """空の検索結果"""
    return {
        "success": True,
        "results": [],
        "total_count": 0,
        "query": "",
        "search_time": 0.0,
    }


@pytest.fixture
def failed_search_result() -> dict[str, Any]:
    """失敗した検索結果"""
    return {
        "success": False,
        "results": [],
        "total_count": 0,
        "query": "test query",
        "error": "検索に失敗しました",
        "search_time": 0.0,
    }


@pytest.fixture
def sample_ui_state() -> dict[str, Any]:
    """サンプルUI状態"""
    return {
        "window_geometry": {"x": 100, "y": 100, "width": 800, "height": 600},
        "splitter_sizes": [200, 400, 200],
        "selected_folder": "/test/documents",
        "search_query": "test query",
        "search_type": "fulltext",
        "show_preview": True,
    }
