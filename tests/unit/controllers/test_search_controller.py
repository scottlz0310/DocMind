"""
検索コントローラーのユニットテスト

Phase5テスト環境 - 実際のコードに合わせて修正
"""

import pytest
from unittest.mock import Mock, patch

try:
    from PySide6.QtWidgets import QApplication
    from src.gui.search.controllers.search_controller import SearchController
    from src.data.models import SearchType
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    SearchController = Mock
    SearchType = Mock


@pytest.mark.skipif(not GUI_AVAILABLE, reason="GUI環境が利用できません")
class TestSearchController:
    """検索コントローラーのテスト"""

    @pytest.fixture
    def qapp(self):
        """QApplicationインスタンス"""
        if not GUI_AVAILABLE:
            return None
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def search_controller(self, qapp):
        """検索コントローラーのインスタンス"""
        return SearchController()

    def test_initialization(self, search_controller):
        """初期化テスト"""
        assert hasattr(search_controller, 'is_searching')
        assert search_controller.is_searching is False

    def test_execute_search_success(self, search_controller):
        """検索実行成功テスト"""
        query = "test query"
        search_type = SearchType.FULL_TEXT
        options = {"limit": 10}
        
        with patch.object(search_controller, 'search_requested') as mock_signal:
            search_controller.execute_search(query, search_type, options)
            mock_signal.emit.assert_called_once()

    def test_execute_search_empty_query(self, search_controller):
        """空クエリ検索テスト"""
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            search_controller.execute_search("", SearchType.FULL_TEXT, {})
            mock_warning.assert_called_once()

    def test_cancel_search(self, search_controller):
        """検索キャンセルテスト"""
        search_controller.is_searching = True
        
        with patch.object(search_controller, 'search_cancelled') as mock_signal:
            search_controller.cancel_search()
            mock_signal.emit.assert_called_once()
            assert search_controller.is_searching is False

    def test_get_searching_state(self, search_controller):
        """検索状態取得テスト"""
        assert search_controller.get_searching_state() is False
        
        search_controller.is_searching = True
        assert search_controller.get_searching_state() is True

    def test_on_search_completed(self, search_controller):
        """検索完了処理テスト"""
        search_controller.is_searching = True
        results = [{"title": "Test"}]
        
        search_controller.on_search_completed(results, 1.5)
        assert search_controller.is_searching is False

    def test_on_search_error(self, search_controller):
        """検索エラー処理テスト"""
        search_controller.is_searching = True
        
        with patch('PySide6.QtWidgets.QMessageBox.critical') as mock_critical:
            search_controller.on_search_error("Test error")
            mock_critical.assert_called_once()
            assert search_controller.is_searching is False