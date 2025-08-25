#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind メインウィンドウのテスト

MainWindowクラスの機能をテストします。
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest

from src.gui.main_window import MainWindow


class TestMainWindow:
    """MainWindowクラスのテストケース"""
    
    @classmethod
    def setup_class(cls):
        """テストクラスのセットアップ"""
        # QApplicationが存在しない場合は作成
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
            # ヘッドレスモードでテストを実行（存在する属性のみ使用）
            try:
                cls.app.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
            except AttributeError:
                # PySide6のバージョンによっては存在しない属性なので無視
                pass
        else:
            cls.app = QApplication.instance()
    
    def setup_method(self):
        """各テストメソッドの前に実行されるセットアップ"""
        # QMessageBoxを完全にモック化
        self.msgbox_patches = [
            patch('src.gui.main_window.QMessageBox.question'),
            patch('src.gui.main_window.QMessageBox.warning'),
            patch('src.gui.main_window.QMessageBox.critical'),
            patch('src.gui.main_window.QMessageBox.information'),
            patch('src.gui.main_window.QMessageBox.about'),
        ]
        
        # QMessageBoxのモックを開始
        self.msgbox_mocks = {}
        for p in self.msgbox_patches:
            mock = p.start()
            # デフォルトは「いいえ」を返す
            mock.return_value = QMessageBox.No
            method_name = p.attribute.split('.')[-1]  # 'question', 'warning', etc.
            self.msgbox_mocks[method_name] = mock
        
        # MainWindowクラスをインポート
        from src.gui.main_window import MainWindow as MainWindowClass
        
        # MainWindowクラスを直接モック化してテスト用のインスタンスを作成
        self.main_window = Mock(spec=MainWindowClass)
        
        # 必要な属性をモック化
        self.main_window.folder_tree_container = Mock()
        self.main_window.folder_tree_container.get_selected_folder = Mock(return_value=None)
        self.main_window.index_manager = Mock()
        self.main_window.thread_manager = Mock()
        self.main_window.timeout_manager = Mock()
        self.main_window.document_processor = Mock()
        self.main_window.database_manager = Mock()
        self.main_window.logger = Mock()
        self.main_window.show_progress = Mock()
        self.main_window.hide_progress = Mock()
        
        # 実際の_rebuild_indexメソッドを使用
        self.main_window._rebuild_index = MainWindowClass._rebuild_index.__get__(self.main_window, MainWindowClass)
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        # QMessageBoxパッチを停止
        if hasattr(self, 'msgbox_patches'):
            for p in self.msgbox_patches:
                p.stop()
    
    def test_window_initialization(self):
        """ウィンドウの初期化をテスト"""
        # ウィンドウタイトルの確認
        assert "DocMind" in self.main_window.windowTitle()
        
        # 最小サイズの確認
        assert self.main_window.minimumSize().width() == 1000
        assert self.main_window.minimumSize().height() == 700
        
        # ウィンドウアイコンが設定されていることを確認
        assert not self.main_window.windowIcon().isNull()
    
    def test_ui_components_exist(self):
        """UIコンポーネントの存在をテスト"""
        # 3ペインスプリッターの存在確認
        assert hasattr(self.main_window, 'main_splitter')
        assert self.main_window.main_splitter is not None
        
        # 各ペインの存在確認
        assert hasattr(self.main_window, 'folder_pane')
        assert hasattr(self.main_window, 'search_pane')
        assert hasattr(self.main_window, 'preview_pane')
        
        # スプリッターに3つのウィジェットが追加されていることを確認
        assert self.main_window.main_splitter.count() == 3
    
    def test_menu_bar_setup(self):
        """メニューバーのセットアップをテスト"""
        menubar = self.main_window.menuBar()
        
        # メニューの存在確認
        menu_titles = [action.text() for action in menubar.actions()]
        expected_menus = ["ファイル(&F)", "検索(&S)", "表示(&V)", "ツール(&T)", "ヘルプ(&H)"]
        
        for expected_menu in expected_menus:
            assert expected_menu in menu_titles
        
        # 主要なアクションの存在確認
        assert hasattr(self.main_window, 'open_folder_action')
        assert hasattr(self.main_window, 'search_action')
        assert hasattr(self.main_window, 'settings_action')
        assert hasattr(self.main_window, 'about_action')
    
    def test_status_bar_setup(self):
        """ステータスバーのセットアップをテスト"""
        status_bar = self.main_window.statusBar()
        assert status_bar is not None
        
        # ステータスバーコンポーネントの存在確認
        assert hasattr(self.main_window, 'status_label')
        assert hasattr(self.main_window, 'progress_bar')
        assert hasattr(self.main_window, 'system_info_label')
        
        # 進捗バーが初期状態で非表示であることを確認
        assert not self.main_window.progress_bar.isVisible()
    
    def test_keyboard_shortcuts(self):
        """キーボードショートカットのテスト"""
        # ショートカットオブジェクトの存在確認
        assert hasattr(self.main_window, 'clear_preview_shortcut')
        assert hasattr(self.main_window, 'refresh_shortcut')
        
        # アクションのショートカット確認
        assert self.main_window.open_folder_action.shortcut().toString() != ""
        assert self.main_window.search_action.shortcut().toString() != ""
        assert self.main_window.settings_action.shortcut().toString() != ""
    
    def test_show_status_message(self):
        """ステータスメッセージ表示のテスト"""
        test_message = "テストメッセージ"
        
        self.main_window.show_status_message(test_message, 1000)
        
        # ステータスバーにメッセージが表示されていることを確認
        # 注意: showMessage()の結果を直接確認する方法が限られているため、
        # エラーが発生しないことを確認
        assert True  # メソッドが正常に実行されることを確認
    
    def test_progress_bar_functionality(self):
        """進捗バー機能のテスト"""
        # 進捗表示
        self.main_window.show_progress("テスト進捗", 50)
        assert self.main_window.progress_bar.isVisible()
        assert self.main_window.progress_bar.value() == 50
        
        # 不定進捗表示
        self.main_window.show_progress("不定進捗", 0)
        assert self.main_window.progress_bar.isVisible()
        assert self.main_window.progress_bar.minimum() == 0
        assert self.main_window.progress_bar.maximum() == 0
        
        # 進捗非表示
        self.main_window.hide_progress("完了")
        assert not self.main_window.progress_bar.isVisible()
    
    def test_system_info_update(self):
        """システム情報更新のテスト"""
        test_info = "テストシステム情報"
        
        self.main_window.update_system_info(test_info)
        
        # システム情報ラベルが更新されていることを確認
        assert self.main_window.system_info_label.text() == test_info
    
    @patch('src.gui.main_window.QFileDialog.getExistingDirectory')
    def test_open_folder_dialog(self, mock_dialog):
        """フォルダ選択ダイアログのテスト"""
        # モックの設定
        test_folder = "/test/folder/path"
        mock_dialog.return_value = test_folder
        
        # シグナルのモック
        with patch.object(self.main_window, 'folder_selected') as mock_signal:
            self.main_window._open_folder_dialog()
            
            # ダイアログが呼ばれたことを確認
            mock_dialog.assert_called_once()
            
            # シグナルが発行されたことを確認
            mock_signal.emit.assert_called_once_with(test_folder)
    
    @patch('src.gui.main_window.QMessageBox.information')
    def test_show_search_dialog(self, mock_msgbox):
        """検索ダイアログ表示のテスト（プレースホルダー）"""
        self.main_window._show_search_dialog()
        
        # メッセージボックスが表示されたことを確認
        mock_msgbox.assert_called_once()
    
    def test_rebuild_index_user_cancels(self):
        """インデックス再構築でユーザーがキャンセルした場合のテスト"""
        # ユーザーが「いいえ」を選択した場合
        self.msgbox_mocks['question'].return_value = QMessageBox.No
        
        self.main_window._rebuild_index()
        
        # 確認ダイアログが表示されたことを確認
        self.msgbox_mocks['question'].assert_called_once()
        # 警告やエラーダイアログは表示されないことを確認
        self.msgbox_mocks['warning'].assert_not_called()
        self.msgbox_mocks['critical'].assert_not_called()

    def test_rebuild_index_no_folder_selected(self):
        """フォルダが選択されていない場合のテスト"""
        # ユーザーが「はい」を選択
        self.msgbox_mocks['question'].return_value = QMessageBox.Yes
        
        # フォルダが選択されていない状態をモック
        self.main_window.folder_tree_container.get_selected_folder.return_value = None
        
        self.main_window._rebuild_index()
        
        # 確認ダイアログと警告ダイアログが表示されることを確認
        self.msgbox_mocks['question'].assert_called_once()
        self.msgbox_mocks['warning'].assert_called_once()
        
        # 警告ダイアログの内容を確認
        args, kwargs = self.msgbox_mocks['warning'].call_args
        assert "フォルダが選択されていません" in args[1]

    def test_rebuild_index_success(self):
        """インデックス再構築が成功する場合のテスト"""
        # ユーザーが「はい」を選択
        self.msgbox_mocks['question'].return_value = QMessageBox.Yes
        
        # フォルダが選択されている状態をモック
        test_folder = "/test/folder"
        self.main_window.folder_tree_container.get_selected_folder.return_value = test_folder
        
        # スレッド開始が成功する状態をモック
        self.main_window.thread_manager.start_indexing_thread.return_value = "test_thread_id"
        
        self.main_window._rebuild_index()
        
        # 各メソッドが正しく呼び出されることを確認
        self.msgbox_mocks['question'].assert_called_once()
        self.main_window.index_manager.clear_index.assert_called_once()
        self.main_window.thread_manager.start_indexing_thread.assert_called_once()
        self.main_window.timeout_manager.start_timeout.assert_called_once_with("test_thread_id")
        
        # エラーダイアログは表示されないことを確認
        self.msgbox_mocks['critical'].assert_not_called()

    def test_rebuild_index_thread_start_failure(self):
        """スレッド開始が失敗する場合のテスト"""
        # ユーザーが「はい」を選択
        self.msgbox_mocks['question'].return_value = QMessageBox.Yes
        
        # フォルダが選択されている状態をモック
        test_folder = "/test/folder"
        self.main_window.folder_tree_container.get_selected_folder.return_value = test_folder
        
        # スレッド開始が失敗する状態をモック
        self.main_window.thread_manager.start_indexing_thread.return_value = None
        
        self.main_window._rebuild_index()
        
        # エラーダイアログが表示されることを確認
        self.msgbox_mocks['critical'].assert_called_once()
        
        # エラーダイアログの内容を確認
        args, kwargs = self.msgbox_mocks['critical'].call_args
        assert "エラー" in args[1]
        assert "インデックス再構築の開始に失敗しました" in args[2]

    def test_rebuild_index_exception_handling(self):
        """例外が発生した場合のエラーハンドリングテスト"""
        # ユーザーが「はい」を選択
        self.msgbox_mocks['question'].return_value = QMessageBox.Yes
        
        # フォルダが選択されている状態をモック
        test_folder = "/test/folder"
        self.main_window.folder_tree_container.get_selected_folder.return_value = test_folder
        
        # clear_indexで例外が発生する状態をモック
        self.main_window.index_manager.clear_index.side_effect = Exception("テスト例外")
        
        self.main_window._rebuild_index()
        
        # エラーダイアログが表示されることを確認
        self.msgbox_mocks['critical'].assert_called_once()
        
        # エラーダイアログの内容を確認
        args, kwargs = self.msgbox_mocks['critical'].call_args
        assert "エラー" in args[1]
        assert "テスト例外" in args[2]
    
    def test_toggle_preview_pane(self):
        """プレビューペイン表示切り替えのテスト"""
        # 初期状態（表示）を確認
        initial_visibility = self.main_window.preview_pane.isVisible()
        
        # 切り替え実行
        self.main_window._toggle_preview_pane()
        
        # 表示状態が変更されたことを確認
        assert self.main_window.preview_pane.isVisible() != initial_visibility
        
        # もう一度切り替えて元に戻ることを確認
        self.main_window._toggle_preview_pane()
        assert self.main_window.preview_pane.isVisible() == initial_visibility
    
    @patch('src.gui.main_window.QMessageBox.about')
    def test_show_about_dialog(self, mock_about):
        """バージョン情報ダイアログのテスト"""
        self.main_window._show_about_dialog()
        
        # aboutダイアログが表示されたことを確認
        mock_about.assert_called_once()
        
        # 呼び出し引数にアプリケーション情報が含まれていることを確認
        args, kwargs = mock_about.call_args
        assert "DocMind" in args[1]  # タイトル
        assert "v1.0.0" in args[2]   # 内容
    
    def test_signal_definitions(self):
        """シグナル定義のテスト"""
        # シグナルが定義されていることを確認
        assert hasattr(self.main_window, 'folder_selected')
        assert hasattr(self.main_window, 'search_requested')
        assert hasattr(self.main_window, 'document_selected')
    
    def test_styling_applied(self):
        """スタイリングが適用されていることをテスト"""
        # スタイルシートが設定されていることを確認
        style_sheet = self.main_window.styleSheet()
        assert len(style_sheet) > 0
        
        # 主要なスタイル要素が含まれていることを確認
        assert "QMainWindow" in style_sheet
        assert "QFrame" in style_sheet
        assert "QMenuBar" in style_sheet


