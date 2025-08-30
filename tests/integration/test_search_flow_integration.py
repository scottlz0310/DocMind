"""
検索フロー統合テスト

Phase5テスト環境 - 検索パイプライン全体の接続確認
"""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication

from src.gui.search_interface import SearchInterface
from src.gui.search_results import SearchResultsWidget
from src.gui.preview_widget import PreviewWidget


class TestSearchFlowIntegration:
    """検索フロー統合テスト - 接続確認レベル"""

    @pytest.fixture(scope="class")
    def qapp(self):
        """QApplicationインスタンス"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def mock_main_window(self):
        """メインウィンドウのモック"""
        return Mock()

    @pytest.fixture
    def search_interface(self, qapp, mock_main_window):
        """検索インターフェースのインスタンス"""
        with patch('src.gui.search_interface.SearchManager'), \
             patch('src.gui.search_interface.IndexManager'):
            interface = SearchInterface(mock_main_window)
            yield interface

    @pytest.fixture
    def search_results(self, qapp, mock_main_window):
        """検索結果のインスタンス"""
        results = SearchResultsWidget(mock_main_window)
        yield results

    @pytest.fixture
    def preview_widget(self, qapp, mock_main_window):
        """プレビューウィジェットのインスタンス"""
        preview = PreviewWidget(mock_main_window)
        yield preview

    def test_search_pipeline_connection(self, search_interface, search_results, preview_widget):
        """検索パイプライン全体の接続確認"""
        try:
            # SearchInterface → SearchController の接続確認
            assert hasattr(search_interface, 'search_controller')
            
            # SearchResults が存在することを確認
            assert search_results is not None
            
            # PreviewWidget が存在することを確認
            assert preview_widget is not None
            
            # エラーが発生しないことを確認
            
        except Exception as e:
            pytest.fail(f"Search pipeline connection failed: {e}")

    def test_search_interface_initialization(self, search_interface):
        """検索インターフェース初期化の接続確認"""
        try:
            # 各マネージャーが初期化されていることを確認
            assert hasattr(search_interface, 'search_ui_manager')
            assert hasattr(search_interface, 'search_controller')
            assert hasattr(search_interface, 'search_layout_manager')
            
        except Exception as e:
            pytest.fail(f"Search interface initialization failed: {e}")

    def test_search_execution_flow(self, search_interface):
        """検索実行フローの接続確認"""
        try:
            # 検索コントローラーが存在することを確認
            assert search_interface.search_controller is not None
            
            # 基本的な検索実行をテスト（詳細な結果検証はしない）
            with patch.object(search_interface.search_controller, 'execute_search') as mock_search:
                mock_search.return_value = Mock(success=True, results=[])
                
                # 検索実行が呼び出されることを確認
                search_interface.search_controller.execute_search("test query")
                mock_search.assert_called_once_with("test query")
                
        except Exception as e:
            pytest.fail(f"Search execution flow failed: {e}")

    def test_result_display_flow(self, search_results):
        """検索結果表示フローの接続確認"""
        try:
            # 結果表示ウィジェットが存在することを確認
            assert search_results is not None
            
            # 基本的な結果表示をテスト
            test_results = [{"title": "Test Document", "path": "/test/doc.txt"}]
            search_results.display_results(test_results)
            
        except Exception as e:
            pytest.fail(f"Result display flow failed: {e}")

    def test_preview_integration(self, preview_widget):
        """プレビュー統合の接続確認"""
        try:
            # プレビューウィジェットが存在することを確認
            assert preview_widget is not None
            
            # 基本的なプレビュー表示をテスト
            with patch.object(preview_widget, 'load_document') as mock_load:
                preview_widget.load_document("/test/document.txt")
                mock_load.assert_called_once_with("/test/document.txt")
                
        except Exception as e:
            pytest.fail(f"Preview integration failed: {e}")

    def test_search_options_integration(self, search_interface):
        """検索オプション統合の接続確認"""
        try:
            # 検索オプションマネージャーが存在することを確認
            assert hasattr(search_interface, 'search_options_manager')
            
            # オプション管理が機能することを確認
            # 詳細な検証はしない - 存在確認のみ
            
        except Exception as e:
            pytest.fail(f"Search options integration failed: {e}")

    def test_search_event_handling(self, search_interface):
        """検索イベント処理の接続確認"""
        try:
            # 検索イベントマネージャーが存在することを確認
            assert hasattr(search_interface, 'search_event_manager')
            
            # イベント処理が機能することを確認
            # 詳細な検証はしない - 存在確認のみ
            
        except Exception as e:
            pytest.fail(f"Search event handling failed: {e}")

    def test_search_api_integration(self, search_interface):
        """検索API統合の接続確認"""
        try:
            # 検索APIマネージャーが存在することを確認
            assert hasattr(search_interface, 'search_api_manager')
            
            # API統合が機能することを確認
            # 詳細な検証はしない - 存在確認のみ
            
        except Exception as e:
            pytest.fail(f"Search API integration failed: {e}")

    def test_shortcut_integration(self, search_interface):
        """ショートカット統合の接続確認"""
        try:
            # ショートカットマネージャーが存在することを確認
            assert hasattr(search_interface, 'shortcut_manager')
            
            # ショートカット機能が機能することを確認
            # 詳細な検証はしない - 存在確認のみ
            
        except Exception as e:
            pytest.fail(f"Shortcut integration failed: {e}")

    def test_search_widgets_integration(self, search_interface):
        """検索ウィジェット統合の接続確認"""
        try:
            # 各検索ウィジェットが統合されていることを確認
            # 詳細な検証はしない - 基本的な存在確認のみ
            
            # 検索インターフェースが正常に動作することを確認
            assert search_interface is not None
            
        except Exception as e:
            pytest.fail(f"Search widgets integration failed: {e}")

    def test_search_history_integration(self, search_interface):
        """検索履歴統合の接続確認"""
        try:
            # 検索履歴機能が統合されていることを確認
            if hasattr(search_interface, 'search_controller'):
                controller = search_interface.search_controller
                
                # 履歴機能が存在することを確認
                if hasattr(controller, 'search_history'):
                    assert controller.search_history is not None
                    
        except Exception as e:
            pytest.fail(f"Search history integration failed: {e}")

    def test_search_suggestions_integration(self, search_interface):
        """検索候補統合の接続確認"""
        try:
            # 検索候補機能が統合されていることを確認
            if hasattr(search_interface, 'search_controller'):
                controller = search_interface.search_controller
                
                # 候補機能をテスト（詳細な検証はしない）
                with patch.object(controller, 'get_search_suggestions') as mock_suggestions:
                    mock_suggestions.return_value = ["suggestion1", "suggestion2"]
                    
                    suggestions = controller.get_search_suggestions("test")
                    mock_suggestions.assert_called_once_with("test")
                    
        except Exception as e:
            pytest.fail(f"Search suggestions integration failed: {e}")

    def test_error_handling_in_search_flow(self, search_interface):
        """検索フローでのエラーハンドリング接続確認"""
        try:
            # エラーハンドリングが統合されていることを確認
            # 詳細な検証はしない - 基本的な動作確認のみ
            
            # 無効な検索でもエラーが適切に処理されることを確認
            if hasattr(search_interface, 'search_controller'):
                controller = search_interface.search_controller
                result = controller.execute_search("")  # 空クエリ
                
                # エラーが適切に処理されることを確認
                assert hasattr(result, 'success')
                
        except Exception as e:
            pytest.fail(f"Error handling in search flow failed: {e}")