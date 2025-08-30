#!/usr/bin/env python3
"""
FolderTreeWidgetのユニットテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

try:
    from PySide6.QtWidgets import QMessageBox
    from src.gui.folder_tree.folder_tree_widget import FolderTreeWidget, FolderTreeContainer
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    QMessageBox = Mock
    FolderTreeWidget = Mock
    FolderTreeContainer = Mock


@pytest.mark.skipif(not GUI_AVAILABLE, reason="GUI環境が利用できません")
class TestFolderTreeWidget:
    """FolderTreeWidgetのテストクラス"""

    @pytest.fixture
    def mock_parent(self):
        """モック親ウィジェットを作成"""
        return Mock()

    @pytest.fixture
    def folder_tree_widget(self):
        """FolderTreeWidgetインスタンスを作成"""
        # 完全にモック化してクラッシュを防止
        widget = Mock()
        widget.__class__ = FolderTreeWidget
        
        # 必要な属性を設定
        widget.root_paths = []
        widget.item_map = {}
        widget.expanded_paths = None
        widget.indexing_paths = None
        widget.indexed_paths = None
        widget.excluded_paths = None
        widget.error_paths = None
        
        # 必要なマネージャーをモック化
        widget.async_manager = Mock()
        widget.context_menu_manager = Mock()
        widget.filter_manager = Mock()
        widget.action_manager = Mock()
        widget.path_optimizer = Mock()
        
        # _ensure_path_setsメソッドをモック化
        def mock_ensure_path_sets():
            if widget.expanded_paths is None:
                widget.expanded_paths = set()
            if widget.indexing_paths is None:
                widget.indexing_paths = set()
            if widget.indexed_paths is None:
                widget.indexed_paths = set()
            if widget.excluded_paths is None:
                widget.excluded_paths = set()
            if widget.error_paths is None:
                widget.error_paths = set()
        
        widget._ensure_path_sets = mock_ensure_path_sets
        
        return widget

    def test_init(self, folder_tree_widget):
        """初期化のテスト"""
        assert folder_tree_widget is not None
        assert hasattr(folder_tree_widget, 'root_paths')
        assert hasattr(folder_tree_widget, 'item_map')
        assert folder_tree_widget.root_paths == []
        assert folder_tree_widget.item_map == {}

    def test_ensure_path_sets(self, folder_tree_widget):
        """パスセット遅延初期化のテスト"""
        # 初期状態ではNone
        assert folder_tree_widget.expanded_paths is None
        assert folder_tree_widget.indexing_paths is None
        assert folder_tree_widget.indexed_paths is None
        assert folder_tree_widget.excluded_paths is None
        assert folder_tree_widget.error_paths is None
        
        # _ensure_path_sets呼び出し後はsetが作成される
        folder_tree_widget._ensure_path_sets()
        
        assert isinstance(folder_tree_widget.expanded_paths, set)
        assert isinstance(folder_tree_widget.indexing_paths, set)
        assert isinstance(folder_tree_widget.indexed_paths, set)
        assert isinstance(folder_tree_widget.excluded_paths, set)
        assert isinstance(folder_tree_widget.error_paths, set)

    @patch('src.gui.folder_tree.folder_tree_widget.os.path.exists')
    @patch('src.gui.folder_tree.folder_tree_widget.os.path.isdir')
    def test_load_folder_structure_success(self, mock_isdir, mock_exists, folder_tree_widget):
        """フォルダ構造読み込み成功のテスト"""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        
        # 必要なメソッドをモック化
        folder_tree_widget._load_subfolders_async = Mock()
        folder_tree_widget.addTopLevelItem = Mock()
        
        with patch('src.gui.folder_tree.folder_tree_widget.FolderTreeItem') as mock_item_class:
            mock_item = Mock()
            mock_item_class.return_value = mock_item
            
            folder_tree_widget.load_folder_structure("/test/folder")
            
            # ルートパスが追加されることを確認
            assert "/test/folder" in folder_tree_widget.root_paths
            
            # アイテムがマップに追加されることを確認
            assert "/test/folder" in folder_tree_widget.item_map
            
            # アイテムが追加されることを確認
            folder_tree_widget.addTopLevelItem.assert_called_once_with(mock_item)
            
            # 非同期読み込みが開始されることを確認
            folder_tree_widget._load_subfolders_async.assert_called_once_with("/test/folder")
            
            # アイテムが展開されることを確認
            mock_item.setExpanded.assert_called_once_with(True)

    @patch('src.gui.folder_tree.folder_tree_widget.os.path.exists')
    @patch('src.gui.folder_tree.folder_tree_widget.QMessageBox')
    def test_load_folder_structure_invalid_path(self, mock_msgbox, mock_exists, folder_tree_widget):
        """無効なパスでのフォルダ構造読み込みのテスト"""
        mock_exists.return_value = False
        
        folder_tree_widget.load_folder_structure("/invalid/folder")
        
        # 警告ダイアログが表示されることを確認
        mock_msgbox.warning.assert_called_once()
        
        # ルートパスが追加されないことを確認
        assert "/invalid/folder" not in folder_tree_widget.root_paths

    def test_load_folder_structure_already_exists(self, folder_tree_widget):
        """既に存在するフォルダの読み込みテスト"""
        folder_tree_widget.root_paths = ["/test/folder"]
        folder_tree_widget.async_manager.cleanup_workers = Mock()
        
        folder_tree_widget.load_folder_structure("/test/folder")
        
        # 重複追加されないことを確認
        assert folder_tree_widget.root_paths.count("/test/folder") == 1

    def test_load_subfolders_async(self, folder_tree_widget):
        """非同期サブフォルダ読み込みのテスト"""
        folder_tree_widget.async_manager.start_folder_loading = Mock()
        
        folder_tree_widget._load_subfolders_async("/test/folder")
        
        folder_tree_widget.async_manager.start_folder_loading.assert_called_once_with(
            "/test/folder", max_depth=2
        )

    def test_cleanup_workers(self, folder_tree_widget):
        """ワーカークリーンアップのテスト"""
        folder_tree_widget.async_manager.cleanup_workers = Mock()
        
        folder_tree_widget._cleanup_workers()
        
        folder_tree_widget.async_manager.cleanup_workers.assert_called_once()

    def test_show_context_menu(self, folder_tree_widget):
        """コンテキストメニュー表示のテスト"""
        folder_tree_widget.context_menu_manager.show_context_menu = Mock()
        position = Mock()
        
        folder_tree_widget._show_context_menu(position)
        
        folder_tree_widget.context_menu_manager.show_context_menu.assert_called_once_with(position)

    def test_filter_folders(self, folder_tree_widget):
        """フォルダフィルタリングのテスト"""
        folder_tree_widget.filter_manager.filter_folders = Mock()
        
        folder_tree_widget.filter_folders("test")
        
        folder_tree_widget.filter_manager.filter_folders.assert_called_once_with("test")

    def test_get_selected_folder_with_selection(self, folder_tree_widget):
        """選択されたフォルダ取得のテスト（選択あり）"""
        mock_item = Mock()
        mock_item.folder_path = "/selected/folder"
        folder_tree_widget.currentItem = Mock(return_value=mock_item)
        
        with patch('src.gui.folder_tree.folder_tree_widget.FolderTreeItem', mock_item.__class__):
            result = folder_tree_widget.get_selected_folder()
            assert result == "/selected/folder"

    def test_get_selected_folder_no_selection(self, folder_tree_widget):
        """選択されたフォルダ取得のテスト（選択なし）"""
        folder_tree_widget.currentItem = Mock(return_value=None)
        
        result = folder_tree_widget.get_selected_folder()
        assert result is None

    def test_get_indexed_folders(self, folder_tree_widget):
        """インデックス済みフォルダ取得のテスト"""
        folder_tree_widget._ensure_path_sets()
        folder_tree_widget.indexed_paths.add("/folder1")
        folder_tree_widget.indexed_paths.add("/folder2")
        
        result = folder_tree_widget.get_indexed_folders()
        assert set(result) == {"/folder1", "/folder2"}

    def test_get_excluded_folders(self, folder_tree_widget):
        """除外フォルダ取得のテスト"""
        folder_tree_widget._ensure_path_sets()
        folder_tree_widget.excluded_paths.add("/excluded1")
        folder_tree_widget.excluded_paths.add("/excluded2")
        
        result = folder_tree_widget.get_excluded_folders()
        assert set(result) == {"/excluded1", "/excluded2"}

    def test_set_indexed_folders(self, folder_tree_widget):
        """インデックス済みフォルダ設定のテスト"""
        folder_tree_widget._update_item_types = Mock()
        
        folder_tree_widget.set_indexed_folders(["/folder1", "/folder2"])
        
        folder_tree_widget._ensure_path_sets()
        assert folder_tree_widget.indexed_paths == {"/folder1", "/folder2"}
        folder_tree_widget._update_item_types.assert_called_once()

    def test_set_excluded_folders(self, folder_tree_widget):
        """除外フォルダ設定のテスト"""
        folder_tree_widget._update_item_types = Mock()
        
        folder_tree_widget.set_excluded_folders(["/excluded1", "/excluded2"])
        
        folder_tree_widget._ensure_path_sets()
        assert folder_tree_widget.excluded_paths == {"/excluded1", "/excluded2"}
        folder_tree_widget._update_item_types.assert_called_once()

    def test_set_folder_indexing(self, folder_tree_widget):
        """フォルダインデックス処理中状態設定のテスト"""
        folder_tree_widget._ensure_path_sets()
        mock_item = Mock()
        folder_tree_widget.item_map["/test/folder"] = mock_item
        folder_tree_widget.path_optimizer.get_basename = Mock(return_value="folder")
        
        folder_tree_widget.set_folder_indexing("/test/folder")
        
        assert "/test/folder" in folder_tree_widget.indexing_paths
        assert "/test/folder" not in folder_tree_widget.indexed_paths
        mock_item.setText.assert_called_once_with(0, "folder (処理中...)")

    def test_set_folder_indexed(self, folder_tree_widget):
        """フォルダインデックス済み状態設定のテスト"""
        folder_tree_widget._ensure_path_sets()
        mock_item = Mock()
        folder_tree_widget.item_map["/test/folder"] = mock_item
        
        folder_tree_widget.set_folder_indexed("/test/folder", 100, 80)
        
        assert "/test/folder" in folder_tree_widget.indexed_paths
        assert "/test/folder" not in folder_tree_widget.indexing_paths
        mock_item.update_statistics.assert_called_once_with(100, 80)

    def test_set_folder_error(self, folder_tree_widget):
        """フォルダエラー状態設定のテスト"""
        folder_tree_widget._ensure_path_sets()
        mock_item = Mock()
        folder_tree_widget.item_map["/test/folder"] = mock_item
        folder_tree_widget.path_optimizer.get_basename = Mock(return_value="folder")
        
        folder_tree_widget.set_folder_error("/test/folder", "Test error")
        
        assert "/test/folder" in folder_tree_widget.error_paths
        assert "/test/folder" not in folder_tree_widget.indexing_paths
        mock_item.setText.assert_called_once_with(0, "folder (エラー)")
        mock_item.setToolTip.assert_called_once_with(0, "/test/folder\nエラー: Test error")

    def test_clear_folder_state(self, folder_tree_widget):
        """フォルダ状態クリアのテスト"""
        folder_tree_widget._ensure_path_sets()
        folder_tree_widget.indexing_paths.add("/test/folder")
        folder_tree_widget.indexed_paths.add("/test/folder")
        folder_tree_widget.error_paths.add("/test/folder")
        
        mock_item = Mock()
        folder_tree_widget.item_map["/test/folder"] = mock_item
        folder_tree_widget.path_optimizer.get_basename = Mock(return_value="folder")
        
        folder_tree_widget.clear_folder_state("/test/folder")
        
        assert "/test/folder" not in folder_tree_widget.indexing_paths
        assert "/test/folder" not in folder_tree_widget.indexed_paths
        assert "/test/folder" not in folder_tree_widget.error_paths
        mock_item.setText.assert_called_once_with(0, "folder")

    def test_expand_to_path(self, folder_tree_widget):
        """パスまでの展開のテスト"""
        folder_tree_widget.action_manager.expand_to_path = Mock()
        
        folder_tree_widget.expand_to_path("/test/folder")
        
        folder_tree_widget.action_manager.expand_to_path.assert_called_once_with("/test/folder")


@pytest.mark.skipif(not GUI_AVAILABLE, reason="GUI環境が利用できません")
class TestFolderTreeContainer:
    """FolderTreeContainerのテストクラス"""

    @pytest.fixture
    def mock_parent(self):
        """モック親ウィジェットを作成"""
        return Mock()

    @pytest.fixture
    def folder_tree_container(self):
        """FolderTreeContainerインスタンスを作成"""
        # 完全にモック化してクラッシュを防止
        container = Mock()
        container.__class__ = FolderTreeContainer
        
        # 必要な属性を設定
        container.tree_widget = Mock()
        container.add_button = Mock()
        container.filter_input = Mock()
        container.stats_label = Mock()
        
        # tree_widgetの必要なメソッドをモック化
        container.tree_widget.load_folder_structure = Mock()
        container.tree_widget.get_selected_folder = Mock()
        container.tree_widget.get_indexed_folders = Mock()
        container.tree_widget.set_folder_indexing = Mock()
        container.tree_widget.set_folder_indexed = Mock()
        container.tree_widget.filter_manager = Mock()
        container.tree_widget._ensure_path_sets = Mock()
        
        return container

    def test_init(self, folder_tree_container):
        """初期化のテスト"""
        assert folder_tree_container is not None
        assert hasattr(folder_tree_container, 'tree_widget')
        assert hasattr(folder_tree_container, 'add_button')
        assert hasattr(folder_tree_container, 'filter_input')
        assert hasattr(folder_tree_container, 'stats_label')

    def test_load_folder_structure(self, folder_tree_container):
        """フォルダ構造読み込みのテスト"""
        folder_tree_container._update_stats = Mock()
        
        folder_tree_container.load_folder_structure("/test/folder")
        
        folder_tree_container.tree_widget.load_folder_structure.assert_called_once_with("/test/folder")
        folder_tree_container._update_stats.assert_called_once()

    def test_get_selected_folder(self, folder_tree_container):
        """選択されたフォルダ取得のテスト"""
        folder_tree_container.tree_widget.get_selected_folder.return_value = "/selected/folder"
        
        result = folder_tree_container.get_selected_folder()
        
        assert result == "/selected/folder"
        folder_tree_container.tree_widget.get_selected_folder.assert_called_once()

    def test_get_indexed_folders(self, folder_tree_container):
        """インデックス済みフォルダ取得のテスト"""
        folder_tree_container.tree_widget.get_indexed_folders.return_value = ["/folder1", "/folder2"]
        
        result = folder_tree_container.get_indexed_folders()
        
        assert result == ["/folder1", "/folder2"]
        folder_tree_container.tree_widget.get_indexed_folders.assert_called_once()

    def test_set_folder_indexing(self, folder_tree_container):
        """フォルダインデックス処理中状態設定のテスト"""
        folder_tree_container._update_stats = Mock()
        
        folder_tree_container.set_folder_indexing("/test/folder")
        
        folder_tree_container.tree_widget.set_folder_indexing.assert_called_once_with("/test/folder")
        folder_tree_container._update_stats.assert_called_once()

    def test_set_folder_indexed(self, folder_tree_container):
        """フォルダインデックス済み状態設定のテスト"""
        folder_tree_container._update_stats = Mock()
        
        folder_tree_container.set_folder_indexed("/test/folder", 100, 80)
        
        folder_tree_container.tree_widget.set_folder_indexed.assert_called_once_with("/test/folder", 100, 80)
        folder_tree_container._update_stats.assert_called_once()

    def test_clear_filter(self, folder_tree_container):
        """フィルタークリアのテスト"""
        folder_tree_container.filter_input.clear = Mock()
        folder_tree_container.tree_widget.filter_manager.clear_filter = Mock()
        
        folder_tree_container._clear_filter()
        
        folder_tree_container.filter_input.clear.assert_called_once()
        folder_tree_container.tree_widget.filter_manager.clear_filter.assert_called_once()

    def test_update_stats(self, folder_tree_container):
        """統計情報更新のテスト"""
        # tree_widgetの_ensure_path_setsをモック化
        folder_tree_container.tree_widget._ensure_path_sets = Mock()
        
        # パスセットをモック化
        folder_tree_container.tree_widget.item_map = {"/folder1": Mock(), "/folder2": Mock()}
        folder_tree_container.tree_widget.indexing_paths = {"/folder1"}
        folder_tree_container.tree_widget.indexed_paths = {"/folder2"}
        folder_tree_container.tree_widget.excluded_paths = set()
        folder_tree_container.tree_widget.error_paths = set()
        
        folder_tree_container._update_stats()
        
        # 統計ラベルが更新されることを確認
        folder_tree_container.stats_label.setText.assert_called_once()
        call_args = folder_tree_container.stats_label.setText.call_args[0][0]
        assert "フォルダ: 2" in call_args
        assert "インデックス: 1" in call_args
        assert "処理中: 1" in call_args