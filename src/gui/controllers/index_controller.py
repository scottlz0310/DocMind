#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
インデックス制御コントローラー

main_window.pyから分離されたインデックス制御機能を提供します。
インデックス再構築、クリア、エラーハンドリングなどの制御ロジックを管理します。
"""

import os
from typing import Optional, TYPE_CHECKING
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QMessageBox

from src.utils.logging_config import LoggerMixin

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow


class IndexController(QObject, LoggerMixin):
    """
    インデックス制御コントローラー
    
    インデックス再構築、クリア、エラーハンドリングなどの
    インデックス関連の制御ロジックを管理します。
    """
    
    def __init__(self, main_window: 'MainWindow'):
        """
        インデックスコントローラーの初期化
        
        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window
        
    def rebuild_index(self) -> None:
        """
        インデックス再構築を実行します

        このメソッドは要件1.1-1.4に基づいて実装されており、以下の処理を行います：
        1. ユーザーに確認ダイアログを表示（要件1.1）
        2. 現在選択されているフォルダの検証（要件1.2）
        3. 既存インデックスのクリア（要件1.3）
        4. IndexingThreadManagerを使用したバックグラウンド処理開始（要件1.4）
        5. タイムアウト監視の開始（要件6.1）
        6. 進捗表示の開始（要件2.1）

        エラーハンドリング：
        - フォルダ未選択時の適切な通知
        - スレッド開始失敗時の詳細エラー表示
        - システムエラー時の回復処理
        """
        try:
            # 改善された確認ダイアログの表示
            reply = self.main_window.dialog_manager.show_rebuild_confirmation_dialog()

            if not reply:
                return

            # 現在選択されているフォルダパスを取得
            current_folder = self.main_window.folder_tree_container.get_selected_folder()
            if not current_folder:
                self.main_window.dialog_manager.show_folder_not_selected_dialog()
                return

            # 既存のインデックスをクリア
            self.logger.info(f"インデックス再構築開始: {current_folder}")
            self.main_window.index_manager.clear_index()

            # 進捗表示を開始
            self.main_window.show_progress("インデックスを再構築中...", 0)

            # IndexingThreadManagerを使用してインデックス再構築を開始
            try:
                thread_id = self.main_window.thread_manager.start_indexing_thread(
                    folder_path=current_folder,
                    document_processor=self.main_window.document_processor,
                    index_manager=self.main_window.index_manager
                )

                if thread_id:
                    # タイムアウト監視を開始
                    self.main_window.timeout_manager.start_timeout(thread_id)
                    self.logger.info(f"インデックス再構築スレッド開始: {thread_id}")
                    self.main_window.show_status_message(f"インデックス再構築を開始しました (ID: {thread_id})", 3000)
                else:
                    # スレッド開始に失敗した場合の処理
                    self.main_window.hide_progress("インデックス再構築の開始に失敗しました")

                    # 詳細なエラー情報を提供
                    active_count = self.main_window.thread_manager.get_active_thread_count()
                    max_threads = self.main_window.thread_manager.max_concurrent_threads

                    if active_count >= max_threads:
                        error_msg = (
                            f"最大同時実行数に達しています ({active_count}/{max_threads})。\n"
                            "他の処理が完了してから再試行してください。"
                        )
                    elif self.main_window.thread_manager._is_folder_being_processed(current_folder):
                        error_msg = (
                            "このフォルダは既に処理中です。\n"
                            "処理が完了してから再試行してください。"
                        )
                    else:
                        error_msg = (
                            "インデックス再構築の開始に失敗しました。\n"
                            "しばらく待ってから再試行してください。"
                        )

                    self.main_window.dialog_manager.show_operation_failed_dialog(
                        "スレッド開始エラー",
                        error_msg,
                        "しばらく待ってから再試行してください。"
                    )

            except Exception as thread_error:
                # スレッド開始時の例外処理
                self.main_window.hide_progress("インデックス再構築の開始でエラーが発生しました")
                self.logger.error(f"スレッド開始エラー: {thread_error}")

                self.main_window.dialog_manager.show_system_error_dialog(
                    "スレッド開始エラー",
                    f"インデックス再構築スレッドの開始でエラーが発生しました:\n{str(thread_error)}",
                    "システムリソースが不足している可能性があります。"
                )
                return

        except Exception as e:
            self.logger.error(f"インデックス再構築エラー: {e}")
            self.main_window.hide_progress("インデックス再構築でエラーが発生しました")
            self.main_window.dialog_manager.show_system_error_dialog(
                "インデックス再構築エラー",
                f"インデックス再構築でエラーが発生しました:\n{str(e)}",
                "しばらく待ってから再試行してください。"
            )

    def clear_index(self) -> None:
        """インデックスをクリアします"""
        reply = self.main_window.dialog_manager.show_clear_index_confirmation_dialog()

        if reply:
            try:
                self.main_window.show_progress("インデックスをクリア中...", 0)

                # インデックスマネージャーからクリアを実行
                if hasattr(self.main_window, 'index_manager') and self.main_window.index_manager:
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

                    self.main_window.hide_progress("インデックスクリアが完了しました")
                    self.main_window.show_status_message("インデックスをクリアしました", 3000)

                    # システム情報を更新
                    if hasattr(self.main_window, 'system_info_label'):
                        self.main_window.system_info_label.setText("インデックス: クリア済み")

                else:
                    self.main_window.hide_progress("")
                    self.main_window.dialog_manager.show_component_unavailable_dialog("インデックスマネージャー")

            except Exception as e:
                self.main_window.hide_progress("")
                self.logger.error(f"インデックスクリアに失敗しました: {e}")
                self.main_window.dialog_manager.show_operation_failed_dialog(
                    "インデックスクリア",
                    f"インデックスクリアに失敗しました:\n{e}",
                    "システムリソースを確認してから再試行してください。"
                )

    def start_indexing_process(self, folder_path: str) -> None:
        """
        実際のインデックス処理を開始

        IndexingThreadManagerを使用してバックグラウンドスレッドで実行し、
        複数の同時インデックス処理を制御します。

        Args:
            folder_path: インデックス化するフォルダのパス
        """
        try:
            # 必要なコンポーネントが初期化されているかチェック
            if not hasattr(self.main_window, 'document_processor') or not self.main_window.document_processor:
                self.logger.error("DocumentProcessorが初期化されていません")
                self.main_window.show_status_message("エラー: ドキュメントプロセッサーが利用できません", 5000)
                return

            if not hasattr(self.main_window, 'index_manager') or not self.main_window.index_manager:
                self.logger.error("IndexManagerが初期化されていません")
                self.main_window.show_status_message("エラー: インデックスマネージャーが利用できません", 5000)
                return

            if not hasattr(self.main_window, 'thread_manager') or not self.main_window.thread_manager:
                self.logger.error("IndexingThreadManagerが初期化されていません")
                self.main_window.show_status_message("エラー: スレッドマネージャーが利用できません", 5000)
                return

            # スレッドマネージャーを使用してインデックス処理を開始
            thread_id = self.main_window.thread_manager.start_indexing_thread(
                folder_path=folder_path,
                document_processor=self.main_window.document_processor,
                index_manager=self.main_window.index_manager
            )

            if thread_id:
                self.logger.info(f"インデックス処理スレッドを開始しました: {thread_id} ({folder_path})")
                self.main_window.show_status_message(f"インデックス処理を開始: {os.path.basename(folder_path)}", 3000)
            else:
                # 同時実行数制限などで開始できない場合
                active_count = self.main_window.thread_manager.get_active_thread_count()
                max_count = self.main_window.thread_manager.max_concurrent_threads
                self.logger.warning(f"インデックス処理を開始できませんでした: {folder_path} (アクティブ: {active_count}/{max_count})")
                self.main_window.show_status_message(
                    f"インデックス処理を開始できません (同時実行数制限: {active_count}/{max_count})",
                    5000
                )

        except Exception as e:
            self.logger.error(f"インデックス処理の開始に失敗しました: {e}")
            self.main_window.show_status_message(f"エラー: インデックス処理を開始できませんでした", 5000)

    def handle_rebuild_completed(self, thread_id: str, statistics: dict) -> None:
        """インデックス再構築完了時の処理

        Args:
            thread_id: 完了したスレッドID
            statistics: 処理統計情報
        """
        try:
            # タイムアウト監視をキャンセル
            if hasattr(self.main_window, 'timeout_manager') and self.main_window.timeout_manager:
                self.main_window.timeout_manager.cancel_timeout(thread_id)

            # SearchManagerのキャッシュをクリア（要件5.3）
            if hasattr(self.main_window, 'search_manager') and self.main_window.search_manager:
                self.main_window.search_manager.clear_suggestion_cache()
                self.logger.info("検索提案キャッシュをクリアしました")

            # システム情報ラベルを更新（要件5.1）
            self.update_system_info_after_rebuild(statistics)

            # フォルダツリーの状態を更新（要件5.4）
            self.update_folder_tree_after_rebuild(thread_id, statistics)

            # 完了メッセージを表示
            files_processed = statistics.get('files_processed', 0)
            documents_added = statistics.get('documents_added', 0)
            processing_time = statistics.get('processing_time', 0)

            # 完了通知（ステータスメッセージとして表示）
            self.main_window.show_status_message(f"インデックス再構築完了 ({files_processed}ファイル処理)", 5000)

            self.logger.info(f"インデックス再構築完了: {thread_id}")
            self.logger.info(f"統計情報: {statistics}")

        except Exception as e:
            self.logger.error(f"インデックス再構築完了処理でエラー: {e}")

    def handle_rebuild_timeout(self, thread_id: str) -> None:
        """インデックス再構築タイムアウト時の処理（要件6.1, 6.2対応）

        Args:
            thread_id: タイムアウトが発生したスレッドID
        """
        try:
            self.logger.warning(f"インデックス再構築タイムアウト: {thread_id}")

            # 改善されたタイムアウトダイアログを表示（要件6.2対応）
            reply = self.main_window.dialog_manager.show_improved_timeout_dialog(thread_id)

            if reply == QMessageBox.Yes:
                # 強制停止処理（要件6.1, 6.3対応）
                self.force_stop_rebuild(thread_id)
            elif reply == QMessageBox.Retry:
                # ユーザーが再開始を選択
                self.force_stop_rebuild(thread_id)
                # 少し待ってから再開始
                QTimer.singleShot(3000, self.rebuild_index)
            else:
                # ユーザーが継続を選択した場合、タイムアウト監視を再開
                self.main_window.timeout_manager.start_timeout(thread_id)
                self.logger.info(f"タイムアウト監視を再開: {thread_id}")

        except Exception as e:
            self.logger.error(f"タイムアウト処理でエラー: {e}")

    def force_stop_rebuild(self, thread_id: str) -> None:
        """インデックス再構築を強制停止

        Args:
            thread_id: 停止対象のスレッドID
        """
        try:
            self.logger.info(f"インデックス再構築強制停止開始: {thread_id}")

            # スレッドを強制停止（要件6.1対応）
            self.main_window.thread_manager.stop_thread(thread_id)

            # タイムアウト監視をキャンセル
            if hasattr(self.main_window, 'timeout_manager') and self.main_window.timeout_manager:
                self.main_window.timeout_manager.cancel_timeout(thread_id)

            # 部分的なインデックスをクリア（要件6.3対応）
            self.main_window.index_manager.clear_index()

            # 検索キャッシュもクリア
            if hasattr(self.main_window, 'search_manager') and self.main_window.search_manager:
                self.main_window.search_manager.clear_suggestion_cache()

            # 進捗表示を非表示
            self.main_window.hide_progress("インデックス再構築が中断されました")

            # システム状態をリセット（要件6.4対応）
            self.reset_rebuild_state()

            # ユーザーに通知（要件6.2対応）
            QMessageBox.information(
                self.main_window,
                "処理中断",
                "インデックス再構築が中断されました。\n\n"
                "部分的に処理されたインデックスはクリアされました。\n"
                "システム状態がリセットされ、再度インデックス再構築を実行できます。"
            )

            self.logger.info(f"インデックス再構築強制停止完了: {thread_id}")

        except Exception as e:
            self.logger.error(f"強制停止処理でエラー: {e}")
            QMessageBox.critical(
                self.main_window,
                "エラー",
                f"インデックス再構築の停止処理でエラーが発生しました:\n{str(e)}"
            )

    def reset_rebuild_state(self) -> None:
        """インデックス再構築の状態をリセット（要件6.4対応）

        タイムアウト後やエラー後にシステム状態を初期状態に戻し、
        ユーザーが再度インデックス再構築を実行できるようにします。
        """
        try:
            # システム情報ラベルを更新
            if hasattr(self.main_window, 'system_info_label'):
                self.main_window.system_info_label.setText("インデックス: 未作成")

            # 検索結果をクリア
            if hasattr(self.main_window, 'search_results_widget'):
                self.main_window.search_results_widget.clear_results()

            # プレビューをクリア
            if hasattr(self.main_window, 'preview_widget'):
                self.main_window.preview_widget.clear_preview()

            # フォルダツリーの状態を更新
            if hasattr(self.main_window, 'folder_tree_container'):
                # フォルダツリーの表示を更新（利用可能なメソッドを使用）
                if hasattr(self.main_window.folder_tree_container, 'refresh_tree'):
                    self.main_window.folder_tree_container.refresh_tree()
                elif hasattr(self.main_window.folder_tree_container, 'update'):
                    self.main_window.folder_tree_container.update()

            # ステータスメッセージをリセット
            self.main_window.show_status_message("準備完了", 2000)

            self.logger.info("インデックス再構築状態をリセットしました")

        except Exception as e:
            self.logger.error(f"状態リセット処理でエラー: {e}")

    def update_system_info_after_rebuild(self, statistics: dict) -> None:
        """インデックス再構築後のシステム情報更新（要件5.1, 5.2）

        Args:
            statistics: 処理統計情報
        """
        try:
            # インデックス統計を取得
            if hasattr(self.main_window, 'index_manager') and self.main_window.index_manager:
                index_stats = self.main_window.index_manager.get_index_stats()
                document_count = index_stats.get('document_count', 0)

                # システム情報ラベルを更新（要件5.1）
                if hasattr(self.main_window, 'system_info_label'):
                    files_processed = statistics.get('files_processed', 0)
                    documents_added = statistics.get('documents_added', 0)
                    processing_time = statistics.get('processing_time', 0)

                    # 詳細なシステム情報を表示
                    self.main_window.system_info_label.setText(
                        f"インデックス済み: {document_count}ドキュメント | "
                        f"処理済み: {files_processed}ファイル | "
                        f"追加: {documents_added}件 | "
                        f"処理時間: {processing_time:.1f}秒"
                    )

                    # ツールチップに詳細情報を設定
                    self.main_window.system_info_label.setToolTip(
                        f"インデックス再構築完了\n"
                        f"・総ドキュメント数: {document_count}\n"
                        f"・処理ファイル数: {files_processed}\n"
                        f"・新規追加ドキュメント: {documents_added}\n"
                        f"・処理時間: {processing_time:.2f}秒"
                    )

                # 検索機能が新しいインデックスを使用するように更新（要件5.2）
                if hasattr(self.main_window, 'search_manager') and self.main_window.search_manager:
                    # SearchManagerの内部状態を更新
                    # インデックスマネージャーが既に更新されているため、
                    # 次回の検索時に自動的に新しいインデックスが使用されます
                    self.logger.info("検索機能が新しいインデックスを使用するように更新されました")

                self.logger.info(f"システム情報更新完了: {document_count}ドキュメント, {files_processed}ファイル処理")

        except Exception as e:
            self.logger.error(f"システム情報更新でエラー: {e}")

    def update_folder_tree_after_rebuild(self, thread_id: str, statistics: dict) -> None:
        """インデックス再構築後のフォルダツリー状態更新

        Args:
            thread_id: 完了したスレッドID
            statistics: 処理統計情報
        """
        try:
            # スレッド情報を取得
            thread_info = self.main_window.thread_manager.get_thread_info(thread_id)
            if not thread_info:
                self.logger.warning(f"スレッド情報が見つかりません: {thread_id}")
                return

            folder_path = thread_info.folder_path
            files_processed = statistics.get('files_processed', 0)
            documents_added = statistics.get('documents_added', 0)

            # フォルダツリーの状態をINDEXEDに更新
            if hasattr(self.main_window, 'folder_tree_container') and self.main_window.folder_tree_container:
                self.main_window.folder_tree_container.set_folder_indexed(
                    folder_path,
                    files_processed,
                    documents_added
                )
                self.logger.info(f"フォルダツリー状態更新: {folder_path} -> INDEXED ({documents_added}ドキュメント)")

                # フォルダツリーの統計情報を更新
                # set_folder_indexedメソッド内で既に視覚的更新が行われるため、
                # 追加のリフレッシュは不要ですが、統計情報の更新を確実にします
                if hasattr(self.main_window.folder_tree_container, '_update_stats'):
                    self.main_window.folder_tree_container._update_stats()
                    self.logger.debug(f"フォルダツリー統計情報更新完了: {folder_path}")

        except Exception as e:
            self.logger.error(f"フォルダツリー状態更新でエラー: {e}")

    def handle_rebuild_error(self, thread_id: str, error_message: str) -> None:
        """インデックス再構築エラー時の処理

        IndexingThreadManagerのエラーシグナルを受信して、エラータイプ別の
        適切な処理を実行します。

        Args:
            thread_id: エラーが発生したスレッドID
            error_message: エラーメッセージ
        """
        try:
            self.logger.error(f"インデックス再構築エラー発生: {thread_id} - {error_message}")

            # タイムアウト監視をキャンセル
            if hasattr(self.main_window, 'timeout_manager'):
                self.main_window.timeout_manager.cancel_timeout(thread_id)

            # スレッド情報を取得
            thread_info = None
            if hasattr(self.main_window, 'thread_manager'):
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
            self.main_window.dialog_manager.show_fallback_error_dialog(error_message)

    def _analyze_error_type(self, error_message: str) -> str:
        """エラーメッセージを分析してエラータイプを特定

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
        elif any(keyword in error_lower for keyword in ["file not found", "ファイルが見つかりません", "no such file"]):
            return "file_access"

        # 権限関連
        elif any(keyword in error_lower for keyword in ["permission denied", "アクセスが拒否", "権限", "access denied"]):
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

    def _handle_file_access_error(self, thread_id: str, error_message: str, thread_info: Optional[object]) -> None:
        """ファイルアクセスエラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, 'folder_path'):
            folder_path = thread_info.folder_path

        self.logger.warning(f"ファイルアクセスエラー: {folder_path}")

        QMessageBox.warning(
            self.main_window,
            "ファイルアクセスエラー",
            f"一部のファイルにアクセスできませんでした。\n\n"
            f"フォルダ: {folder_path}\n"
            f"エラー詳細: {error_message}\n\n"
            "対処方法:\n"
            "• ファイルの権限を確認してください\n"
            "• 他のアプリケーションでファイルが使用されていないか確認してください\n"
            "• 管理者権限で実行してください\n\n"
            "処理可能なファイルのみでインデックスを作成しました。"
        )

    def _handle_permission_error(self, thread_id: str, error_message: str, thread_info: Optional[object]) -> None:
        """権限エラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, 'folder_path'):
            folder_path = thread_info.folder_path

        self.logger.error(f"権限エラー: {folder_path}")

        # 部分的なインデックスをクリア
        self._cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "権限エラー",
            f"フォルダへのアクセス権限がありません。\n\n"
            f"フォルダ: {folder_path}\n"
            f"エラー詳細: {error_message}\n\n"
            "対処方法:\n"
            "• 管理者権限でアプリケーションを実行してください\n"
            "• フォルダの権限設定を確認してください\n"
            "• 別のフォルダを選択してください\n\n"
            "部分的に処理されたインデックスはクリアされました。"
        )

    def _handle_resource_error(self, thread_id: str, error_message: str, thread_info: Optional[object]) -> None:
        """リソースエラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, 'folder_path'):
            folder_path = thread_info.folder_path

        self.logger.error(f"リソースエラー: {folder_path}")

        # 部分的なインデックスをクリア
        self._cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "リソース不足エラー",
            f"システムリソースが不足しています。\n\n"
            f"フォルダ: {folder_path}\n"
            f"エラー詳細: {error_message}\n\n"
            "対処方法:\n"
            "• 他のアプリケーションを終了してください\n"
            "• より小さなフォルダから開始してください\n"
            "• システムを再起動してください\n\n"
            "部分的に処理されたインデックスはクリアされました。"
        )

    def _handle_disk_space_error(self, thread_id: str, error_message: str, thread_info: Optional[object]) -> None:
        """ディスク容量エラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, 'folder_path'):
            folder_path = thread_info.folder_path

        self.logger.error(f"ディスク容量エラー: {folder_path}")

        # 部分的なインデックスをクリア
        self._cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "ディスク容量不足エラー",
            f"ディスク容量が不足しています。\n\n"
            f"フォルダ: {folder_path}\n"
            f"エラー詳細: {error_message}\n\n"
            "対処方法:\n"
            "• 不要なファイルを削除してください\n"
            "• 一時ファイルをクリアしてください\n"
            "• より小さなフォルダから開始してください\n\n"
            "部分的に処理されたインデックスはクリアされました。"
        )

    def _handle_corruption_error(self, thread_id: str, error_message: str, thread_info: Optional[object]) -> None:
        """データ破損エラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, 'folder_path'):
            folder_path = thread_info.folder_path

        self.logger.error(f"データ破損エラー: {folder_path}")

        # インデックス全体をクリア（破損の可能性があるため）
        self._cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "データ破損エラー",
            f"ファイルまたはインデックスデータが破損しています。\n\n"
            f"フォルダ: {folder_path}\n"
            f"エラー詳細: {error_message}\n\n"
            "対処方法:\n"
            "• ファイルシステムをチェックしてください\n"
            "• 破損したファイルを修復または削除してください\n"
            "• インデックスを完全に再構築してください\n\n"
            "既存のインデックスはクリアされました。"
        )

    def _handle_system_error(self, thread_id: str, error_message: str, thread_info: Optional[object]) -> None:
        """システムエラーの処理"""
        folder_path = "不明なフォルダ"
        if thread_info and hasattr(thread_info, 'folder_path'):
            folder_path = thread_info.folder_path

        self.logger.error(f"システムエラー: {folder_path}")

        # 部分的なインデックスをクリア
        self._cleanup_partial_index()

        QMessageBox.critical(
            self.main_window,
            "システムエラー",
            f"インデックス再構築中にシステムエラーが発生しました。\n\n"
            f"フォルダ: {folder_path}\n"
            f"エラー詳細: {error_message}\n\n"
            "対処方法:\n"
            "• しばらく待ってから再試行してください\n"
            "• システムを再起動してください\n"
            "• より小さなフォルダから開始してください\n\n"
            "部分的に処理されたインデックスはクリアされました。"
        )

    def _cleanup_partial_index(self) -> None:
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

    def _perform_error_cleanup(self, thread_id: str, error_type: str, thread_info: Optional[object]) -> None:
        """エラー後の共通クリーンアップ処理

        Args:
            thread_id: スレッドID
            error_type: エラータイプ
            thread_info: スレッド情報
        """
        try:
            # フォルダツリーの状態を更新
            if thread_info and hasattr(thread_info, 'folder_path'):
                if hasattr(self.main_window, 'folder_tree_container'):
                    self.main_window.folder_tree_container.set_folder_error(
                        thread_info.folder_path,
                        f"{error_type}エラー"
                    )

            # システム情報を更新
            if hasattr(self.main_window, 'thread_manager'):
                active_count = self.main_window.thread_manager.get_active_thread_count()
                indexed_count = 0
                if hasattr(self.main_window, 'folder_tree_container'):
                    indexed_count = len(self.main_window.folder_tree_container.get_indexed_folders())

                if active_count > 0:
                    self.main_window.update_system_info(f"インデックス: {indexed_count}フォルダ, 処理中: {active_count}スレッド (エラー発生)")
                else:
                    self.main_window.update_system_info(f"インデックス: {indexed_count}フォルダ, エラーで停止")

            self.logger.info(f"エラークリーンアップ完了: {thread_id} ({error_type})")

        except Exception as e:
            self.logger.error(f"エラークリーンアップでエラー: {e}")