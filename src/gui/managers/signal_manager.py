#!/usr/bin/env python3
"""
DocMind シグナル管理マネージャー

メインウィンドウのシグナル接続・切断処理を管理します。
すべてのコンポーネント間のシグナル・スロット接続を一元的に管理し、
適切なライフサイクル管理を提供します。
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from src.utils.logging_config import LoggerMixin

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow


class SignalManager(QObject, LoggerMixin):
    """
    シグナル管理マネージャー

    メインウィンドウのすべてのシグナル接続・切断を管理し、
    コンポーネント間の通信を適切に制御します。
    """

    def __init__(self, main_window: "MainWindow"):
        """
        シグナル管理マネージャーを初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__()
        self.main_window = main_window
        self.logger.info("シグナル管理マネージャーが初期化されました")

    def connect_all_signals(self) -> None:
        """
        すべてのシグナル接続を統合管理します

        メインウィンドウ初期化時に呼び出され、すべてのコンポーネントの
        シグナル接続を一元的に管理します。
        """
        try:
            # フォルダツリーのシグナル接続
            self._connect_folder_tree_signals()

            # 検索結果ウィジェットのシグナル接続
            self._connect_search_results_signals()

            # インデックス再構築関連のシグナル接続
            self._connect_rebuild_signals()

            self.logger.info("すべてのシグナル接続が完了しました")

        except Exception as e:
            self.logger.error(f"シグナル接続中にエラーが発生しました: {e}")
            # エラーが発生してもアプリケーションは継続
            pass

    def _connect_folder_tree_signals(self) -> None:
        """フォルダツリーのシグナルを接続します"""
        # フォルダツリーのシグナルはすでに_create_folder_paneで接続済み
        # 将来的に追加のシグナル接続が必要な場合はここに実装
        pass

    def _connect_search_results_signals(self) -> None:
        """検索結果ウィジェットのシグナルを接続します"""
        # 検索結果ウィジェットのシグナルはすでに_create_search_paneで接続済み
        # 将来的に追加のシグナル接続が必要な場合はここに実装
        pass

    def _connect_rebuild_signals(self) -> None:
        """
        インデックス再構築関連のすべてのシグナル接続を管理します

        要件7.3, 4.2に対応し、スレッドマネージャーとタイムアウトマネージャーの
        シグナルを適切に接続します。
        """
        try:
            # スレッドマネージャーのシグナル接続
            self._connect_thread_manager_signals()

            # タイムアウトマネージャーのシグナル接続
            self._connect_timeout_manager_signals()

            self.logger.info("インデックス再構築関連のシグナル接続が完了しました")

        except Exception as e:
            self.logger.error(f"再構築シグナル接続中にエラーが発生しました: {e}")
            # エラーが発生してもアプリケーションは継続
            pass

    def _connect_thread_manager_signals(self) -> None:
        """
        スレッドマネージャーのシグナルを接続します

        IndexingThreadManagerの各種シグナルを適切なハンドラーメソッドに接続し、
        インデックス再構築処理の状態変化を監視します。
        """
        if (
            hasattr(self.main_window, "thread_manager")
            and self.main_window.thread_manager
        ):
            try:
                # スレッド開始シグナル
                self.main_window.thread_manager.thread_started.connect(
                    self.main_window._on_thread_started
                )

                # スレッド完了シグナル
                self.main_window.thread_manager.thread_finished.connect(
                    self.main_window._on_thread_finished
                )

                # スレッドエラーシグナル
                self.main_window.thread_manager.thread_error.connect(
                    self.main_window._on_thread_error
                )

                # スレッド進捗シグナル（インデックス再構築専用）
                self.main_window.thread_manager.thread_progress.connect(
                    self.main_window._on_rebuild_progress
                )

                # マネージャー状態変更シグナル
                self.main_window.thread_manager.manager_status_changed.connect(
                    self.main_window._on_manager_status_changed
                )

                self.logger.debug("スレッドマネージャーのシグナル接続が完了しました")

            except Exception as e:
                self.logger.error(f"スレッドマネージャーシグナル接続エラー: {e}")
        else:
            self.logger.warning("スレッドマネージャーが利用できません")

    def _connect_timeout_manager_signals(self) -> None:
        """
        タイムアウトマネージャーのシグナルを接続します

        RebuildTimeoutManagerのタイムアウト発生シグナルを適切なハンドラーに接続し、
        長時間実行される再構築処理の監視を行います。
        """
        if (
            hasattr(self.main_window, "timeout_manager")
            and self.main_window.timeout_manager
        ):
            try:
                # タイムアウト発生シグナル
                self.main_window.timeout_manager.timeout_occurred.connect(
                    self.main_window.index_controller.handle_rebuild_timeout
                )

                self.logger.debug(
                    "タイムアウトマネージャーのシグナル接続が完了しました"
                )

            except Exception as e:
                self.logger.error(f"タイムアウトマネージャーシグナル接続エラー: {e}")
        else:
            self.logger.warning("タイムアウトマネージャーが利用できません")

    def disconnect_all_signals(self) -> None:
        """
        すべてのシグナル接続を切断します

        メモリリークを防ぐため、アプリケーション終了時にすべてのシグナル接続を
        明示的に切断します。
        """
        try:
            # インデックス再構築関連のシグナル切断
            self._disconnect_rebuild_signals()

            # その他のシグナル切断
            self._disconnect_ui_signals()

            self.logger.info("すべてのシグナル接続を切断しました")

        except Exception as e:
            self.logger.error(f"シグナル切断中にエラーが発生しました: {e}")

    def _disconnect_rebuild_signals(self) -> None:
        """インデックス再構築関連のシグナル接続を切断"""
        try:
            # スレッドマネージャーのシグナル切断
            if (
                hasattr(self.main_window, "thread_manager")
                and self.main_window.thread_manager
            ):
                signals_to_disconnect = [
                    ("thread_started", self.main_window._on_thread_started),
                    ("thread_finished", self.main_window._on_thread_finished),
                    ("thread_error", self.main_window._on_thread_error),
                    ("thread_progress", self.main_window._on_rebuild_progress),
                    (
                        "manager_status_changed",
                        self.main_window._on_manager_status_changed,
                    ),
                ]

                for signal_name, handler in signals_to_disconnect:
                    try:
                        signal = getattr(self.main_window.thread_manager, signal_name)
                        signal.disconnect(handler)
                    except (AttributeError, TypeError):
                        # シグナルが存在しないか、接続されていない場合は無視
                        pass

                self.logger.debug("スレッドマネージャーのシグナルを切断しました")

            # タイムアウトマネージャーのシグナル切断
            if (
                hasattr(self.main_window, "timeout_manager")
                and self.main_window.timeout_manager
            ):
                try:
                    self.main_window.timeout_manager.timeout_occurred.disconnect(
                        self.main_window._handle_rebuild_timeout
                    )
                    self.logger.debug(
                        "タイムアウトマネージャーのシグナルを切断しました"
                    )
                except (AttributeError, TypeError):
                    # シグナルが接続されていない場合は無視
                    pass

        except Exception as e:
            self.logger.error(f"再構築シグナル切断エラー: {e}")

    def _disconnect_ui_signals(self) -> None:
        """UIコンポーネントのシグナル接続を切断"""
        try:
            # メインウィンドウのシグナル切断（接続されているハンドラーがある場合のみ）
            # これらのシグナルは通常他のコンポーネントに接続されているため、
            # 全切断ではなく特定のハンドラーのみ切断する場合は個別に実装

            # フォルダツリーのシグナル切断
            if (
                hasattr(self.main_window, "folder_tree_container")
                and self.main_window.folder_tree_container
            ):
                ui_signals_to_disconnect = [
                    ("folder_selected", self.main_window._on_folder_selected),
                    ("folder_indexed", self.main_window._on_folder_indexed),
                    ("folder_excluded", self.main_window._on_folder_excluded),
                    ("refresh_requested", self.main_window._on_folder_refresh),
                ]

                for signal_name, handler in ui_signals_to_disconnect:
                    try:
                        signal = getattr(
                            self.main_window.folder_tree_container, signal_name
                        )
                        signal.disconnect(handler)
                    except (AttributeError, TypeError):
                        pass

            # 検索インターフェースのシグナル切断
            if (
                hasattr(self.main_window, "search_interface")
                and self.main_window.search_interface
            ):
                search_signals_to_disconnect = [
                    ("search_requested", self.main_window._on_search_requested),
                    ("search_cancelled", self.main_window._on_search_cancelled),
                ]

                for signal_name, handler in search_signals_to_disconnect:
                    try:
                        signal = getattr(self.main_window.search_interface, signal_name)
                        signal.disconnect(handler)
                    except (AttributeError, TypeError):
                        pass

                # 検索入力のテキスト変更シグナル
                try:
                    self.main_window.search_interface.search_input.textChanged.disconnect(
                        self.main_window._on_search_text_changed
                    )
                except (AttributeError, TypeError):
                    pass

            # 検索結果ウィジェットのシグナル切断
            if (
                hasattr(self.main_window, "search_results_widget")
                and self.main_window.search_results_widget
            ):
                result_signals_to_disconnect = [
                    ("result_selected", self.main_window._on_search_result_selected),
                    ("preview_requested", self.main_window._on_preview_requested),
                    ("page_changed", self.main_window._on_page_changed),
                    ("sort_changed", self.main_window._on_sort_changed),
                    ("filter_changed", self.main_window._on_filter_changed),
                ]

                for signal_name, handler in result_signals_to_disconnect:
                    try:
                        signal = getattr(
                            self.main_window.search_results_widget, signal_name
                        )
                        signal.disconnect(handler)
                    except (AttributeError, TypeError):
                        pass

            # プレビューウィジェットのシグナル切断
            if (
                hasattr(self.main_window, "preview_widget")
                and self.main_window.preview_widget
            ):
                preview_signals_to_disconnect = [
                    ("zoom_changed", self.main_window._on_preview_zoom_changed),
                    ("format_changed", self.main_window._on_preview_format_changed),
                ]

                for signal_name, handler in preview_signals_to_disconnect:
                    try:
                        signal = getattr(self.main_window.preview_widget, signal_name)
                        signal.disconnect(handler)
                    except (AttributeError, TypeError):
                        pass

            self.logger.debug("UIコンポーネントのシグナルを切断しました")

        except Exception as e:
            self.logger.error(f"UIシグナル切断エラー: {e}")

    def cleanup(self) -> None:
        """
        シグナル管理マネージャーのクリーンアップ
        """
        try:
            self.disconnect_all_signals()
            self.logger.info("シグナル管理マネージャーをクリーンアップしました")
        except Exception as e:
            self.logger.error(f"シグナル管理マネージャーのクリーンアップでエラー: {e}")
