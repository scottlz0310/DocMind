#!/usr/bin/env python3
"""
DocMind メインウィンドウ

PySide6を使用した3ペインレイアウトのメインアプリケーションウィンドウを実装します。
左ペイン: フォルダツリーナビゲーション
中央ペイン: 検索結果表示
右ペイン: ドキュメントプレビュー

包括的エラーハンドリングと優雅な劣化機能を統合しています。
"""


from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QWidget

from src.core.document_processor import DocumentProcessor
from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.core.rebuild_timeout_manager import RebuildTimeoutManager
from src.core.search_manager import SearchManager
from src.core.thread_manager import IndexingThreadManager
from src.data.database import DatabaseManager
from src.gui.controllers.index_controller import IndexController
from src.gui.dialogs.dialog_manager import DialogManager
from src.gui.managers.cleanup_manager import CleanupManager
from src.gui.managers.error_rebuild_manager import ErrorRebuildManager
from src.gui.managers.event_ui_manager import EventUIManager
from src.gui.managers.layout_manager import LayoutManager
from src.gui.managers.menu_manager import MenuManager
from src.gui.managers.progress_manager import ProgressManager
from src.gui.managers.progress_system_manager import ProgressSystemManager
from src.gui.managers.rebuild_handler_manager import RebuildHandlerManager
from src.gui.managers.search_handler_manager import SearchHandlerManager
from src.gui.managers.settings_handler_manager import SettingsHandlerManager
from src.gui.managers.settings_theme_manager import SettingsThemeManager
from src.gui.managers.signal_manager import SignalManager
from src.gui.managers.status_manager import StatusManager
from src.gui.managers.thread_handler_manager import ThreadHandlerManager
from src.gui.managers.toolbar_manager import ToolbarManager
from src.gui.managers.window_state_manager import WindowStateManager
from src.utils.config import Config
from src.utils.error_handler import handle_exceptions
from src.utils.graceful_degradation import get_global_degradation_manager
from src.utils.logging_config import LoggerMixin


