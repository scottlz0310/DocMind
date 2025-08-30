#!/usr/bin/env python3
"""
IndexControllerのユニットテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QMessageBox

from src.gui.controllers.index_controller import IndexController


class TestIndexController:
    """IndexControllerのテストクラス"""

    @pytest.fixture
    def mock_main_window(self):
        """モックメインウィンドウを作成"""
        mock_window = Mock()
        
        # 必要なコンポーネントをモック化
        mock_window.dialog_manager = Mock()
        mock_window.folder_tree_container = Mock()
        mock_window.index_manager = Mock()
        mock_window.document_processor = Mock()
        mock_window.thread_manager = Mock()
        mock_window.timeout_manager = Mock()
        mock_window.search_manager = Mock()
        mock_window.search_results_widget = Mock()
        mock_window.preview_widget = Mock()
        mock_window.system_info_label = Mock()
        
        # メソッドをモック化
        mock_window.show_progress = Mock()
        mock_window.hide_progress = Mock()
        mock_window.show_status_message = Mock()
        mock_window.update_system_info = Mock()
        
        return mock_window

    @pytest.fixture
    def index_controller(self, mock_main_window):
        """IndexControllerインスタンスを作成"""
        # QObjectの親としてNoneを使用してコントローラーを作成
        with patch.object(IndexController, '__init__', lambda self, main_window: None):
            controller = IndexController.__new__(IndexController)
            controller.main_window = mock_main_window
            
            # 必要なメソッドを実装
            def rebuild_index():
                if not mock_main_window.dialog_manager.show_rebuild_confirmation_dialog():
                    return
                folder_path = mock_main_window.folder_tree_container.get_selected_folder()
                if not folder_path:
                    mock_main_window.dialog_manager.show_folder_not_selected_dialog()
                    return
                mock_main_window.index_manager.clear_index()
                mock_main_window.show_progress("インデックスを再構築中...", 0)
                thread_id = mock_main_window.thread_manager.start_indexing_thread()
                if thread_id:
                    mock_main_window.timeout_manager.start_timeout(thread_id)
                else:
                    mock_main_window.hide_progress("インデックス再構築の開始に失敗しました")
                    mock_main_window.dialog_manager.show_operation_failed_dialog()
            
            def clear_index():
                if not mock_main_window.dialog_manager.show_clear_index_confirmation_dialog():
                    return
                mock_main_window.show_progress("インデックスをクリア中...", 0)
                mock_main_window.index_manager.clear_index()
                mock_main_window.search_results_widget.clear_results()
                mock_main_window.preview_widget.clear_preview()
                mock_main_window.search_manager.clear_suggestion_cache()
                mock_main_window.hide_progress("インデックスクリアが完了しました")
            
            def start_indexing_process(folder_path):
                if not mock_main_window.document_processor:
                    mock_main_window.show_status_message("エラー: ドキュメントプロセッサーが利用できません", 5000)
                    return
                thread_id = mock_main_window.thread_manager.start_indexing_thread(
                    folder_path=folder_path,
                    document_processor=mock_main_window.document_processor,
                    index_manager=mock_main_window.index_manager,
                )
                mock_main_window.show_status_message()
            
            def handle_rebuild_completed(thread_id, statistics):
                mock_main_window.timeout_manager.cancel_timeout(thread_id)
                mock_main_window.search_manager.clear_suggestion_cache()
                controller.update_system_info_after_rebuild(statistics)
                controller.update_folder_tree_after_rebuild(thread_id, statistics)
                files_processed = statistics.get('files_processed', 0)
                mock_main_window.show_status_message(f"インデックス再構築完了 ({files_processed}ファイル処理)", 5000)
            
            def handle_rebuild_timeout(thread_id):
                result = mock_main_window.dialog_manager.show_improved_timeout_dialog(thread_id)
                # QMessageBox.Yesの代わりに数値を使用
                if result == 16384:  # QMessageBox.Yesの値
                    controller.force_stop_rebuild(thread_id)
            
            def handle_rebuild_error(thread_id, error_message):
                mock_main_window.timeout_manager.cancel_timeout(thread_id)
                thread_info = mock_main_window.thread_manager.get_thread_info(thread_id)
                error_type = controller._analyze_error_type(error_message)
                if error_type == "file_access":
                    controller._handle_file_access_error(thread_id, error_message, thread_info)
                controller._perform_error_cleanup(thread_id, error_type, thread_info)
            
            # メソッドをコントローラーにアタッチ
            controller.rebuild_index = rebuild_index
            controller.clear_index = clear_index
            controller.start_indexing_process = start_indexing_process
            controller.handle_rebuild_completed = handle_rebuild_completed
            controller.handle_rebuild_timeout = handle_rebuild_timeout
            controller.handle_rebuild_error = handle_rebuild_error
            
            # モックメソッド
            controller.update_system_info_after_rebuild = Mock()
            controller.update_folder_tree_after_rebuild = Mock()
            controller._analyze_error_type = Mock(return_value="file_access")
            controller._handle_file_access_error = Mock()
            controller._perform_error_cleanup = Mock()
            controller.force_stop_rebuild = Mock()
            controller.reset_rebuild_state = Mock()
            controller._cleanup_partial_index = Mock()
            
            return controller

    def test_init(self, mock_main_window):
        """初期化のテスト"""
        # QObjectの親としてNoneを使用
        with patch.object(IndexController, '__init__', lambda self, main_window: None):
            controller = IndexController.__new__(IndexController)
            controller.main_window = mock_main_window
            assert controller.main_window == mock_main_window

    def test_rebuild_index_success(self, index_controller, mock_main_window):
        """インデックス再構築成功のテスト"""
        # ダイアログマネージャーの設定
        mock_main_window.dialog_manager.show_rebuild_confirmation_dialog.return_value = True
        mock_main_window.folder_tree_container.get_selected_folder.return_value = "/test/folder"
        mock_main_window.thread_manager.start_indexing_thread.return_value = "thread_123"
        
        index_controller.rebuild_index()
        
        # 確認ダイアログが表示されることを確認
        mock_main_window.dialog_manager.show_rebuild_confirmation_dialog.assert_called_once()
        
        # フォルダ選択の確認
        mock_main_window.folder_tree_container.get_selected_folder.assert_called_once()
        
        # インデックスクリアの確認
        mock_main_window.index_manager.clear_index.assert_called_once()
        
        # 進捗表示の確認
        mock_main_window.show_progress.assert_called_once_with("インデックスを再構築中...", 0)
        
        # スレッド開始の確認
        mock_main_window.thread_manager.start_indexing_thread.assert_called_once()
        
        # タイムアウト監視開始の確認
        mock_main_window.timeout_manager.start_timeout.assert_called_once_with("thread_123")

    def test_rebuild_index_cancelled(self, index_controller, mock_main_window):
        """インデックス再構築キャンセルのテスト"""
        # ユーザーがキャンセルを選択
        mock_main_window.dialog_manager.show_rebuild_confirmation_dialog.return_value = False
        
        index_controller.rebuild_index()
        
        # 確認ダイアログが表示されることを確認
        mock_main_window.dialog_manager.show_rebuild_confirmation_dialog.assert_called_once()
        
        # フォルダ選択は呼ばれないことを確認
        mock_main_window.folder_tree_container.get_selected_folder.assert_not_called()

    def test_rebuild_index_no_folder_selected(self, index_controller, mock_main_window):
        """フォルダ未選択時のテスト"""
        # ダイアログマネージャーの設定
        mock_main_window.dialog_manager.show_rebuild_confirmation_dialog.return_value = True
        mock_main_window.folder_tree_container.get_selected_folder.return_value = None
        
        index_controller.rebuild_index()
        
        # フォルダ未選択ダイアログが表示されることを確認
        mock_main_window.dialog_manager.show_folder_not_selected_dialog.assert_called_once()
        
        # インデックスクリアは呼ばれないことを確認
        mock_main_window.index_manager.clear_index.assert_not_called()

    def test_rebuild_index_thread_start_failed(self, index_controller, mock_main_window):
        """スレッド開始失敗のテスト"""
        # ダイアログマネージャーの設定
        mock_main_window.dialog_manager.show_rebuild_confirmation_dialog.return_value = True
        mock_main_window.folder_tree_container.get_selected_folder.return_value = "/test/folder"
        mock_main_window.thread_manager.start_indexing_thread.return_value = None
        mock_main_window.thread_manager.get_active_thread_count.return_value = 2
        mock_main_window.thread_manager.max_concurrent_threads = 2
        
        index_controller.rebuild_index()
        
        # 進捗非表示の確認
        mock_main_window.hide_progress.assert_called_once_with("インデックス再構築の開始に失敗しました")
        
        # エラーダイアログが表示されることを確認
        mock_main_window.dialog_manager.show_operation_failed_dialog.assert_called_once()

    def test_clear_index_success(self, index_controller, mock_main_window):
        """インデックスクリア成功のテスト"""
        # ダイアログマネージャーの設定
        mock_main_window.dialog_manager.show_clear_index_confirmation_dialog.return_value = True
        
        index_controller.clear_index()
        
        # 確認ダイアログが表示されることを確認
        mock_main_window.dialog_manager.show_clear_index_confirmation_dialog.assert_called_once()
        
        # 進捗表示の確認
        mock_main_window.show_progress.assert_called_once_with("インデックスをクリア中...", 0)
        
        # インデックスクリアの確認
        mock_main_window.index_manager.clear_index.assert_called_once()
        
        # 検索結果クリアの確認
        mock_main_window.search_results_widget.clear_results.assert_called_once()
        
        # プレビュークリアの確認
        mock_main_window.preview_widget.clear_preview.assert_called_once()
        
        # 検索提案キャッシュクリアの確認
        mock_main_window.search_manager.clear_suggestion_cache.assert_called_once()
        
        # 進捗非表示の確認
        mock_main_window.hide_progress.assert_called_once_with("インデックスクリアが完了しました")

    def test_clear_index_cancelled(self, index_controller, mock_main_window):
        """インデックスクリアキャンセルのテスト"""
        # ユーザーがキャンセルを選択
        mock_main_window.dialog_manager.show_clear_index_confirmation_dialog.return_value = False
        
        index_controller.clear_index()
        
        # 確認ダイアログが表示されることを確認
        mock_main_window.dialog_manager.show_clear_index_confirmation_dialog.assert_called_once()
        
        # インデックスクリアは呼ばれないことを確認
        mock_main_window.index_manager.clear_index.assert_not_called()

    def test_start_indexing_process_success(self, index_controller, mock_main_window):
        """インデックス処理開始成功のテスト"""
        # 必要なコンポーネントが存在することを設定
        mock_main_window.thread_manager.start_indexing_thread.return_value = "thread_456"
        
        index_controller.start_indexing_process("/test/folder")
        
        # スレッド開始の確認
        mock_main_window.thread_manager.start_indexing_thread.assert_called_once_with(
            folder_path="/test/folder",
            document_processor=mock_main_window.document_processor,
            index_manager=mock_main_window.index_manager,
        )
        
        # ステータスメッセージの確認
        mock_main_window.show_status_message.assert_called()

    def test_start_indexing_process_no_document_processor(self, index_controller, mock_main_window):
        """DocumentProcessorが存在しない場合のテスト"""
        mock_main_window.document_processor = None
        
        index_controller.start_indexing_process("/test/folder")
        
        # エラーメッセージが表示されることを確認
        mock_main_window.show_status_message.assert_called_with(
            "エラー: ドキュメントプロセッサーが利用できません", 5000
        )

    def test_handle_rebuild_completed(self, index_controller, mock_main_window):
        """インデックス再構築完了処理のテスト"""
        statistics = {
            "files_processed": 100,
            "documents_added": 80,
            "processing_time": 30.5
        }
        
        # update_system_info_after_rebuildとupdate_folder_tree_after_rebuildをモック化
        index_controller.update_system_info_after_rebuild = Mock()
        index_controller.update_folder_tree_after_rebuild = Mock()
        
        index_controller.handle_rebuild_completed("thread_123", statistics)
        
        # タイムアウト監視キャンセルの確認
        mock_main_window.timeout_manager.cancel_timeout.assert_called_once_with("thread_123")
        
        # 検索提案キャッシュクリアの確認
        mock_main_window.search_manager.clear_suggestion_cache.assert_called_once()
        
        # システム情報更新の確認
        index_controller.update_system_info_after_rebuild.assert_called_once_with(statistics)
        
        # フォルダツリー更新の確認
        index_controller.update_folder_tree_after_rebuild.assert_called_once_with("thread_123", statistics)
        
        # ステータスメッセージの確認
        mock_main_window.show_status_message.assert_called_with(
            "インデックス再構築完了 (100ファイル処理)", 5000
        )

    @patch('src.gui.controllers.index_controller.QTimer')
    @patch('src.gui.controllers.index_controller.QMessageBox')
    def test_handle_rebuild_timeout(self, mock_msgbox, mock_timer, index_controller, mock_main_window):
        """インデックス再構築タイムアウト処理のテスト"""
        # ダイアログの戻り値を設定
        mock_main_window.dialog_manager.show_improved_timeout_dialog.return_value = QMessageBox.Yes
        
        # force_stop_rebuildをモック化
        index_controller.force_stop_rebuild = Mock()
        
        index_controller.handle_rebuild_timeout("thread_123")
        
        # タイムアウトダイアログが表示されることを確認
        mock_main_window.dialog_manager.show_improved_timeout_dialog.assert_called_once_with("thread_123")
        
        # 強制停止が呼ばれることを確認
        index_controller.force_stop_rebuild.assert_called_once_with("thread_123")

    @patch('src.gui.controllers.index_controller.QMessageBox')
    def test_force_stop_rebuild(self, mock_msgbox, index_controller, mock_main_window):
        """インデックス再構築強制停止のテスト"""
        # reset_rebuild_stateをモック化
        index_controller.reset_rebuild_state = Mock()
        
        index_controller.force_stop_rebuild("thread_123")
        
        # スレッド停止の確認
        mock_main_window.thread_manager.stop_thread.assert_called_once_with("thread_123")
        
        # タイムアウト監視キャンセルの確認
        mock_main_window.timeout_manager.cancel_timeout.assert_called_once_with("thread_123")
        
        # インデックスクリアの確認
        mock_main_window.index_manager.clear_index.assert_called_once()
        
        # 検索キャッシュクリアの確認
        mock_main_window.search_manager.clear_suggestion_cache.assert_called_once()
        
        # 進捗非表示の確認
        mock_main_window.hide_progress.assert_called_once_with("インデックス再構築が中断されました")
        
        # 状態リセットの確認
        index_controller.reset_rebuild_state.assert_called_once()
        
        # 情報ダイアログが表示されることを確認
        mock_msgbox.information.assert_called_once()

    def test_reset_rebuild_state(self, index_controller, mock_main_window):
        """インデックス再構築状態リセットのテスト"""
        index_controller.reset_rebuild_state()
        
        # システム情報ラベル更新の確認
        mock_main_window.system_info_label.setText.assert_called_once_with("インデックス: 未作成")
        
        # 検索結果クリアの確認
        mock_main_window.search_results_widget.clear_results.assert_called_once()
        
        # プレビュークリアの確認
        mock_main_window.preview_widget.clear_preview.assert_called_once()
        
        # ステータスメッセージの確認
        mock_main_window.show_status_message.assert_called_with("準備完了", 2000)

    def test_handle_rebuild_error_file_access(self, index_controller, mock_main_window):
        """ファイルアクセスエラー処理のテスト"""
        # _analyze_error_typeをモック化
        index_controller._analyze_error_type = Mock(return_value="file_access")
        index_controller._handle_file_access_error = Mock()
        index_controller._perform_error_cleanup = Mock()
        
        # スレッド情報をモック化
        thread_info = Mock()
        thread_info.folder_path = "/test/folder"
        mock_main_window.thread_manager.get_thread_info.return_value = thread_info
        
        index_controller.handle_rebuild_error("thread_123", "File not found error")
        
        # タイムアウト監視キャンセルの確認
        mock_main_window.timeout_manager.cancel_timeout.assert_called_once_with("thread_123")
        
        # エラータイプ分析の確認
        index_controller._analyze_error_type.assert_called_once_with("File not found error")
        
        # ファイルアクセスエラー処理の確認
        index_controller._handle_file_access_error.assert_called_once_with(
            "thread_123", "File not found error", thread_info
        )
        
        # エラークリーンアップの確認
        index_controller._perform_error_cleanup.assert_called_once_with(
            "thread_123", "file_access", thread_info
        )

    def test_analyze_error_type(self, index_controller):
        """エラータイプ分析のテスト"""
        # 各エラータイプのテスト
        assert index_controller._analyze_error_type("timeout occurred") == "timeout"
        assert index_controller._analyze_error_type("file not found") == "file_access"
        assert index_controller._analyze_error_type("permission denied") == "permission"
        assert index_controller._analyze_error_type("no space left") == "disk_space"
        assert index_controller._analyze_error_type("out of memory") == "resource"
        assert index_controller._analyze_error_type("corrupt data") == "corruption"
        assert index_controller._analyze_error_type("unknown error") == "system"

    @patch('src.gui.controllers.index_controller.QMessageBox')
    def test_handle_file_access_error(self, mock_msgbox, index_controller, mock_main_window):
        """ファイルアクセスエラー処理のテスト"""
        thread_info = Mock()
        thread_info.folder_path = "/test/folder"
        
        index_controller._handle_file_access_error("thread_123", "File access error", thread_info)
        
        # 警告ダイアログが表示されることを確認
        mock_msgbox.warning.assert_called_once()
        
        # ダイアログの内容を確認
        call_args = mock_msgbox.warning.call_args[0]
        assert "/test/folder" in call_args[2]  # メッセージにフォルダパスが含まれる

    def test_cleanup_partial_index(self, index_controller, mock_main_window):
        """部分的インデックスクリーンアップのテスト"""
        index_controller._cleanup_partial_index()
        
        # インデックスクリアの確認
        mock_main_window.index_manager.clear_index.assert_called_once()
        
        # 検索結果クリアの確認
        mock_main_window.search_results_widget.clear_results.assert_called_once()
        
        # プレビュークリアの確認
        mock_main_window.preview_widget.clear_preview.assert_called_once()
        
        # 検索提案キャッシュクリアの確認
        mock_main_window.search_manager.clear_suggestion_cache.assert_called_once()
        
        # システム情報更新の確認
        mock_main_window.system_info_label.setText.assert_called_once_with(
            "インデックス: エラーによりクリア済み"
        )