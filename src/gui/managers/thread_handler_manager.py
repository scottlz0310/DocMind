#!/usr/bin/env python3
"""
DocMind スレッド処理ハンドラーマネージャー

インデックス処理スレッドの開始・完了・エラー・進捗イベントを専門的に処理します。
スレッドライフサイクル管理、進捗表示、エラーハンドリングを統合管理します。
"""

import os

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from src.utils.logging_config import LoggerMixin


class ThreadHandlerManager(QObject, LoggerMixin):
    """
    スレッド処理ハンドラーマネージャー

    インデックス処理スレッドのイベント処理を専門的に管理し、
    進捗表示、状態更新、エラーハンドリングを統合処理します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        スレッド処理ハンドラーマネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window

        self.logger.debug("スレッド処理ハンドラーマネージャーが初期化されました")

    def handle_thread_started(self, thread_id: str) -> None:
        """スレッド開始時の処理

        Args:
            thread_id: 開始されたスレッドのID
        """
        thread_info = self.main_window.thread_manager.get_thread_info(thread_id)
        if thread_info:
            folder_name = os.path.basename(thread_info.folder_path)
            self.logger.info(
                f"インデックス処理スレッド開始: {thread_id} ({folder_name})"
            )

            # フォルダツリーの状態をINDEXINGに更新
            self.main_window.folder_tree_container.set_folder_indexing(
                thread_info.folder_path
            )

            # 初期進捗表示
            start_message = f"📁 インデックス処理開始: {folder_name}"
            self.main_window.set_progress_indeterminate(start_message)
            self.main_window.set_progress_style("info")

            # システム情報を更新
            active_count = self.main_window.thread_manager.get_active_thread_count()
            indexed_count = len(
                self.main_window.folder_tree_container.get_indexed_folders()
            )
            self.main_window.update_system_info(
                f"インデックス: {indexed_count}フォルダ, 処理中: {active_count}スレッド"
            )

            # ステータスメッセージも更新
            self.main_window.show_status_message(start_message, 3000)

    def handle_thread_finished(self, thread_id: str, statistics: dict) -> None:
        """スレッド完了時の処理

        Args:
            thread_id: 完了したスレッドのID
            statistics: 処理統計情報
        """
        thread_info = self.main_window.thread_manager.get_thread_info(thread_id)
        if thread_info:
            folder_name = os.path.basename(thread_info.folder_path)

            # フォルダツリーの状態をINDEXEDに更新
            files_processed = statistics.get("files_processed", 0)
            documents_added = statistics.get("documents_added", 0)
            self.main_window.folder_tree_container.set_folder_indexed(
                thread_info.folder_path, files_processed, documents_added
            )

            # 詳細な完了メッセージを生成
            completion_message = self._format_detailed_completion_message(
                folder_name, statistics
            )

            # 進捗バーの表示制御
            active_count = self.main_window.thread_manager.get_active_thread_count() - 1

            if active_count > 0:
                # 他のスレッドがまだ実行中の場合は進捗バーを維持
                self.main_window.show_status_message(completion_message, 5000)
                self.logger.info(f"スレッド完了（他のスレッド実行中）: {folder_name}")
            else:
                # すべてのスレッドが完了した場合のみ進捗バーを非表示
                self.main_window.hide_progress(completion_message)
                self.logger.info("全スレッド完了: 進捗バーを非表示")

                # インデックス再構築完了時の追加処理
                self.main_window.index_controller.handle_rebuild_completed(
                    thread_id, statistics
                )

            # システム情報を更新
            indexed_count = len(
                self.main_window.folder_tree_container.get_indexed_folders()
            )

            if active_count > 0:
                self.main_window.update_system_info(
                    f"インデックス: {indexed_count}フォルダ, 処理中: {active_count}スレッド"
                )
            else:
                self.main_window.update_system_info(
                    f"インデックス: {indexed_count}フォルダ, 待機中"
                )

            # 完了ログ
            duration = thread_info.get_duration()
            self.logger.info(
                f"インデックス処理完了: {thread_id} ({folder_name}, {duration:.2f}秒)"
            )
            self.logger.info(f"統計情報: {statistics}")

    def handle_thread_error(self, thread_id: str, error_message: str) -> None:
        """スレッドエラー時の処理

        Args:
            thread_id: エラーが発生したスレッドのID
            error_message: エラーメッセージ
        """
        thread_info = self.main_window.thread_manager.get_thread_info(thread_id)
        folder_name = "不明"
        if thread_info:
            folder_name = os.path.basename(thread_info.folder_path)
            # フォルダツリーの状態をERRORに更新
            self.main_window.folder_tree_container.set_folder_error(
                thread_info.folder_path, error_message
            )

        # 進捗バーの表示制御
        active_count = self.main_window.thread_manager.get_active_thread_count() - 1

        if active_count > 0:
            # 他のスレッドがまだ実行中の場合は進捗バーを維持し、エラースタイルに変更
            self.main_window.set_progress_style("error")
            error_msg = f"エラー発生 ({folder_name}): {error_message}"
            self.main_window.show_status_message(error_msg, 8000)
            self.logger.warning(f"スレッドエラー（他のスレッド実行中）: {folder_name}")
        else:
            # すべてのスレッドが完了/エラーした場合のみ進捗バーを非表示
            self.main_window.hide_progress("")
            error_msg = f"インデックス処理エラー ({folder_name}): {error_message}"
            self.main_window.show_status_message(error_msg, 10000)
            self.logger.error("全スレッド完了/エラー: 進捗バーを非表示")

            # インデックス再構築エラー時の追加処理
            self.main_window.index_controller.handle_rebuild_error(
                thread_id, error_message
            )

        # エラーログ
        self.logger.error(f"スレッドエラー: {thread_id} - {error_message}")

        # システム情報を更新
        indexed_count = len(
            self.main_window.folder_tree_container.get_indexed_folders()
        )
        if active_count > 0:
            self.main_window.update_system_info(
                f"インデックス: {indexed_count}フォルダ, 処理中: {active_count}スレッド (エラー発生)"
            )
        else:
            self.main_window.update_system_info(
                f"インデックス: {indexed_count}フォルダ, エラーで停止"
            )

    def handle_thread_progress(
        self, thread_id: str, message: str, current: int, total: int
    ) -> None:
        """スレッド進捗更新時の処理

        Args:
            thread_id: 進捗を報告したスレッドのID
            message: 進捗メッセージ
            current: 現在の処理数
            total: 総処理数
        """
        try:
            # スレッド情報を取得してフォルダ名を正確に取得
            thread_info = None
            folder_name = "不明"

            if (
                hasattr(self.main_window, "thread_manager")
                and self.main_window.thread_manager
            ):
                thread_info = self.main_window.thread_manager.get_thread_info(thread_id)
                if thread_info:
                    folder_name = os.path.basename(thread_info.folder_path)

            # 詳細な進捗メッセージを生成
            detailed_message = self._format_progress_message(message, current, total)

            # フォルダ名を含む完全なメッセージを作成
            full_message = f"[{folder_name}] {detailed_message}"

            # 進捗表示を更新
            if total > 0:
                # 正確な進捗率計算を使用
                self.main_window.update_progress(current, total, full_message)

                # システム情報を更新（詳細な進捗情報を含む）
                self._update_system_info_with_progress(
                    folder_name, current, total, self.main_window.get_progress_value()
                )
            else:
                # 不定進捗の場合（スキャン中など）
                self.main_window.set_progress_indeterminate(full_message)
                self._update_system_info_with_progress(folder_name, current, total, 0)

            # ステータスメッセージを更新
            self.main_window.show_status_message(full_message, 0)

            self.logger.debug(
                f"スレッド進捗更新: {thread_id} - {full_message} ({current}/{total})"
            )

        except Exception as e:
            self.logger.error(f"進捗更新処理中にエラーが発生: {e}")
            # エラーが発生しても進捗表示は継続
            fallback_message = f"処理中: {message}"
            if total > 0:
                self.main_window.update_progress(current, total, fallback_message)
            else:
                self.main_window.set_progress_indeterminate(fallback_message)

    def _format_detailed_completion_message(
        self, folder_name: str, statistics: dict
    ) -> str:
        """詳細な完了メッセージをフォーマット"""
        try:
            files_processed = statistics.get("files_processed", 0)
            files_failed = statistics.get("files_failed", 0)
            statistics.get("documents_added", 0)
            processing_time = statistics.get("processing_time", 0.0)

            if files_processed == 0 and files_failed == 0:
                return f"✅ {folder_name}: 処理対象ファイルなし"

            total_files = files_processed + files_failed
            success_rate = (
                (files_processed / total_files) * 100 if total_files > 0 else 0
            )

            if files_failed == 0:
                return f"✅ {folder_name}: {files_processed}ファイル処理完了 ({processing_time:.1f}秒)"
            else:
                return f"⚠️ {folder_name}: {files_processed}/{total_files}ファイル処理完了 (成功率: {success_rate:.1f}%)"

        except Exception as e:
            self.logger.warning(f"完了メッセージのフォーマットに失敗: {e}")
            return f"✅ {folder_name}: インデックス処理完了"

    def _format_progress_message(self, message: str, current: int, total: int) -> str:
        """進捗メッセージをフォーマットして詳細情報を追加"""
        try:
            # 進捗率を計算
            percentage = 0
            if total > 0:
                percentage = min(100, max(0, int((current / total) * 100)))

            # 処理段階を判定してアイコンと詳細情報を追加
            if "スキャン" in message:
                if total > 0:
                    return f"📁 {message} ({current}/{total}ファイル)"
                else:
                    return f"📁 {message}"
            elif "処理中:" in message:
                # ファイル名を抽出して短縮表示
                if total > 0:
                    if ":" in message:
                        file_part = message.split(":", 1)[1].strip()
                        if len(file_part) > 30:
                            file_part = file_part[:27] + "..."
                        return f"📄 処理中: {file_part} ({current}/{total} - {percentage}%)"
                    else:
                        return f"📄 {message} ({current}/{total} - {percentage}%)"
                else:
                    return f"📄 {message}"
            elif "インデックス" in message:
                if total > 0:
                    return f"🔍 {message} ({current}/{total} - {percentage}%)"
                else:
                    return f"🔍 {message}"
            elif "監視" in message or "FileWatcher" in message:
                return f"👁️ {message}"
            elif "完了" in message:
                return f"✅ {message}"
            elif "エラー" in message:
                return f"❌ {message}"
            else:
                # その他のメッセージ
                if total > 0:
                    return f"⚙️ {message} ({current}/{total} - {percentage}%)"
                else:
                    return f"⚙️ {message}"

        except Exception as e:
            self.logger.warning(f"進捗メッセージのフォーマットに失敗: {e}")
            return message

    def _update_system_info_with_progress(
        self, folder_name: str, current: int, total: int, percentage: int
    ) -> None:
        """システム情報を進捗情報で更新"""
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

            # インデックス済みフォルダ数を取得
            indexed_count = 0
            if hasattr(self.main_window, "folder_tree_container"):
                indexed_count = len(
                    self.main_window.folder_tree_container.get_indexed_folders()
                )

            if total > 0:
                # 定進捗の場合
                system_info = (
                    f"インデックス: {indexed_count}フォルダ | "
                    f"処理中: {folder_name} ({current}/{total} - {percentage}%) | "
                    f"アクティブ: {active_threads}スレッド"
                )
            else:
                # 不定進捗の場合
                system_info = (
                    f"インデックス: {indexed_count}フォルダ | "
                    f"処理中: {folder_name} (スキャン中) | "
                    f"アクティブ: {active_threads}スレッド"
                )

            self.main_window.update_system_info(system_info)

        except Exception as e:
            self.logger.warning(f"システム情報の更新に失敗: {e}")
            # フォールバック
            self.main_window.update_system_info(f"処理中: {folder_name}")

    def cleanup(self) -> None:
        """スレッド処理ハンドラーマネージャーのクリーンアップ"""
        try:
            self.logger.debug(
                "スレッド処理ハンドラーマネージャーをクリーンアップしました"
            )

        except Exception as e:
            self.logger.error(
                f"スレッド処理ハンドラーマネージャーのクリーンアップ中にエラー: {e}"
            )