class MainWindow(QMainWindow, LoggerMixin):
    """
    DocMindのメインアプリケーションウィンドウ

    3ペインレイアウト（フォルダツリー、検索結果、プレビュー）を提供し、
    メニューバー、ステータスバー、キーボードショートカットを含む
    完全なデスクトップアプリケーションインターフェースを実装します。

    包括的エラーハンドリングと優雅な劣化機能を統合し、
    コンポーネント障害時の適切なフォールバック処理を提供します。
    """

    # シグナル定義
    folder_selected = Signal(str)  # フォルダが選択された時
    search_requested = Signal(str, str)  # 検索が要求された時 (query, search_type)
    document_selected = Signal(str)  # ドキュメントが選択された時
    error_occurred = Signal(str, str)  # エラーが発生した時 (title, message)

    @handle_exceptions(
        context="メインウィンドウ初期化",
        user_message="メインウィンドウの初期化中にエラーが発生しました。",
        attempt_recovery=True,
        reraise=True,
    )
    def __init__(self, parent: QWidget | None = None):
        """
        メインウィンドウの初期化

        Args:
            parent: 親ウィジェット（通常はNone）
        """
        super().__init__(parent)
        # LoggerMixinのloggerプロパティを使用
        self.config = Config()
        # ダイアログマネージャーの初期化
        self.dialog_manager = DialogManager(self)
        # 進捗管理マネージャーの初期化
        self.progress_manager = ProgressManager(self)
        # レイアウトマネージャーの初期化
        self.layout_manager = LayoutManager(self)
        # メニュー管理マネージャーの初期化
        self.menu_manager = MenuManager(self)
        # ツールバー管理マネージャーの初期化
        self.toolbar_manager = ToolbarManager(self)
        # ステータス管理マネージャーの初期化
        self.status_manager = StatusManager(self)
        # ウィンドウ状態管理マネージャーの初期化
        self.window_state_manager = WindowStateManager(self)
        # ハンドラーマネージャーの初期化
        self.thread_handler_manager = ThreadHandlerManager(self)
        self.search_handler_manager = SearchHandlerManager(self)
        self.rebuild_handler_manager = RebuildHandlerManager(self)
        self.settings_handler_manager = SettingsHandlerManager(self)
        # Phase3新規マネージャーの初期化
        self.settings_theme_manager = SettingsThemeManager(self)
        self.error_rebuild_manager = ErrorRebuildManager(self)
        self.progress_system_manager = ProgressSystemManager(self)
        self.event_ui_manager = EventUIManager(self)
        # インデックス制御コントローラーの初期化
        self.index_controller = IndexController(self)
        # シグナル管理マネージャーの初期化
        self.signal_manager = SignalManager(self)
        # クリーンアップ管理マネージャーの初期化
        self.cleanup_manager = CleanupManager(self)
        # 検索関連コンポーネントの初期化
        self._initialize_search_components()
        # UIレイアウトの設定（各マネージャーに委譲）
        self.window_state_manager.setup_window_properties()
        self.layout_manager.setup_ui()
        self.menu_manager.setup_menu_bar()
        self.toolbar_manager.setup_toolbar()
        self.status_manager.setup_status_bar()
        self.window_state_manager.setup_shortcuts()
        self.window_state_manager.setup_accessibility()
        self.layout_manager.apply_styling()
        # 進捗管理マネージャーの初期化
        self.progress_manager.initialize()
        # すべてのシグナル接続を統合管理（signal_managerに委譲）
        self.signal_manager.connect_all_signals()
        self.logger.info("メインウィンドウが初期化されました")

    def _initialize_search_components(self) -> None:
        """検索関連コンポーネントを初期化"""
        try:
            # データベースパスを設定
            db_path = self.config.data_dir / "documents.db"
            # データベースマネージャーの初期化
            self.database_manager = DatabaseManager(str(db_path))
            # インデックスパスを設定
            index_path = self.config.data_dir / "whoosh_index"
            # インデックスマネージャーの初期化
            self.index_manager = IndexManager(str(index_path))
            # 埋め込みマネージャーの初期化
            self.embedding_manager = EmbeddingManager()
            # ドキュメントプロセッサーの初期化
            self.document_processor = DocumentProcessor()
            # 検索マネージャーの初期化
            self.search_manager = SearchManager(
                self.index_manager, self.embedding_manager
            )
            # スレッドマネージャーの初期化
            self.thread_manager = IndexingThreadManager(max_concurrent_threads=2)
            # タイムアウトマネージャーの初期化
            self.timeout_manager = RebuildTimeoutManager(
                timeout_minutes=30, parent=self
            )
            # 劣化管理マネージャーで検索機能を有効化
            degradation_manager = get_global_degradation_manager()
            degradation_manager.mark_component_healthy("search_manager")
            self.logger.info("検索コンポーネントが初期化されました")
        except Exception as e:
            self.logger.error(f"検索コンポーネントの初期化に失敗: {e}")
            # 劣化管理で検索機能を無効化
            degradation_manager = get_global_degradation_manager()
            degradation_manager.mark_component_degraded(
                "search_manager",
                ["full_text_search", "semantic_search", "hybrid_search"],
                f"検索コンポーネントの初期化に失敗: {e}",
            )

    # メニューアクションのスロット関数
    def _on_settings_changed(self, settings: dict) -> None:
        """設定変更時の処理（settings_theme_managerに委譲）"""
        self.settings_theme_manager.handle_settings_changed(settings)

    # ユーティリティメソッド
    def show_status_message(self, message: str, timeout: int = 0) -> None:
        """
        ステータスバーにメッセージを表示します（status_managerに委譲）

        Args:
            message: 表示するメッセージ
            timeout: 表示時間（ミリ秒、0で永続表示）
        """
        self.status_manager.show_status_message(message, timeout)

    def show_progress(
        self, message: str, value: int, current: int = 0, total: int = 0
    ) -> None:
        """
        進捗バーを表示（progress_managerに委譲）
        """
        self.progress_manager.show_progress(message, value, current, total)

    def hide_progress(self, completion_message: str = "") -> None:
        """
        進捗バーを非表示（progress_managerに委譲）
        """
        self.progress_manager.hide_progress(completion_message)

    def update_system_info(self, info: str) -> None:
        """
        システム情報を更新します（status_managerに委譲）

        Args:
            info: システム情報文字列
        """
        self.status_manager.update_system_info(info)

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """
        進捗を更新（progress_managerに委譲）
        """
        self.progress_manager.update_progress(current, total, message)

    def set_progress_indeterminate(self, message: str = "処理中...") -> None:
        """
        不定進捗モードに設定（progress_managerに委譲）
        """
        self.progress_manager.set_progress_indeterminate(message)

    def is_progress_visible(self) -> bool:
        """
        進捗バーが表示されているか確認（progress_managerに委譲）
        """
        return self.progress_manager.is_progress_visible()

    def get_progress_value(self) -> int:
        """
        現在の進捗値を取得（progress_managerに委譲）
        """
        return self.progress_manager.get_progress_value()

    def set_progress_style(self, style: str) -> None:
        """
        進捗バーのスタイルを設定（progress_managerに委譲）
        """
        self.progress_manager.set_progress_style(style)

    # フォルダツリーのシグナルハンドラー（settings_handler_managerに委譲）
    def _on_folder_selected(self, folder_path: str) -> None:
        """フォルダが選択された時の処理（settings_handler_managerに委譲）"""
        self.settings_handler_manager.handle_folder_selected(folder_path)

    def _on_folder_indexed(self, folder_path: str) -> None:
        """フォルダがインデックスに追加された時の処理（settings_handler_managerに委譲）"""
        self.settings_handler_manager.handle_folder_indexed(folder_path)

    def _format_completion_message(self, statistics: dict) -> str:
        """完了メッセージをフォーマット（progress_system_managerに委譲）"""
        return self.progress_system_manager.format_completion_message(statistics)

    def _cleanup_indexing_thread(self) -> None:
        """
        インデックス処理スレッドのクリーンアップ
        """
        try:
            # ワーカーを先にクリーンアップ
            if hasattr(self, "indexing_worker") and self.indexing_worker:
                try:
                    self.indexing_worker.deleteLater()
                except RuntimeError:
                    # C++オブジェクトが既に削除されている場合は無視
                    pass
                self.indexing_worker = None
            # スレッドをクリーンアップ
            if hasattr(self, "indexing_thread") and self.indexing_thread:
                try:
                    self.indexing_thread.deleteLater()
                except RuntimeError:
                    # C++オブジェクトが既に削除されている場合は無視
                    pass
                self.indexing_thread = None
            self.logger.debug("インデックス処理スレッドをクリーンアップしました")
        except Exception as e:
            self.logger.warning(f"インデックス処理スレッドのクリーンアップに失敗: {e}")

    def _on_thread_started(self, thread_id: str) -> None:
        """スレッド開始時の処理（thread_handler_managerに委譲）"""
        self.thread_handler_manager.handle_thread_started(thread_id)

    def _on_thread_finished(self, thread_id: str, statistics: dict) -> None:
        """スレッド完了時の処理（thread_handler_managerに委譲）"""
        self.thread_handler_manager.handle_thread_finished(thread_id, statistics)

    def _format_detailed_completion_message(
        self, folder_name: str, statistics: dict
    ) -> str:
        """詳細な完了メッセージをフォーマット（progress_system_managerに委譲）"""
        return self.progress_system_manager.format_detailed_completion_message(
            folder_name, statistics
        )

    def _on_thread_error(self, thread_id: str, error_message: str) -> None:
        """スレッドエラー時の処理（thread_handler_managerに委譲）"""
        self.thread_handler_manager.handle_thread_error(thread_id, error_message)

    def _on_thread_progress(
        self, thread_id: str, message: str, current: int, total: int
    ) -> None:
        """スレッド進捗更新時の処理（thread_handler_managerに委譲）"""
        self.thread_handler_manager.handle_thread_progress(
            thread_id, message, current, total
        )

    def _update_system_info_with_progress(
        self, folder_name: str, current: int, total: int, percentage: int
    ) -> None:
        """システム情報を進捗情報で更新（progress_system_managerに委譲）"""
        self.progress_system_manager.update_system_info_with_progress(
            folder_name, current, total, percentage
        )

    def _format_progress_message(self, message: str, current: int, total: int) -> str:
        """進捗メッセージをフォーマット（progress_system_managerに委譲）"""
        return self.progress_system_manager.format_progress_message(
            message, current, total
        )

    def _on_manager_status_changed(self, status_message: str) -> None:
        """マネージャー状態変更時の処理（progress_system_managerに委譲）"""
        self.progress_system_manager.handle_manager_status_changed(status_message)

    def _on_rebuild_progress(
        self, thread_id: str, message: str, current: int, total: int
    ) -> None:
        """インデックス再構築進捗処理（progress_system_managerに委譲）"""
        self.progress_system_manager.handle_rebuild_progress(
            thread_id, message, current, total
        )

    def _on_folder_excluded(self, folder_path: str) -> None:
        """フォルダ除外処理（event_ui_managerに委譲）"""
        self.event_ui_manager.handle_folder_excluded(folder_path)

    def _on_folder_refresh(self) -> None:
        """フォルダリフレッシュ処理（event_ui_managerに委譲）"""
        self.event_ui_manager.handle_folder_refresh()

    def closeEvent(self, event) -> None:
        """
        ウィンドウクローズイベントをハンドルします（cleanup_managerに委譲）

        Args:
            event: クローズイベント
        """
        self.cleanup_manager.handle_close_event(event)

    # 検索結果ウィジェットのシグナルハンドラー
    def _on_search_result_selected(self, result) -> None:
        """検索結果選択処理（event_ui_managerに委譲）"""
        self.event_ui_manager.handle_search_result_selected(result)

    def _on_preview_requested(self, result) -> None:
        """プレビュー要求処理（event_ui_managerに委譲）"""
        self.event_ui_manager.handle_preview_requested(result)

    def _on_page_changed(self, page: int) -> None:
        """ページ変更処理（event_ui_managerに委譲）"""
        self.event_ui_manager.handle_page_changed(page)

    def _on_sort_changed(self, sort_order) -> None:
        """ソート変更処理（event_ui_managerに委譲）"""
        self.event_ui_manager.handle_sort_changed(sort_order)

    def _on_filter_changed(self, filters: dict) -> None:
        """フィルター変更処理（event_ui_managerに委譲）"""
        self.event_ui_manager.handle_filter_changed(filters)

    def _on_preview_zoom_changed(self, zoom_level: int) -> None:
        """プレビューズーム変更処理（event_ui_managerに委譲）"""
        self.event_ui_manager.handle_preview_zoom_changed(zoom_level)

    def _on_preview_format_changed(self, format_name: str) -> None:
        """プレビューフォーマット変更処理（event_ui_managerに委譲）"""
        self.event_ui_manager.handle_preview_format_changed(format_name)

    # 検索インターフェースのシグナルハンドラー
    def _on_search_requested(self, search_query) -> None:
        """検索要求時の処理（search_handler_managerに委譲）"""
        self.search_handler_manager.handle_search_requested(search_query)

    def _on_search_cancelled(self) -> None:
        """検索キャンセル時の処理（search_handler_managerに委譲）"""
        self.search_handler_manager.handle_search_cancelled()

    def _on_search_completed(self, results, execution_time: float) -> None:
        """検索完了時の処理（search_handler_managerに委譲）"""
        self.search_handler_manager.handle_search_completed(results, execution_time)

    def _on_search_error(self, error_message: str) -> None:
        """検索エラー時の処理（search_handler_managerに委譲）"""
        self.search_handler_manager.handle_search_error(error_message)

    def _on_search_text_changed(self, text: str) -> None:
        """検索テキスト変更時の処理（search_handler_managerに委譲）"""
        self.search_handler_manager.handle_search_text_changed(text)

    # インデックス再構築関連のシグナルハンドラー
    def _on_rebuild_completed(self, thread_id: str, statistics: dict) -> None:
        """インデックス再構築完了処理（error_rebuild_managerに委譲）"""
        self.error_rebuild_manager.handle_rebuild_completed(thread_id, statistics)

    def _handle_rebuild_timeout(self, thread_id: str) -> None:
        """インデックス再構築タイムアウト処理（error_rebuild_managerに委譲）"""
        self.error_rebuild_manager.handle_rebuild_timeout(thread_id)

    def _force_stop_rebuild(self, thread_id: str) -> None:
        """インデックス再構築強制停止（error_rebuild_managerに委譲）"""
        self.error_rebuild_manager.force_stop_rebuild(thread_id)

    def _reset_rebuild_state(self) -> None:
        """インデックス再構築状態リセット（error_rebuild_managerに委譲）"""
        self.error_rebuild_manager.reset_rebuild_state()

    def _on_rebuild_error(self, thread_id: str, error_message: str) -> None:
        """インデックス再構築エラー処理（error_rebuild_managerに委譲）"""
        self.error_rebuild_manager.handle_rebuild_error(thread_id, error_message)
