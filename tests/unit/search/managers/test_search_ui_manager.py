#!/usr/bin/env python3
"""
SearchUIManagerのユニットテスト
"""

import pytest
from unittest.mock import Mock, patch

from src.gui.search.managers.search_ui_manager import SearchUIManager
from src.data.models import SearchType


class TestSearchUIManager:
    """SearchUIManagerのテストクラス"""

    @pytest.fixture
    def search_ui_manager(self):
        """SearchUIManagerインスタンスを作成"""
        return SearchUIManager()

    @pytest.fixture
    def mock_search_button(self):
        """モック検索ボタンを作成"""
        mock_button = Mock()
        mock_button.setEnabled = Mock()
        mock_button.setText = Mock()
        return mock_button

    @pytest.fixture
    def mock_search_input(self):
        """モック検索入力を作成"""
        mock_input = Mock()
        mock_input.update_suggestions = Mock()
        mock_input.clear = Mock()
        mock_input.setFocus = Mock()
        mock_input.setEnabled = Mock()
        return mock_input

    @pytest.fixture
    def mock_history_widget(self):
        """モック履歴ウィジェットを作成"""
        mock_widget = Mock()
        mock_widget.update_recent_searches = Mock()
        mock_widget.update_popular_searches = Mock()
        mock_widget.update_saved_searches = Mock()
        return mock_widget

    @pytest.fixture
    def mock_advanced_options(self):
        """モック高度なオプションを作成"""
        mock_options = Mock()
        mock_options.reset_to_defaults = Mock()
        mock_options.setEnabled = Mock()
        mock_options.findChild = Mock()
        return mock_options

    @pytest.fixture
    def mock_progress_widget(self):
        """モック進捗ウィジェットを作成"""
        mock_widget = Mock()
        mock_widget.finish_search = Mock()
        return mock_widget

    def test_init(self):
        """初期化のテスト"""
        manager = SearchUIManager()
        assert manager is not None
        assert hasattr(manager, 'logger')

    def test_init_with_parent(self):
        """親ウィジェット付き初期化のテスト"""
        # QObjectの親として使用するため、Noneを使用
        manager = SearchUIManager(None)
        assert manager is not None

    def test_update_search_button_state_searching(self, search_ui_manager, mock_search_button):
        """検索中の検索ボタン状態更新のテスト"""
        search_ui_manager.update_search_button_state(mock_search_button, True)
        
        mock_search_button.setEnabled.assert_called_once_with(False)
        mock_search_button.setText.assert_called_once_with("検索中...")

    def test_update_search_button_state_not_searching(self, search_ui_manager, mock_search_button):
        """非検索中の検索ボタン状態更新のテスト"""
        search_ui_manager.update_search_button_state(mock_search_button, False)
        
        mock_search_button.setEnabled.assert_called_once_with(True)
        mock_search_button.setText.assert_called_once_with("検索")

    def test_update_search_suggestions(self, search_ui_manager, mock_search_input):
        """検索提案更新のテスト"""
        suggestions = ["suggestion1", "suggestion2", "suggestion3"]
        
        search_ui_manager.update_search_suggestions(mock_search_input, suggestions)
        
        mock_search_input.update_suggestions.assert_called_once_with(suggestions)

    def test_update_search_history_with_all_params(self, search_ui_manager, mock_history_widget):
        """すべてのパラメータ付き検索履歴更新のテスト"""
        recent_searches = [{"query": "recent1"}, {"query": "recent2"}]
        popular_searches = [{"query": "popular1"}, {"query": "popular2"}]
        saved_searches = [{"query": "saved1"}, {"query": "saved2"}]
        
        search_ui_manager.update_search_history(
            mock_history_widget, recent_searches, popular_searches, saved_searches
        )
        
        mock_history_widget.update_recent_searches.assert_called_once_with(recent_searches)
        mock_history_widget.update_popular_searches.assert_called_once_with(popular_searches)
        mock_history_widget.update_saved_searches.assert_called_once_with(saved_searches)

    def test_update_search_history_without_saved(self, search_ui_manager, mock_history_widget):
        """保存された検索なしの検索履歴更新のテスト"""
        recent_searches = [{"query": "recent1"}]
        popular_searches = [{"query": "popular1"}]
        
        search_ui_manager.update_search_history(
            mock_history_widget, recent_searches, popular_searches
        )
        
        mock_history_widget.update_recent_searches.assert_called_once_with(recent_searches)
        mock_history_widget.update_popular_searches.assert_called_once_with(popular_searches)
        mock_history_widget.update_saved_searches.assert_not_called()

    def test_set_interface_enabled_true(self, search_ui_manager, mock_search_input, 
                                       mock_search_button, mock_advanced_options):
        """インターフェース有効化のテスト"""
        mock_search_type_selector = Mock()
        mock_search_type_selector.setEnabled = Mock()
        
        search_ui_manager.set_interface_enabled(
            mock_search_input, mock_search_button, mock_search_type_selector, 
            mock_advanced_options, True
        )
        
        mock_search_input.setEnabled.assert_called_once_with(True)
        mock_search_button.setEnabled.assert_called_once_with(True)
        mock_search_type_selector.setEnabled.assert_called_once_with(True)
        mock_advanced_options.setEnabled.assert_called_once_with(True)

    def test_set_interface_enabled_false(self, search_ui_manager, mock_search_input, 
                                        mock_search_button, mock_advanced_options):
        """インターフェース無効化のテスト"""
        mock_search_type_selector = Mock()
        mock_search_type_selector.setEnabled = Mock()
        
        search_ui_manager.set_interface_enabled(
            mock_search_input, mock_search_button, mock_search_type_selector, 
            mock_advanced_options, False
        )
        
        mock_search_input.setEnabled.assert_called_once_with(False)
        mock_search_button.setEnabled.assert_called_once_with(False)
        mock_search_type_selector.setEnabled.assert_called_once_with(False)
        mock_advanced_options.setEnabled.assert_called_once_with(False)

    def test_set_interface_enabled_searching(self, search_ui_manager, mock_search_input, 
                                            mock_search_button, mock_advanced_options):
        """検索中のインターフェース状態のテスト"""
        mock_search_type_selector = Mock()
        mock_search_type_selector.setEnabled = Mock()
        
        search_ui_manager.set_interface_enabled(
            mock_search_input, mock_search_button, mock_search_type_selector, 
            mock_advanced_options, True, is_searching=True
        )
        
        mock_search_input.setEnabled.assert_called_once_with(True)
        mock_search_button.setEnabled.assert_called_once_with(False)  # 検索中は無効
        mock_search_type_selector.setEnabled.assert_called_once_with(True)
        mock_advanced_options.setEnabled.assert_called_once_with(True)

    def test_clear_search_interface(self, search_ui_manager, mock_search_input, 
                                   mock_advanced_options, mock_progress_widget):
        """検索インターフェースクリアのテスト"""
        search_ui_manager.clear_search_interface(
            mock_search_input, mock_advanced_options, mock_progress_widget
        )
        
        mock_search_input.clear.assert_called_once()
        mock_search_input.setFocus.assert_called_once()
        mock_advanced_options.reset_to_defaults.assert_called_once()
        mock_progress_widget.finish_search.assert_called_once_with("")

    def test_handle_search_type_change_hybrid(self, search_ui_manager, mock_advanced_options):
        """ハイブリッド検索タイプ変更のテスト"""
        mock_weights_group = Mock()
        mock_weights_group.setEnabled = Mock()
        mock_advanced_options.findChild.return_value = mock_weights_group
        
        search_ui_manager.handle_search_type_change(SearchType.HYBRID, mock_advanced_options)
        
        mock_advanced_options.findChild.assert_called_once()
        mock_weights_group.setEnabled.assert_called_once_with(True)

    def test_handle_search_type_change_fulltext(self, search_ui_manager, mock_advanced_options):
        """全文検索タイプ変更のテスト"""
        mock_weights_group = Mock()
        mock_weights_group.setEnabled = Mock()
        mock_advanced_options.findChild.return_value = mock_weights_group
        
        search_ui_manager.handle_search_type_change(SearchType.FULL_TEXT, mock_advanced_options)
        
        mock_advanced_options.findChild.assert_called_once()
        mock_weights_group.setEnabled.assert_called_once_with(False)

    def test_handle_search_type_change_semantic(self, search_ui_manager, mock_advanced_options):
        """セマンティック検索タイプ変更のテスト"""
        mock_weights_group = Mock()
        mock_weights_group.setEnabled = Mock()
        mock_advanced_options.findChild.return_value = mock_weights_group
        
        search_ui_manager.handle_search_type_change(SearchType.SEMANTIC, mock_advanced_options)
        
        mock_advanced_options.findChild.assert_called_once()
        mock_weights_group.setEnabled.assert_called_once_with(False)

    def test_handle_search_type_change_no_weights_group(self, search_ui_manager, mock_advanced_options):
        """重み設定グループが存在しない場合のテスト"""
        mock_advanced_options.findChild.return_value = None
        
        # エラーが発生しないことを確認
        search_ui_manager.handle_search_type_change(SearchType.HYBRID, mock_advanced_options)
        
        mock_advanced_options.findChild.assert_called_once()

    def test_update_search_suggestions_empty_list(self, search_ui_manager, mock_search_input):
        """空の提案リストのテスト"""
        suggestions = []
        
        search_ui_manager.update_search_suggestions(mock_search_input, suggestions)
        
        mock_search_input.update_suggestions.assert_called_once_with(suggestions)

    def test_update_search_history_empty_lists(self, search_ui_manager, mock_history_widget):
        """空の履歴リストのテスト"""
        recent_searches = []
        popular_searches = []
        saved_searches = []
        
        search_ui_manager.update_search_history(
            mock_history_widget, recent_searches, popular_searches, saved_searches
        )
        
        mock_history_widget.update_recent_searches.assert_called_once_with(recent_searches)
        mock_history_widget.update_popular_searches.assert_called_once_with(popular_searches)
        mock_history_widget.update_saved_searches.assert_called_once_with(saved_searches)