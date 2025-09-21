#!/usr/bin/env python3
"""
DocMind インデックス再構築ハンドラーマネージャー

インデックス再構築の進捗・完了・エラー・タイムアウト処理を専門的に管理します。
段階別進捗表示、エラータイプ別処理、システム状態管理を統合処理します。
"""

import os

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox

from src.utils.logging_config import LoggerMixin


class RebuildHandlerManager(QObject, LoggerMixin):
    """
    インデックス再構築ハンドラーマネージャー

    インデックス再構築関連のイベント処理を専門的に管理し、
    進捗表示、完了処理、エラーハンドリングを統合処理します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        インデックス再構築ハンドラーマネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window

        self.logger.debug("インデックス再構築ハンドラーマネージャーが初期化されました")

    def handle_rebuild_progress(
        self, thread_id: str, message: str, current: int, total: int
    ) -> None:
        """インデックス再構築専用の進捗更新処理

        Args:
            thread_id: 進捗を報告したスレッドのID
            message: IndexingWorkerからの進捗メッセージ
            current: 現在の処理数
            total: 総処理数
        """
        try:
            # スレッド情報を取得してフォルダ名を正確に取得
            thread_info = None
            folder_name = "不明"
            folder_path = ""

            if (
                hasattr(self.main_window, "thread_manager")
                and self.main_window.thread_manager
            ):
                thread_info = self.main_window.thread_manager.get_thread_info(thread_id)
                if thread_info:
                    folder_path = thread_info.folder_path
                    folder_name = os.path.basename(folder_path)

            # メッセージから処理段階を判定
            stage = self._determine_rebuild_stage(message, current, total)

            # 段階別進捗メッセージを生成
            formatted_message = self._format_rebuild_progress_message(
                stage, message, folder_name, current, total
            )

            # 進捗表示を更新
            if stage == "scanning":
                # スキャン段階：不定進捗
                self.main_window.show_progress(formatted_message, 0)
                self.logger.info(f"インデックス再構築 - スキャン段階: {folder_name}")

            elif stage == "processing":
                # 処理段階：定進捗
                if total > 0:
                    percentage = min(100, max(0, int((current / total) * 100)))
                    self.main_window.show_progress(
                        formatted_message, percentage, current, total
                    )

                    # 処理完了に近い場合は次の段階への準備
                    if current >= total:
                        # 全ファイル処理完了、インデックス作成段階へ移行
                        indexing_message = f"[{folder_name}] 🔍 インデックスを作成中... ({current}ファイル処理済み)"
                        self.main_window.show_progress(
                            indexing_message, 0
                        )  # 不定進捗でインデックス作成
                        self.logger.info(
                            f"インデックス再構築 - ファイル処理完了、インデックス作成開始: {folder_name}"
                        )
                else:
                    self.main_window.show_progress(formatted_message, 0)

                # 処理中のファイル情報をログに記録
                if "処理中:" in message:
                    self.logger.debug(f"インデックス再構築 - 処理中: {message}")

            elif stage == "indexing":
                # インデックス段階：不定進捗（インデックス作成中）
                self.main_window.show_progress(formatted_message, 0)
                self.logger.info(
                    f"インデックス再構築 - インデックス作成段階: {folder_name}"
                )

            elif stage == "completed":
                # 完了段階：100%進捗で一時的に表示
                self.main_window.show_progress(formatted_message, 100, current, total)
                self.logger.info(f"インデックス再構築 - 完了段階: {folder_name}")

            # システム情報を更新（再構築専用の情報を含む）
            self._update_rebuild_system_info(folder_name, stage, current, total)

            # ステータスメッセージを更新
            self.main_window.show_status_message(formatted_message, 0)

            self.logger.debug(
                f"インデックス再構築進捗: {thread_id} - {stage} - {formatted_message} ({current}/{total})"
            )

        except Exception as e:
            self.logger.error(f"インデックス再構築進捗更新中にエラーが発生: {e}")
            # エラーが発生しても基本的な進捗表示は継続
            fallback_message = f"インデックス再構築中: {message}"
            if total > 0:
                self.main_window.update_progress(current, total, fallback_message)
            else:
                self.main_window.set_progress_indeterminate(fallback_message)

    def handle_rebuild_completed(self, thread_id: str, statistics: dict) -> None:
        """インデックス再構築完了時の処理

        Args:
            thread_id: 完了したスレッドID
            statistics: 処理統計情報
        """
        try:
            # タイムアウト監視をキャンセル
            if (
                hasattr(self.main_window, "timeout_manager")
                and self.main_window.timeout_manager
            ):
                self.main_window.timeout_manager.cancel_timeout(thread_id)

            # SearchManagerのキャッシュをクリア
            if (
                hasattr(self.main_window, "search_manager")
                and self.main_window.search_manager
            ):
                self.main_window.search_manager.clear_suggestion_cache()
                self.logger.info("検索提案キャッシュをクリアしました")

            # システム情報ラベルを更新
            self._update_system_info_after_rebuild(statistics)

            # フォルダツリーの状態を更新
            self._update_folder_tree_after_rebuild(thread_id, statistics)

            # 完了メッセージを表示
            files_processed = statistics.get("files_processed", 0)
            statistics.get("documents_added", 0)
            statistics.get("processing_time", 0)

            # 完了通知（ステータスメッセージとして表示）
            self.main_window.show_status_message(
                f"インデックス再構築完了 ({files_processed}ファイル処理)", 5000
            )

            self.logger.info(f"インデックス再構築完了: {thread_id}")
            self.logger.info(f"統計情報: {statistics}")

        except Exception as e:
            self.logger.error(f"インデックス再構築完了処理でエラー: {e}")

    def handle_rebuild_timeout(self, thread_id: str) -> None:
        """インデックス再構築タイムアウト時の処理

        Args:
            thread_id: タイムアウトが発生したスレッドID
        """
        try:
            self.logger.warning(f"インデックス再構築タイムアウト: {thread_id}")

            # 改善されたタイムアウトダイアログを表示
            reply = self.main_window.dialog_manager.show_improved_timeout_dialog(
                thread_id
            )

            if reply == QMessageBox.Yes:
                # 強制停止処理
                self._force_stop_rebuild(thread_id)
            elif reply == QMessageBox.Retry:
                # ユーザーが再開始を選択
                self._force_stop_rebuild(thread_id)
                # 少し待ってから再開始
                QTimer.singleShot(3000, self._rebuild_index)
            else:
                # ユーザーが継続を選択した場合、タイムアウト監視を再開
                self.main_window.timeout_manager.start_timeout(thread_id)
                self.logger.info(f"タイムアウト監視を再開: {thread_id}")

        except Exception as e:
            self.logger.error(f"タイムアウト処理でエラー: {e}")

    def handle_rebuild_error(self, thread_id: str, error_message: str) -> None:
        """インデックス再構築エラー時の処理

        Args:
            thread_id: エラーが発生したスレッドID
            error_message: エラーメッセージ
        """
        try:
            self.logger.error(
                f"インデックス再構築エラー発生: {thread_id} - {error_message}"
            )

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
                # タイムアウトエラーは_handle_rebuild_timeoutで処理済み
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
            self.main_window.dialog_manager.show_fallback_error_dialog(error_message)

    def _determine_rebuild_stage(self, message: str, current: int, total: int) -> str:
        """進捗メッセージから処理段階を判定"""
        message_lower = message.lower()

        # メッセージ内容から段階を判定
        if "スキャン" in message or "scan" in message_lower:
            return "scanning"
        elif "処理中:" in message or "processing" in message_lower:
            return "processing"
        elif "インデックス" in message and (
            "作成" in message or "creating" in message_lower
        ):
            return "indexing"
        elif current > 0 and total > 0 and current >= total:
            return "completed"
        elif current > 0 and total > 0:
            return "processing"
        else:
            # デフォルトはスキャン段階
            return "scanning"

    def _format_rebuild_progress_message(
        self,
        stage: str,
        original_message: str,
        folder_name: str,
        current: int,
        total: int,
    ) -> str:
        """段階別進捗メッセージをフォーマット"""
        # フォルダ名のプレフィックスを追加
        folder_prefix = f"[{folder_name}] "

        if stage == "scanning":
            if total > 0:
                return f"{folder_prefix}📂 ファイルをスキャン中... ({total}個発見)"
            else:
                return f"{folder_prefix}📂 ファイルをスキャン中..."

        elif stage == "processing":
            # 元のメッセージから詳細情報を抽出
            if "処理中:" in original_message:
                # ファイル名とアイコンが含まれている場合はそのまま使用
                file_info = original_message.split("処理中:", 1)[1].strip()
                return f"{folder_prefix}⚙️ 処理中: {file_info}"
            else:
                return f"{folder_prefix}⚙️ ファイル処理中... ({current}/{total})"

        elif stage == "indexing":
            if current > 0:
                return f"{folder_prefix}🔍 インデックスを作成中... ({current}ファイル処理済み)"
            else:
                return f"{folder_prefix}🔍 インデックスを作成中..."

        elif stage == "completed":
            return f"{folder_prefix}✅ インデックス再構築が完了しました ({current}ファイル処理)"

        else:
            # フォールバック
            return f"{folder_prefix}{original_message}"

    def _update_rebuild_system_info(
        self, folder_name: str, stage: str, current: int, total: int
    ) -> None:
        """インデックス再構築用のシステム情報を更新"""
        try:
            # アクティブなスレッド数を取得
            active_threads = 0
            if (
                hasattr(self.main_window, "thread_manager")
                and self.main_window.thread_manager
            ):
                active_threads = (
                    self.main_window.thread_manager.get_active_thread_count()
                )

            # 段階別のシステム情報を生成
            if stage == "scanning":
                system_info = f"インデックス再構築: {folder_name} (スキャン中) | アクティブ: {active_threads}スレッド"
            elif stage == "processing":
                if total > 0:
                    percentage = min(100, max(0, int((current / total) * 100)))
                    system_info = (
                        f"インデックス再構築: {folder_name} ({current}/{total} - {percentage}%) | "
                        f"アクティブ: {active_threads}スレッド"
                    )
                else:
                    system_info = (
                        f"インデックス再構築: {folder_name} (処理中) | "
                        f"アクティブ: {active_threads}スレッド"
                    )
            elif stage == "indexing":
                system_info = (
                    f"インデックス再構築: {folder_name} (インデックス作成中) | "
                    f"アクティブ: {active_threads}スレッド"
                )
            elif stage == "completed":
                system_info = (
                    f"インデックス再構築: {folder_name} (完了 - {current}ファイル) | "
                    f"アクティブ: {active_threads}スレッド"
                )
            else:
                system_info = f"インデックス再構築: {folder_name} | アクティブ: {active_threads}スレッド"

            self.main_window.update_system_info(system_info)

        except Exception as e:
            self.logger.error(f"再構築システム情報更新中にエラーが発生: {e}")
            # エラーが発生してもシステム情報は基本情報を表示
            self.main_window.update_system_info(
                f"インデックス再構築: エラー - {str(e)[:30]}..."
            )

    def _analyze_error_type(self, error_message: str) -> str:
        """エラーメッセージを分析してエラータイプを特定"""
        error_lower = error_message.lower()

        # タイムアウト関連
        if any(
            keyword in error_lower
            for keyword in ["timeout", "タイムアウト", "応答なし"]
        ):
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
        elif any(
            keyword in error_lower
            for keyword in ["no space", "disk full", "容量不足", "ディスク"]
        ):
            return "disk_space"
        # リソース関連
        elif any(
            keyword in error_lower
            for keyword in ["memory", "メモリ", "resource", "リソース", "out of memory"]
        ):
            return "resource"
        # データ破損関連
        elif any(
            keyword in error_lower for keyword in ["corrupt", "破損", "invalid", "不正"]
        ):
            return "corruption"
        else:
            return "system"

    def _force_stop_rebuild(self, thread_id: str) -> None:
        """インデックス再構築を強制停止"""
        try:
            self.logger.info(f"インデックス再構築強制停止開始: {thread_id}")

            # スレッドを強制停止
            self.main_window.thread_manager.stop_thread(thread_id)

            # タイムアウト監視をキャンセル
            if (
                hasattr(self.main_window, "timeout_manager")
                and self.main_window.timeout_manager
            ):
                self.main_window.timeout_manager.cancel_timeout(thread_id)

            # 部分的なインデックスをクリア
            self.main_window.index_manager.clear_index()

            # 検索キャッシュもクリア
            if (
                hasattr(self.main_window, "search_manager")
                and self.main_window.search_manager
            ):
                self.main_window.search_manager.clear_suggestion_cache()

            # 進捗表示を非表示
            self.main_window.hide_progress("インデックス再構築が中断されました")

            # システム状態をリセット
            self._reset_rebuild_state()

            # ユーザーに通知
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
                f"インデックス再構築の停止処理でエラーが発生しました:\\n{str(e)}",
            )

    def _reset_rebuild_state(self) -> None:
        """インデックス再構築の状態をリセット"""
        try:
            # 検索結果をクリア
            if hasattr(self.main_window, "search_results_widget"):
                self.main_window.search_results_widget.clear_results()

            # プレビューをクリア
            if hasattr(self.main_window, "preview_widget"):
                self.main_window.preview_widget.clear_preview()

            # フォルダツリーの状態を更新
            if hasattr(self.main_window, "folder_tree_container"):
                if hasattr(self.main_window.folder_tree_container, "refresh_tree"):
                    self.main_window.folder_tree_container.refresh_tree()
                elif hasattr(self.main_window.folder_tree_container, "update"):
                    self.main_window.folder_tree_container.update()

            # ステータスメッセージをリセット
            self.main_window.show_status_message("準備完了", 2000)

            self.logger.info("インデックス再構築状態をリセットしました")

        except Exception as e:
            self.logger.error(f"状態リセット処理でエラー: {e}")

    def cleanup(self) -> None:
        """インデックス再構築ハンドラーマネージャーのクリーンアップ"""
        try:
            self.logger.debug(
                "インデックス再構築ハンドラーマネージャーをクリーンアップしました"
            )

        except Exception as e:
            self.logger.error(
                f"インデックス再構築ハンドラーマネージャーのクリーンアップ中にエラー: {e}"
            )
