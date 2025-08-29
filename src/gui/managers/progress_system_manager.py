#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind 進捗・システム情報管理マネージャー

進捗メッセージのフォーマット、システム情報の更新、再構築進捗の管理を行います。
main_window.pyから分離された進捗・システム情報関連の処理を統合管理します。
"""

import os
from typing import Dict, Any

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from src.utils.logging_config import LoggerMixin


class ProgressSystemManager(QObject, LoggerMixin):
    """
    進捗・システム情報管理マネージャー
    
    進捗メッセージのフォーマット、システム情報の更新、再構築進捗の管理を行います。
    メインウィンドウから進捗・システム情報関連の責務を分離し、独立した管理を提供します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        進捗・システム情報管理マネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(parent=main_window)
        self.main_window = main_window
        self.logger.info("進捗・システム情報管理マネージャーが初期化されました")

    def format_completion_message(self, statistics: Dict[str, Any]) -> str:
        """
        完了メッセージをフォーマット

        Args:
            statistics: 統計情報

        Returns:
            str: フォーマットされた完了メッセージ
        """
        try:
            files_processed = statistics.get('files_processed', 0)
            files_failed = statistics.get('files_failed', 0)
            documents_added = statistics.get('documents_added', 0)
            processing_time = statistics.get('processing_time', 0.0)

            if files_processed == 0 and files_failed == 0:
                return "インデックス処理完了（処理対象ファイルなし）"

            success_rate = (files_processed / (files_processed + files_failed)) * 100 if (files_processed + files_failed) > 0 else 0

            return (
                f"インデックス作成完了: {files_processed}ファイル処理済み "
                f"(成功率: {success_rate:.1f}%, 処理時間: {processing_time:.1f}秒)"
            )

        except Exception as e:
            self.logger.warning(f"完了メッセージのフォーマットに失敗: {e}")
            return "インデックス処理完了"

    def format_detailed_completion_message(self, folder_name: str, statistics: Dict[str, Any]) -> str:
        """
        詳細な完了メッセージをフォーマット

        Args:
            folder_name (str): フォルダ名
            statistics (dict): 統計情報

        Returns:
            str: フォーマットされた完了メッセージ
        """
        try:
            files_processed = statistics.get('files_processed', 0)
            files_failed = statistics.get('files_failed', 0)
            documents_added = statistics.get('documents_added', 0)
            processing_time = statistics.get('processing_time', 0.0)

            if files_processed == 0 and files_failed == 0:
                return f"✅ {folder_name}: 処理対象ファイルなし"

            total_files = files_processed + files_failed
            success_rate = (files_processed / total_files) * 100 if total_files > 0 else 0

            if files_failed == 0:
                return f"✅ {folder_name}: {files_processed}ファイル処理完了 ({processing_time:.1f}秒)"
            else:
                return f"⚠️ {folder_name}: {files_processed}/{total_files}ファイル処理完了 (成功率: {success_rate:.1f}%)"

        except Exception as e:
            self.logger.warning(f"完了メッセージのフォーマットに失敗: {e}")
            return f"✅ {folder_name}: インデックス処理完了"

    def update_system_info_with_progress(self, folder_name: str, current: int, total: int, percentage: int) -> None:
        """
        システム情報を進捗情報で更新

        Args:
            folder_name (str): 処理中のフォルダ名
            current (int): 現在の処理数
            total (int): 総処理数
            percentage (int): 進捗率
        """
        try:
            # アクティブなスレッド数を取得
            active_threads = 0
            if hasattr(self.main_window, 'thread_manager') and self.main_window.thread_manager:
                active_threads = self.main_window.thread_manager.get_active_thread_count()

            # インデックス済みフォルダ数を取得
            indexed_count = 0
            if hasattr(self.main_window, 'folder_tree_container'):
                indexed_count = len(self.main_window.folder_tree_container.get_indexed_folders())

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

            if hasattr(self.main_window, 'update_system_info'):
                self.main_window.update_system_info(system_info)

        except Exception as e:
            self.logger.warning(f"システム情報の更新に失敗: {e}")
            # フォールバック
            if hasattr(self.main_window, 'update_system_info'):
                self.main_window.update_system_info(f"処理中: {folder_name}")

    def format_progress_message(self, message: str, current: int, total: int) -> str:
        """
        進捗メッセージをフォーマットして詳細情報を追加

        Args:
            message (str): 基本メッセージ
            current (int): 現在の処理数
            total (int): 総処理数

        Returns:
            str: フォーマットされた進捗メッセージ
        """
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
                    # ファイル名を抽出（"処理中: filename.pdf" の形式から）
                    if ":" in message:
                        file_part = message.split(":", 1)[1].strip()
                        # ファイル名が長い場合は短縮
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

    def handle_manager_status_changed(self, status_message: str) -> None:
        """
        マネージャー状態変更時の処理

        Args:
            status_message (str): 状態メッセージ
        """
        # システム情報にスレッド状態を追加
        try:
            indexed_count = 0
            if hasattr(self.main_window, 'folder_tree_container'):
                indexed_count = len(self.main_window.folder_tree_container.get_indexed_folders())
                
            active_threads = 0
            if hasattr(self.main_window, 'thread_manager') and self.main_window.thread_manager:
                active_threads = self.main_window.thread_manager.get_active_thread_count()

            if active_threads > 0:
                info_text = f"インデックス: {indexed_count}フォルダ, 処理中: {active_threads}スレッド"
            else:
                info_text = f"インデックス: {indexed_count}フォルダ, {status_message}"

            if hasattr(self.main_window, 'update_system_info'):
                self.main_window.update_system_info(info_text)
        except Exception as e:
            self.logger.warning(f"システム情報の更新に失敗: {e}")
            if hasattr(self.main_window, 'update_system_info'):
                self.main_window.update_system_info("システム情報取得中...")

    def handle_rebuild_progress(self, thread_id: str, message: str, current: int, total: int) -> None:
        """
        インデックス再構築専用の進捗更新処理

        段階別進捗メッセージ（スキャン、処理、インデックス、完了）を提供し、
        既存のshow_progress、update_progress、hide_progressメソッドを活用します。

        Args:
            thread_id (str): 進捗を報告したスレッドのID
            message (str): IndexingWorkerからの進捗メッセージ
            current (int): 現在の処理数
            total (int): 総処理数
        """
        try:
            # スレッド情報を取得してフォルダ名を正確に取得
            thread_info = None
            folder_name = "不明"
            folder_path = ""

            if hasattr(self.main_window, 'thread_manager') and self.main_window.thread_manager:
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
                if hasattr(self.main_window, 'show_progress'):
                    self.main_window.show_progress(formatted_message, 0)
                self.logger.info(f"インデックス再構築 - スキャン段階: {folder_name}")

            elif stage == "processing":
                # 処理段階：定進捗
                if total > 0:
                    percentage = min(100, max(0, int((current / total) * 100)))
                    if hasattr(self.main_window, 'show_progress'):
                        self.main_window.show_progress(formatted_message, percentage, current, total)

                    # 処理完了に近い場合は次の段階への準備
                    if current >= total:
                        # 全ファイル処理完了、インデックス作成段階へ移行
                        indexing_message = f"[{folder_name}] 🔍 インデックスを作成中... ({current}ファイル処理済み)"
                        if hasattr(self.main_window, 'show_progress'):
                            self.main_window.show_progress(indexing_message, 0)  # 不定進捗でインデックス作成
                        self.logger.info(f"インデックス再構築 - ファイル処理完了、インデックス作成開始: {folder_name}")
                else:
                    if hasattr(self.main_window, 'show_progress'):
                        self.main_window.show_progress(formatted_message, 0)

                # 処理中のファイル情報をログに記録
                if "処理中:" in message:
                    self.logger.debug(f"インデックス再構築 - 処理中: {message}")

            elif stage == "indexing":
                # インデックス段階：不定進捗（インデックス作成中）
                if hasattr(self.main_window, 'show_progress'):
                    self.main_window.show_progress(formatted_message, 0)
                self.logger.info(f"インデックス再構築 - インデックス作成段階: {folder_name}")

            elif stage == "completed":
                # 完了段階：100%進捗で一時的に表示
                if hasattr(self.main_window, 'show_progress'):
                    self.main_window.show_progress(formatted_message, 100, current, total)
                self.logger.info(f"インデックス再構築 - 完了段階: {folder_name}")

                # 完了メッセージを少し表示してから、実際の完了処理は _on_thread_finished で行う
                # ここでは進捗バーを非表示にしない（_on_thread_finished で処理）

            # システム情報を更新（再構築専用の情報を含む）
            self._update_rebuild_system_info(folder_name, stage, current, total)

            # ステータスメッセージを更新
            if hasattr(self.main_window, 'show_status_message'):
                self.main_window.show_status_message(formatted_message, 0)

            self.logger.debug(f"インデックス再構築進捗: {thread_id} - {stage} - {formatted_message} ({current}/{total})")

        except Exception as e:
            self.logger.error(f"インデックス再構築進捗更新中にエラーが発生: {e}")
            # エラーが発生しても基本的な進捗表示は継続
            fallback_message = f"インデックス再構築中: {message}"
            if total > 0:
                if hasattr(self.main_window, 'update_progress'):
                    self.main_window.update_progress(current, total, fallback_message)
            else:
                if hasattr(self.main_window, 'set_progress_indeterminate'):
                    self.main_window.set_progress_indeterminate(fallback_message)

    def _determine_rebuild_stage(self, message: str, current: int, total: int) -> str:
        """
        進捗メッセージから処理段階を判定

        Args:
            message (str): IndexingWorkerからの進捗メッセージ
            current (int): 現在の処理数
            total (int): 総処理数

        Returns:
            str: 処理段階 ("scanning", "processing", "indexing", "completed")
        """
        message_lower = message.lower()

        # メッセージ内容から段階を判定
        if "スキャン" in message or "scan" in message_lower:
            return "scanning"
        elif "処理中:" in message or "processing" in message_lower:
            return "processing"
        elif "インデックス" in message and ("作成" in message or "creating" in message_lower):
            return "indexing"
        elif current > 0 and total > 0 and current >= total:
            return "completed"
        elif current > 0 and total > 0:
            return "processing"
        else:
            # デフォルトはスキャン段階
            return "scanning"

    def _format_rebuild_progress_message(self, stage: str, original_message: str,
                                       folder_name: str, current: int, total: int) -> str:
        """
        段階別進捗メッセージをフォーマット

        Args:
            stage (str): 処理段階
            original_message (str): 元のメッセージ
            folder_name (str): フォルダ名
            current (int): 現在の処理数
            total (int): 総処理数

        Returns:
            str: フォーマットされた進捗メッセージ
        """
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

    def _update_rebuild_system_info(self, folder_name: str, stage: str, current: int, total: int) -> None:
        """
        インデックス再構築用のシステム情報を更新

        Args:
            folder_name (str): 処理中のフォルダ名
            stage (str): 処理段階
            current (int): 現在の処理数
            total (int): 総処理数
        """
        try:
            # アクティブなスレッド数を取得
            active_threads = 0
            if hasattr(self.main_window, 'thread_manager') and self.main_window.thread_manager:
                active_threads = self.main_window.thread_manager.get_active_thread_count()

            # 段階別のシステム情報を生成
            if stage == "scanning":
                system_info = f"インデックス再構築: {folder_name} (スキャン中) | アクティブ: {active_threads}スレッド"
            elif stage == "processing":
                if total > 0:
                    percentage = min(100, max(0, int((current / total) * 100)))
                    system_info = f"インデックス再構築: {folder_name} ({current}/{total} - {percentage}%) | アクティブ: {active_threads}スレッド"
                else:
                    system_info = f"インデックス再構築: {folder_name} (処理中) | アクティブ: {active_threads}スレッド"
            elif stage == "indexing":
                system_info = f"インデックス再構築: {folder_name} (インデックス作成中) | アクティブ: {active_threads}スレッド"
            elif stage == "completed":
                system_info = f"インデックス再構築: {folder_name} (完了 - {current}ファイル) | アクティブ: {active_threads}スレッド"
            else:
                system_info = f"インデックス再構築: {folder_name} | アクティブ: {active_threads}スレッド"

            if hasattr(self.main_window, 'update_system_info'):
                self.main_window.update_system_info(system_info)

        except Exception as e:
            self.logger.error(f"再構築システム情報更新中にエラーが発生: {e}")
            # エラーが発生してもシステム情報は基本情報を表示
            if hasattr(self.main_window, 'update_system_info'):
                self.main_window.update_system_info(f"インデックス再構築: エラー - {str(e)[:30]}...")