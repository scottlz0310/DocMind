#!/usr/bin/env python3
"""
DocMind 設定変更ハンドラーマネージャー

アプリケーション設定変更・テーマ適用・フォント設定の処理を専門的に管理します。
設定変更イベント、テーマ切り替え、フォント適用を統合処理します。
"""

from PySide6.QtCore import QObject
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMainWindow

from src.utils.logging_config import LoggerMixin


class SettingsHandlerManager(QObject, LoggerMixin):
    """
    設定変更ハンドラーマネージャー

    アプリケーション設定変更関連のイベント処理を専門的に管理し、
    設定適用、テーマ変更、フォント設定を統合処理します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        設定変更ハンドラーマネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window

        self.logger.debug("設定変更ハンドラーマネージャーが初期化されました")

    def handle_settings_changed(self, settings: dict) -> None:
        """設定変更時の処理

        Args:
            settings: 変更された設定の辞書
        """
        try:
            # ログ設定の更新
            if any(key in settings for key in ["log_level", "console_logging", "file_logging"]):
                self._update_logging_config(settings)

            # ウィンドウサイズの更新
            if "window_width" in settings and "window_height" in settings:
                self.main_window.resize(settings["window_width"], settings["window_height"])

            # UIテーマの更新
            if "ui_theme" in settings:
                self._apply_theme(settings["ui_theme"])

            # フォント設定の更新
            if "font_family" in settings or "font_size" in settings:
                self._apply_font_settings(settings)

            self.logger.info("設定変更が適用されました")

        except Exception as e:
            self.logger.error(f"設定変更の適用に失敗しました: {e}")
            self.main_window.dialog_manager.show_partial_failure_dialog(
                "設定変更",
                f"一部の設定変更の適用に失敗しました:\\n{e}",
                "アプリケーションを再起動すると設定が正しく適用される可能性があります。",
            )

    def _update_logging_config(self, settings: dict) -> None:
        """ログ設定を更新

        Args:
            settings: 設定辞書
        """
        try:
            from src.utils.logging_config import reconfigure_logging

            reconfigure_logging(
                level=settings.get("log_level"),
                enable_console=settings.get("console_logging"),
                enable_file=settings.get("file_logging"),
            )
            self.logger.info("ログ設定を更新しました")

        except Exception as e:
            self.logger.error(f"ログ設定の更新に失敗: {e}")

    def _apply_theme(self, theme: str) -> None:
        """UIテーマを適用

        Args:
            theme: テーマ名('light', 'dark', 'system')
        """
        try:
            # window_state_managerに委譲
            if hasattr(self.main_window, "window_state_manager"):
                self.main_window.window_state_manager.apply_theme(theme)
            # フォールバック処理
            elif theme == "dark":
                self.logger.info("ダークテーマが選択されました(実装予定)")
            elif theme == "light":
                self.logger.info("ライトテーマが適用されました")
            elif theme == "system":
                self.logger.info("システムテーマが適用されました")

        except Exception as e:
            self.logger.error(f"テーマ適用中にエラーが発生: {e}")

    def _apply_font_settings(self, settings: dict) -> None:
        """フォント設定を適用

        Args:
            settings: 設定辞書
        """
        try:
            font_family = settings.get("font_family", "システムデフォルト")
            font_size = settings.get("font_size", 10)

            # window_state_managerに委譲
            if hasattr(self.main_window, "window_state_manager"):
                self.main_window.window_state_manager.apply_font_settings(font_family, font_size)
            # フォールバック処理
            elif font_family != "システムデフォルト":
                font = QFont(font_family, font_size)
                self.main_window.setFont(font)
                QApplication.instance().setFont(font)
                self.logger.info(f"フォント設定を適用しました: {font_family}, {font_size}pt")

        except Exception as e:
            self.logger.error(f"フォント設定適用中にエラーが発生: {e}")

    def handle_folder_selected(self, folder_path: str) -> None:
        """フォルダが選択された時の処理

        Args:
            folder_path: 選択されたフォルダのパス
        """
        self.logger.info(f"フォルダツリーでフォルダが選択されました: {folder_path}")
        self.main_window.folder_selected.emit(folder_path)
        self.main_window.show_status_message(f"選択: {folder_path}", 3000)

    def handle_folder_indexed(self, folder_path: str) -> None:
        """フォルダがインデックスに追加された時の処理

        Args:
            folder_path: インデックスに追加されたフォルダのパス
        """
        import os

        self.logger.info(f"フォルダがインデックスに追加されました: {folder_path}")
        self.main_window.show_status_message(f"インデックスに追加: {os.path.basename(folder_path)}", 3000)

        # 実際のインデックス処理を開始
        self.main_window.index_controller.start_indexing_process(folder_path)

    def handle_folder_excluded(self, folder_path: str) -> None:
        """フォルダが除外された時の処理

        Args:
            folder_path: 除外されたフォルダのパス
        """
        import os

        self.logger.info(f"フォルダが除外されました: {folder_path}")
        self.main_window.show_status_message(f"除外: {os.path.basename(folder_path)}", 3000)

        # システム情報を更新
        indexed_count = len(self.main_window.folder_tree_container.get_indexed_folders())
        excluded_count = len(self.main_window.folder_tree_container.get_excluded_folders())
        info_text = f"インデックス: {indexed_count}フォルダ"
        if excluded_count > 0:
            info_text += f", 除外: {excluded_count}フォルダ"
        self.main_window.update_system_info(info_text)

    def handle_folder_refresh(self) -> None:
        """フォルダツリーがリフレッシュされた時の処理"""
        self.logger.info("フォルダツリーがリフレッシュされました")
        self.main_window.show_status_message("フォルダツリーを更新しました", 2000)

        # システム情報を更新
        indexed_count = len(self.main_window.folder_tree_container.get_indexed_folders())
        excluded_count = len(self.main_window.folder_tree_container.get_excluded_folders())
        info_text = f"インデックス: {indexed_count}フォルダ"
        if excluded_count > 0:
            info_text += f", 除外: {excluded_count}フォルダ"
        self.main_window.update_system_info(info_text)

    def handle_manager_status_changed(self, status_message: str) -> None:
        """マネージャー状態変更時の処理

        Args:
            status_message: 状態メッセージ
        """
        # システム情報にスレッド状態を追加
        try:
            indexed_count = len(self.main_window.folder_tree_container.get_indexed_folders())
            active_threads = (
                self.main_window.thread_manager.get_active_thread_count()
                if hasattr(self.main_window, "thread_manager")
                else 0
            )

            if active_threads > 0:
                info_text = f"インデックス: {indexed_count}フォルダ, 処理中: {active_threads}スレッド"
            else:
                info_text = f"インデックス: {indexed_count}フォルダ, {status_message}"

            self.main_window.update_system_info(info_text)
        except Exception as e:
            self.logger.warning(f"システム情報の更新に失敗: {e}")
            self.main_window.update_system_info("システム情報取得中...")

    def cleanup(self) -> None:
        """設定変更ハンドラーマネージャーのクリーンアップ"""
        try:
            self.logger.debug("設定変更ハンドラーマネージャーをクリーンアップしました")

        except Exception as e:
            self.logger.error(f"設定変更ハンドラーマネージャーのクリーンアップ中にエラー: {e}")
