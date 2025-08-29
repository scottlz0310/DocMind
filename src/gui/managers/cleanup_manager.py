#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind クリーンアップ管理マネージャー

アプリケーション終了時のリソース管理とクリーンアップ処理を管理します。
すべてのコンポーネントの適切な終了処理を提供し、
メモリリークやリソースリークを防止します。
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from src.utils.logging_config import LoggerMixin

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow


class CleanupManager(QObject, LoggerMixin):
    """
    クリーンアップ管理マネージャー
    
    アプリケーション終了時のすべてのリソース管理とクリーンアップを統合管理し、
    適切な終了処理を提供します。
    """
    
    def __init__(self, main_window: 'MainWindow'):
        """
        クリーンアップ管理マネージャーを初期化
        
        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__()
        self.main_window = main_window
        self.logger.info("クリーンアップ管理マネージャーが初期化されました")
    
    def handle_close_event(self, event) -> None:
        """
        ウィンドウクローズイベントをハンドルします

        Args:
            event: クローズイベント
        """
        reply = QMessageBox.question(
            self.main_window,
            "終了確認",
            "DocMindを終了しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.logger.info("アプリケーションを終了します")

            # すべてのコンポーネントを適切にクリーンアップ
            self.cleanup_all_components()

            event.accept()
        else:
            event.ignore()

    def cleanup_all_components(self):
        """
        すべてのコンポーネントをクリーンアップします

        アプリケーション終了時に呼び出され、すべてのリソースを適切に解放し、
        実行中のスレッドやタイマーを安全に停止します。
        """
        try:
            self.logger.info("アプリケーション終了時のクリーンアップを開始します")

            # インデックス再構築関連のクリーンアップを最優先で実行
            self.cleanup_rebuild_components()

            # その他のUIコンポーネントのクリーンアップ
            self.cleanup_ui_components()

            # 検索関連コンポーネントのクリーンアップ
            self.cleanup_search_components()

            # 進捗管理マネージャーのクリーンアップ
            if hasattr(self.main_window, 'progress_manager') and self.main_window.progress_manager:
                self.main_window.progress_manager.cleanup()
                self.logger.info("進捗管理マネージャーをクリーンアップしました")
            
            # シグナル管理マネージャーのクリーンアップ
            if hasattr(self.main_window, 'signal_manager') and self.main_window.signal_manager:
                self.main_window.signal_manager.cleanup()
                self.logger.info("シグナル管理マネージャーをクリーンアップしました")

            self.logger.info("すべてのコンポーネントクリーンアップが完了しました")

        except Exception as e:
            self.logger.error(f"コンポーネントクリーンアップ中にエラーが発生しました: {e}")

    def cleanup_rebuild_components(self):
        """
        インデックス再構築関連コンポーネントのクリーンアップ

        要件7.3, 4.2に対応し、スレッドマネージャーとタイムアウトマネージャーを
        適切にクリーンアップします。
        """
        try:
            # タイムアウトマネージャーのクリーンアップ（最優先）
            if hasattr(self.main_window, 'timeout_manager') and self.main_window.timeout_manager:
                self.main_window.timeout_manager.cancel_all_timeouts()
                self.logger.info("タイムアウトマネージャーをクリーンアップしました")

            # スレッドマネージャーのクリーンアップ
            if hasattr(self.main_window, 'thread_manager') and self.main_window.thread_manager:
                # 実行中のスレッドを安全に停止
                active_threads = self.main_window.thread_manager.get_active_thread_count()
                if active_threads > 0:
                    self.logger.info(f"実行中のスレッド {active_threads} 個を停止します")

                # シャットダウン処理を実行
                self.main_window.thread_manager.shutdown()
                self.logger.info("スレッドマネージャーをクリーンアップしました")

            # 古いインデックス処理スレッドのクリーンアップ（後方互換性）
            self.cleanup_indexing_thread()

        except Exception as e:
            self.logger.error(f"再構築コンポーネントクリーンアップエラー: {e}")

    def cleanup_ui_components(self):
        """UIコンポーネントのクリーンアップ"""
        try:
            # フォルダツリーのクリーンアップ
            if hasattr(self.main_window, 'folder_tree_container') and self.main_window.folder_tree_container:
                if hasattr(self.main_window.folder_tree_container, 'tree_widget') and hasattr(self.main_window.folder_tree_container.tree_widget, '_cleanup_worker'):
                    self.main_window.folder_tree_container.tree_widget._cleanup_worker()
                self.logger.info("フォルダツリーをクリーンアップしました")

            # プレビューウィジェットのクリーンアップ
            if hasattr(self.main_window, 'preview_widget') and self.main_window.preview_widget:
                self.main_window.preview_widget.clear_preview()
                self.logger.info("プレビューウィジェットをクリーンアップしました")

        except Exception as e:
            self.logger.error(f"UIコンポーネントクリーンアップエラー: {e}")

    def cleanup_search_components(self):
        """検索関連コンポーネントのクリーンアップ"""
        try:
            # 検索インターフェースのクリーンアップ（ワーカースレッドがあれば）
            if hasattr(self.main_window, 'search_interface') and self.main_window.search_interface:
                # 実行中のタスクがあればキャンセル
                try:
                    if hasattr(self.main_window, 'search_worker') and self.main_window.search_worker.isRunning():
                        self.main_window.search_worker.cancel()
                        self.main_window.search_worker.wait()
                except:
                    pass
                self.logger.info("検索インターフェースをクリーンアップしました")

            # 検索マネージャーのクリーンアップ
            if hasattr(self.main_window, 'search_manager'):
                try:
                    self.main_window.search_manager.clear_suggestion_cache()
                except:
                    pass
                self.logger.info("検索マネージャーをクリーンアップしました")

        except Exception as e:
            self.logger.error(f"検索コンポーネントクリーンアップエラー: {e}")

    def cleanup_indexing_thread(self) -> None:
        """
        インデックス処理スレッドのクリーンアップ
        """
        try:
            if hasattr(self.main_window, 'indexing_worker') and self.main_window.indexing_worker:
                try:
                    self.main_window.indexing_worker.stop()
                    if hasattr(self.main_window, 'indexing_thread') and self.main_window.indexing_thread:
                        if self.main_window.indexing_thread.isRunning():
                            self.main_window.indexing_thread.quit()
                            self.main_window.indexing_thread.wait(3000)  # 3秒待機
                        try:
                            self.main_window.indexing_thread.deleteLater()
                        except RuntimeError:
                            pass
                    try:
                        self.main_window.indexing_worker.deleteLater()
                    except RuntimeError:
                        pass
                    self.logger.info("レガシーインデックス処理スレッドをクリーンアップしました")
                except Exception as cleanup_error:
                    self.logger.debug(f"レガシーインデックス処理スレッドクリーンアップエラー: {cleanup_error}")

            # ワーカーを先にクリーンアップ
            if hasattr(self.main_window, 'indexing_worker') and self.main_window.indexing_worker:
                try:
                    self.main_window.indexing_worker.deleteLater()
                except RuntimeError:
                    # C++オブジェクトが既に削除されている場合は無視
                    pass
                self.main_window.indexing_worker = None

            # スレッドをクリーンアップ
            if hasattr(self.main_window, 'indexing_thread') and self.main_window.indexing_thread:
                try:
                    self.main_window.indexing_thread.deleteLater()
                except RuntimeError:
                    # C++オブジェクトが既に削除されている場合は無視
                    pass
                self.main_window.indexing_thread = None

            self.logger.debug("インデックス処理スレッドをクリーンアップしました")

        except Exception as e:
            self.logger.warning(f"インデックス処理スレッドのクリーンアップに失敗: {e}")

    def cleanup_partial_index(self) -> None:
        """部分的インデックスのクリーンアップ処理

        要件3.3対応: 部分的に構築されたインデックスをクリアして
        データの一貫性を保持します。
        """
        try:
            if hasattr(self.main_window, 'index_manager') and self.main_window.index_manager:
                self.logger.info("部分的インデックスのクリーンアップを開始")
                self.main_window.index_manager.clear_index()

                # 検索結果をクリア
                if hasattr(self.main_window, 'search_results_widget'):
                    self.main_window.search_results_widget.clear_results()

                # プレビューをクリア
                if hasattr(self.main_window, 'preview_widget'):
                    self.main_window.preview_widget.clear_preview()

                # 検索提案キャッシュをクリア
                if hasattr(self.main_window, 'search_manager'):
                    self.main_window.search_manager.clear_suggestion_cache()

                # システム情報を更新
                if hasattr(self.main_window, 'system_info_label'):
                    self.main_window.system_info_label.setText("インデックス: エラーによりクリア済み")

                self.logger.info("部分的インデックスのクリーンアップが完了")

        except Exception as e:
            self.logger.error(f"インデックスクリーンアップでエラー: {e}")

    def cleanup(self) -> None:
        """
        クリーンアップ管理マネージャー自体のクリーンアップ
        """
        try:
            self.logger.info("クリーンアップ管理マネージャーをクリーンアップしました")
        except Exception as e:
            self.logger.error(f"クリーンアップ管理マネージャーのクリーンアップでエラー: {e}")