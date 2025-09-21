#!/usr/bin/env python3
"""
DocMind エラー処理・再構築管理マネージャー

インデックス再構築のエラー処理、タイムアウト処理、強制停止処理を管理します。
main_window.pyから分離されたエラー処理関連の処理を統合管理します。
"""

from typing import Any

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox

from src.utils.logging_config import LoggerMixin


class ErrorRebuildManager(QObject, LoggerMixin):
    """
    エラー処理・再構築管理マネージャー

    インデックス再構築時のエラー処理、タイムアウト処理、強制停止処理を管理します。
    メインウィンドウからエラー処理関連の責務を分離し、独立した管理を提供します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        エラー処理・再構築管理マネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(parent=main_window)
        self.main_window = main_window
        self.logger.info("エラー処理・再構築管理マネージャーが初期化されました")

    def handle_rebuild_completed(self, thread_id: str, statistics: dict[str, Any]) -> None:
        """
        インデックス再構築完了時の処理

        Args:
            thread_id: 完了したスレッドID
            statistics: 処理統計情報
        """
        try:
            # タイムアウト監視をキャンセル
            if hasattr(self.main_window, "timeout_manager") and self.main_window.timeout_manager:
                self.main_window.timeout_manager.cancel_timeout(thread_id)

            # SearchManagerのキャッシュをクリア(要件5.3)
            if hasattr(self.main_window, "search_manager") and self.main_window.search_manager:
                self.main_window.search_manager.clear_suggestion_cache()
                self.logger.info("検索提案キャッシュをクリアしました")

            # システム情報ラベルを更新(要件5.1)
            self._update_system_info_after_rebuild(statistics)

            # フォルダツリーの状態を更新(要件5.4)
            self._update_folder_tree_after_rebuild(thread_id, statistics)

            # 完了メッセージを表示
            files_processed = statistics.get("files_processed", 0)
            statistics.get("documents_added", 0)
            statistics.get("processing_time", 0)

            # 完了通知(ステータスメッセージとして表示)
            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(f"インデックス再構築完了 ({files_processed}ファイル処理)", 5000)

            self.logger.info(f"インデックス再構築完了: {thread_id}")
            self.logger.info(f"統計情報: {statistics}")

        except Exception as e:
            self.logger.error(f"インデックス再構築完了処理でエラー: {e}")

    def handle_rebuild_timeout(self, thread_id: str) -> None:
        """
        インデックス再構築タイムアウト時の処理(要件6.1, 6.2対応)

        Args:
            thread_id: タイムアウトが発生したスレッドID
        """
        try:
            self.logger.warning(f"インデックス再構築タイムアウト: {thread_id}")

            # 改善されたタイムアウトダイアログを表示(要件6.2対応)
            if hasattr(self.main_window, "dialog_manager"):
                reply = self.main_window.dialog_manager.show_improved_timeout_dialog(thread_id)

                if reply == QMessageBox.Yes:
                    # 強制停止処理(要件6.1, 6.3対応)
                    self.force_stop_rebuild(thread_id)
                elif reply == QMessageBox.Retry:
                    # ユーザーが再開始を選択
                    self.force_stop_rebuild(thread_id)
                    # 少し待ってから再開始
                    if hasattr(self.main_window, "_rebuild_index"):
                        QTimer.singleShot(3000, self.main_window._rebuild_index)
                # ユーザーが継続を選択した場合、タイムアウト監視を再開
                elif hasattr(self.main_window, "timeout_manager"):
                    self.main_window.timeout_manager.start_timeout(thread_id)
                    self.logger.info(f"タイムアウト監視を再開: {thread_id}")

        except Exception as e:
            self.logger.error(f"タイムアウト処理でエラー: {e}")

    def force_stop_rebuild(self, thread_id: str) -> None:
        """
        インデックス再構築を強制停止

        Args:
            thread_id: 停止対象のスレッドID
        """
        try:
            self.logger.info(f"インデックス再構築強制停止開始: {thread_id}")

            # スレッドを強制停止(要件6.1対応)
            if hasattr(self.main_window, "thread_manager"):
                self.main_window.thread_manager.stop_thread(thread_id)

            # タイムアウト監視をキャンセル
            if hasattr(self.main_window, "timeout_manager") and self.main_window.timeout_manager:
                self.main_window.timeout_manager.cancel_timeout(thread_id)

            # 部分的なインデックスをクリア(要件6.3対応)
            if hasattr(self.main_window, "index_manager"):
                self.main_window.index_manager.clear_index()

            # 検索キャッシュもクリア
            if hasattr(self.main_window, "search_manager") and self.main_window.search_manager:
                self.main_window.search_manager.clear_suggestion_cache()

            # 進捗表示を非表示
            if hasattr(self.main_window, "hide_progress"):
                self.main_window.hide_progress("インデックス再構築が中断されました")

            # システム状態をリセット(要件6.4対応)
            self.reset_rebuild_state()

            # ユーザーに通知(要件6.2対応)
            QMessageBox.information(
                self.main_window,
                "処理中断",
                "インデックス再構築が中断されました。\\n\\n"
                "部分的に処理されたインデックスはクリアされました。\\n"
                "システム状態がリセットされ、再度インデックス再構築を実行できます。",
            )

            self.logger.info(f"インデックス再構築強制停止完了: {thread_id}")

        except Exception as e:
            self.logger.error(f"強制停止処理でエラー: {e}")
            QMessageBox.critical(
                self.main_window,
                "エラー",
                f"インデックス再構築の停止処理でエラーが発生しました:\\n{e!s}",
            )

    def reset_rebuild_state(self) -> None:
        """
        インデックス再構築の状態をリセット(要件6.4対応)

        タイムアウト後やエラー後にシステム状態を初期状態に戻し、
        ユーザーが再度インデックス再構築を実行できるようにします。
        """
        try:
            # システム情報ラベルを更新
            if hasattr(self.main_window, "system_info_label"):
                self.main_window.system_info_label.setText("インデックス: 未作成")

            # 検索結果をクリア
            if hasattr(self.main_window, "search_results_widget"):
                self.main_window.search_results_widget.clear_results()

            # プレビューをクリア
            if hasattr(self.main_window, "preview_widget"):
                self.main_window.preview_widget.clear_preview()

            # フォルダツリーの状態を更新
            if hasattr(self.main_window, "folder_tree_container"):
                # フォルダツリーの表示を更新(利用可能なメソッドを使用)
                if hasattr(self.main_window.folder_tree_container, "refresh_tree"):
                    self.main_window.folder_tree_container.refresh_tree()
                elif hasattr(self.main_window.folder_tree_container, "update"):
                    self.main_window.folder_tree_container.update()

            # ステータスメッセージをリセット
            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message("準備完了", 2000)

            self.logger.info("インデックス再構築状態をリセットしました")

        except Exception as e:
            self.logger.error(f"状態リセット処理でエラー: {e}")

    def _update_system_info_after_rebuild(self, statistics: dict[str, Any]) -> None:
        """
        インデックス再構築後のシステム情報更新(要件5.1, 5.2)

        Args:
            statistics: 処理統計情報
        """
        try:
            # インデックス統計を取得
            if hasattr(self.main_window, "index_manager") and self.main_window.index_manager:
                index_stats = self.main_window.index_manager.get_index_stats()
                document_count = index_stats.get("document_count", 0)

                # システム情報ラベルを更新(要件5.1)
                if hasattr(self.main_window, "system_info_label"):
                    files_processed = statistics.get("files_processed", 0)
                    documents_added = statistics.get("documents_added", 0)
                    processing_time = statistics.get("processing_time", 0)

                    # 詳細なシステム情報を表示
                    self.main_window.system_info_label.setText(
                        f"インデックス済み: {document_count}ドキュメント | "
                        f"処理済み: {files_processed}ファイル | "
                        f"追加: {documents_added}件 | "
                        f"処理時間: {processing_time:.1f}秒"
                    )

                    # ツールチップに詳細情報を設定
                    self.main_window.system_info_label.setToolTip(
                        f"インデックス再構築完了\\n"
                        f"・総ドキュメント数: {document_count}\\n"
                        f"・処理ファイル数: {files_processed}\\n"
                        f"・新規追加ドキュメント: {documents_added}\\n"
                        f"・処理時間: {processing_time:.2f}秒"
                    )

                # 検索機能が新しいインデックスを使用するように更新(要件5.2)
                if hasattr(self.main_window, "search_manager") and self.main_window.search_manager:
                    # SearchManagerの内部状態を更新
                    # インデックスマネージャーが既に更新されているため、
                    # 次回の検索時に自動的に新しいインデックスが使用されます
                    self.logger.info("検索機能が新しいインデックスを使用するように更新されました")

                self.logger.info(f"システム情報更新完了: {document_count}ドキュメント, {files_processed}ファイル処理")

        except Exception as e:
            self.logger.error(f"システム情報更新でエラー: {e}")

    def _update_folder_tree_after_rebuild(self, thread_id: str, statistics: dict[str, Any]) -> None:
        """
        インデックス再構築後のフォルダツリー状態更新

        Args:
            thread_id: 完了したスレッドID
            statistics: 処理統計情報
        """
        try:
            # スレッド情報を取得
            thread_info = None
            if hasattr(self.main_window, "thread_manager"):
                thread_info = self.main_window.thread_manager.get_thread_info(thread_id)

            if not thread_info:
                self.logger.warning(f"スレッド情報が見つかりません: {thread_id}")
                return

            folder_path = thread_info.folder_path
            files_processed = statistics.get("files_processed", 0)
            documents_added = statistics.get("documents_added", 0)

            # フォルダツリーの状態をINDEXEDに更新
            if hasattr(self.main_window, "folder_tree_container") and self.main_window.folder_tree_container:
                self.main_window.folder_tree_container.set_folder_indexed(folder_path, files_processed, documents_added)
                self.logger.info(f"フォルダツリー状態更新: {folder_path} -> INDEXED ({documents_added}ドキュメント)")

                # フォルダツリーの統計情報を更新
                if hasattr(self.main_window.folder_tree_container, "_update_stats"):
                    self.main_window.folder_tree_container._update_stats()
                    self.logger.debug(f"フォルダツリー統計情報更新完了: {folder_path}")

        except Exception as e:
            self.logger.error(f"フォルダツリー状態更新でエラー: {e}")

    def handle_rebuild_error(self, thread_id: str, error_message: str) -> None:
        """
        インデックス再構築エラー時の処理

        Args:
            thread_id: エラーが発生したスレッドID
            error_message: エラーメッセージ
        """
        try:
            self.logger.error(f"インデックス再構築エラー発生: {thread_id} - {error_message}")

            # タイムアウト監視をキャンセル
            if hasattr(self.main_window, "timeout_manager"):
                self.main_window.timeout_manager.cancel_timeout(thread_id)

            # スレッド情報を取得
            thread_info = None
            if hasattr(self.main_window, "thread_manager"):
                thread_info = self.main_window.thread_manager.get_thread_info(thread_id)

            # エラータイプの詳細分析と分岐処理
            error_type = self._analyze_error_type(error_message)

            if error_type == "timeout":
                # タイムアウトエラーはhandle_rebuild_timeoutで処理済み
                self.logger.info("タイムアウトエラーは既に処理済みです")
                return
            elif error_type == "file_access":
                self._handle_file_access_error(thread_id, error_message, thread_info)
            elif error_type == "resource":
                self._handle_resource_error(thread_id, error_message, thread_info)
            elif error_type == "permission":
                self._handle_permission_error(thread_id, error_message, thread_info)
            elif error_type == "disk_space":
                self._handle_disk_space_error(thread_id, error_message, thread_info)
            elif error_type == "corruption":
                self._handle_corruption_error(thread_id, error_message, thread_info)
            else:
                # その他のシステムエラー
                self._handle_system_error(thread_id, error_message, thread_info)

            # 共通のクリーンアップ処理
            self._perform_error_cleanup(thread_id, error_type, thread_info)

        except Exception as e:
            self.logger.error(f"インデックス再構築エラー処理でエラー: {e}")
            # 最後の手段として基本的なエラーダイアログを表示
            if hasattr(self.main_window, "dialog_manager"):
                self.main_window.dialog_manager.show_fallback_error_dialog(error_message)

    def _analyze_error_type(self, error_message: str) -> str:
        """
        エラーメッセージを分析してエラータイプを特定

        Args:
            error_message: エラーメッセージ

        Returns:
            エラータイプ文字列
        """
        error_lower = error_message.lower()

        # タイムアウト関連
        if any(keyword in error_lower for keyword in ["timeout", "タイムアウト", "応答なし"]):
            return "timeout"

        # ファイルアクセス関連
        elif any(
            keyword in error_lower
            for keyword in [
                "file not found",
                "ファイルが見つかりません",
                "no such file",
            ]
        ):
            return "file_access"

        # 権限関連
        elif any(
            keyword in error_lower
            for keyword in [
                "permission denied",
                "アクセスが拒否",
                "権限",
                "access denied",
            ]
        ):
            return "permission"

        # ディスク容量関連
        elif any(keyword in error_lower for keyword in ["no space", "disk full", "容量不足", "ディスク"]):
            return "disk_space"

        # リソース関連
        elif any(keyword in error_lower for keyword in ["memory", "メモリ", "resource", "リソース", "out of memory"]):
            return "resource"

        # データ破損関連
        elif any(keyword in error_lower for keyword in ["corrupt", "破損", "invalid", "不正"]):
            return "corruption"

        else:
            return "system"

    def _handle_file_access_error(self, thread_id: str, error_message: str, thread_info: object | None) -> None:
        """ファイルアクセスエラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, "folder_path"):
            folder_path = thread_info.folder_path

        self.logger.warning(f"ファイルアクセスエラー: {folder_path}")

        QMessageBox.warning(
            self.main_window,
            "ファイルアクセスエラー",
            f"一部のファイルにアクセスできませんでした。\\n\\n"
            f"フォルダ: {folder_path}\\n"
            f"エラー詳細: {error_message}\\n\\n"
            "対処方法:\\n"
            "• ファイルの権限を確認してください\\n"
            "• 他のアプリケーションでファイルが使用されていないか確認してください\\n"
            "• 管理者権限で実行してください\\n\\n"
            "処理可能なファイルのみでインデックスを作成しました。",
        )

    def _handle_permission_error(self, thread_id: str, error_message: str, thread_info: object | None) -> None:
        """権限エラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, "folder_path"):
            folder_path = thread_info.folder_path

        self.logger.error(f"権限エラー: {folder_path}")

        # 部分的なインデックスをクリア
        if hasattr(self.main_window, "cleanup_manager"):
            self.main_window.cleanup_manager.cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "権限エラー",
            f"フォルダへのアクセス権限がありません。\\n\\n"
            f"フォルダ: {folder_path}\\n"
            f"エラー詳細: {error_message}\\n\\n"
            "対処方法:\\n"
            "• 管理者権限でアプリケーションを実行してください\\n"
            "• フォルダの権限設定を確認してください\\n"
            "• 別のフォルダを選択してください\\n\\n"
            "部分的に処理されたインデックスはクリアされました。",
        )

    def _handle_resource_error(self, thread_id: str, error_message: str, thread_info: object | None) -> None:
        """リソースエラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, "folder_path"):
            folder_path = thread_info.folder_path

        self.logger.error(f"リソースエラー: {folder_path}")

        # 部分的なインデックスをクリア
        if hasattr(self.main_window, "cleanup_manager"):
            self.main_window.cleanup_manager.cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "リソース不足エラー",
            f"システムリソースが不足しています。\\n\\n"
            f"フォルダ: {folder_path}\\n"
            f"エラー詳細: {error_message}\\n\\n"
            "対処方法:\\n"
            "• 他のアプリケーションを終了してください\\n"
            "• より小さなフォルダから開始してください\\n"
            "• システムを再起動してください\\n\\n"
            "部分的に処理されたインデックスはクリアされました。",
        )

    def _handle_disk_space_error(self, thread_id: str, error_message: str, thread_info: object | None) -> None:
        """ディスク容量エラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, "folder_path"):
            folder_path = thread_info.folder_path

        self.logger.error(f"ディスク容量エラー: {folder_path}")

        # 部分的なインデックスをクリア
        if hasattr(self.main_window, "cleanup_manager"):
            self.main_window.cleanup_manager.cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "ディスク容量不足エラー",
            f"ディスク容量が不足しています。\\n\\n"
            f"フォルダ: {folder_path}\\n"
            f"エラー詳細: {error_message}\\n\\n"
            "対処方法:\\n"
            "• 不要なファイルを削除してください\\n"
            "• 一時ファイルをクリアしてください\\n"
            "• より小さなフォルダから開始してください\\n\\n"
            "部分的に処理されたインデックスはクリアされました。",
        )

    def _handle_corruption_error(self, thread_id: str, error_message: str, thread_info: object | None) -> None:
        """データ破損エラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, "folder_path"):
            folder_path = thread_info.folder_path

        self.logger.error(f"データ破損エラー: {folder_path}")

        # インデックス全体をクリア(破損の可能性があるため)
        if hasattr(self.main_window, "cleanup_manager"):
            self.main_window.cleanup_manager.cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "データ破損エラー",
            f"ファイルまたはインデックスデータが破損しています。\\n\\n"
            f"フォルダ: {folder_path}\\n"
            f"エラー詳細: {error_message}\\n\\n"
            "対処方法:\\n"
            "• ファイルシステムをチェックしてください\\n"
            "• 破損したファイルを修復または削除してください\\n"
            "• インデックスを完全に再構築してください\\n\\n"
            "既存のインデックスはクリアされました。",
        )

    def _handle_system_error(self, thread_id: str, error_message: str, thread_info: object | None) -> None:
        """システムエラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, "folder_path"):
            folder_path = thread_info.folder_path

        self.logger.error(f"システムエラー: {folder_path}")

        # 部分的なインデックスをクリア
        if hasattr(self.main_window, "cleanup_manager"):
            self.main_window.cleanup_manager.cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "システムエラー",
            f"インデックス再構築中にシステムエラーが発生しました。\\n\\n"
            f"フォルダ: {folder_path}\\n"
            f"エラー詳細: {error_message}\\n\\n"
            "対処方法:\\n"
            "• しばらく待ってから再試行してください\\n"
            "• システムを再起動してください\\n"
            "• より小さなフォルダから開始してください\\n\\n"
            "部分的に処理されたインデックスはクリアされました。",
        )

    def _perform_error_cleanup(self, thread_id: str, error_type: str, thread_info: object | None) -> None:
        """
        エラー後の共通クリーンアップ処理

        Args:
            thread_id: スレッドID
            error_type: エラータイプ
            thread_info: スレッド情報
        """
        try:
            # フォルダツリーの状態を更新
            if thread_info and hasattr(thread_info, "folder_path"):
                if hasattr(self.main_window, "folder_tree_container"):
                    self.main_window.folder_tree_container.set_folder_error(
                        thread_info.folder_path, f"{error_type}エラー"
                    )

            # システム情報を更新
            if hasattr(self.main_window, "thread_manager"):
                active_count = self.main_window.thread_manager.get_active_thread_count()
                indexed_count = 0
                if hasattr(self.main_window, "folder_tree_container"):
                    indexed_count = len(self.main_window.folder_tree_container.get_indexed_folders())

                if active_count > 0:
                    if hasattr(self.main_window, "update_system_info"):
                        self.main_window.update_system_info(
                            f"インデックス: {indexed_count}フォルダ, 処理中: {active_count}スレッド (エラー発生)"
                        )
                elif hasattr(self.main_window, "update_system_info"):
                    self.main_window.update_system_info(f"インデックス: {indexed_count}フォルダ, エラーで停止")

            self.logger.info(f"エラークリーンアップ完了: {thread_id} ({error_type})")

        except Exception as e:
            self.logger.error(f"エラークリーンアップでエラー: {e}")
