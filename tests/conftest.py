"""
テスト共通設定 - pytest設定とフィクスチャ
"""
import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Qt環境設定
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_LOGGING_RULES'] = '*.debug=false'

@pytest.fixture(scope="session")
def qapp():
    """セッション全体で共有するQApplication"""
    try:
        from PySide6.QtWidgets import QApplication

        # 既存のアプリケーションインスタンスをチェック
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
            app.setQuitOnLastWindowClosed(False)
            created_new = True
        else:
            created_new = False

        yield app

        # 新しく作成した場合のみクリーンアップ
        if created_new and app:
            app.processEvents()
            app.quit()
    except ImportError:
        # PySide6が利用できない場合はNoneを返す
        yield None

# pytest-qtのqtbotフィクスチャを使用し、独自の定義は削除

@pytest.fixture
def temp_config_dir(tmp_path):
    """一時設定ディレクトリ"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return str(config_dir)

@pytest.fixture
def sample_text_file(tmp_path):
    """サンプルテキストファイル"""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("これはサンプルテキストファイルです。\n検索テスト用の内容が含まれています。")
    return str(file_path)

@pytest.fixture
def mock_search_manager():
    """検索マネージャーのモック"""
    manager = Mock()
    manager.search.return_value = [
        {"title": "テストドキュメント1", "content": "テスト内容1"},
        {"title": "テストドキュメント2", "content": "テスト内容2"}
    ]
    return manager

@pytest.fixture
def mock_index_manager():
    """インデックスマネージャーのモック"""
    manager = Mock()
    manager.create_index.return_value = Mock(success=True)
    manager.add_document.return_value = Mock(success=True)
    manager.document_count.return_value = 10
    return manager