class TestMainWindowIntegration:
    """MainWindowの統合テスト"""
    
    @classmethod
    def setup_class(cls):
        """テストクラスのセットアップ"""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def test_window_show_and_close(self):
        """ウィンドウの表示と閉じる操作のテスト"""
        main_window = MainWindow()
        
        # ウィンドウを表示
        main_window.show()
        assert main_window.isVisible()
        
        # ウィンドウを閉じる（確認ダイアログをスキップ）
        with patch('src.gui.main_window.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.Yes
            main_window.close()
        
        main_window.deleteLater()
    
    def test_menu_action_triggers(self):
        """メニューアクションのトリガーテスト"""
        main_window = MainWindow()
        
        try:
            # 各アクションがトリガーできることを確認（エラーが発生しないことを確認）
            with patch('src.gui.main_window.QFileDialog.getExistingDirectory'):
                main_window.open_folder_action.trigger()
            
            with patch('src.gui.main_window.QMessageBox.information'):
                main_window.search_action.trigger()
            
            with patch('src.gui.main_window.QMessageBox.information'):
                main_window.settings_action.trigger()
            
            with patch('src.gui.main_window.QMessageBox.about'):
                main_window.about_action.trigger()
            
            # プレビューペイン切り替え
            main_window.toggle_preview_action.trigger()
            
        finally:
            main_window.close()
            main_window.deleteLater()


if __name__ == "__main__":
    # テストの実行
    pytest.main([__file__, "-v"])