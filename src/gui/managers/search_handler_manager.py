#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind 検索・プレビューハンドラーマネージャー

検索要求・完了・エラー、プレビュー操作、検索結果表示のイベント処理を専門的に管理します。
検索ワーカースレッド管理、結果表示、プレビュー制御を統合処理します。
"""

from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from src.gui.search.widgets.worker_thread import SearchWorkerThread
from src.utils.logging_config import LoggerMixin


class SearchHandlerManager(QObject, LoggerMixin):
    """
    検索・プレビューハンドラーマネージャー
    
    検索関連のイベント処理を専門的に管理し、
    検索実行、結果表示、プレビュー制御を統合処理します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        検索・プレビューハンドラーマネージャーの初期化
        
        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window
        self.search_worker: Optional[SearchWorkerThread] = None
        
        self.logger.debug("検索・プレビューハンドラーマネージャーが初期化されました")

    def handle_search_requested(self, search_query) -> None:
        """検索要求時の処理

        Args:
            search_query: 検索クエリオブジェクト
        """
        self.logger.info(f"検索要求: '{search_query.query_text}' ({search_query.search_type.value})")

        if not hasattr(self.main_window, 'search_manager') or self.main_window.search_manager is None:
            error_msg = "検索機能が初期化されていません"
            self.logger.error(error_msg)
            self.main_window.search_interface.on_search_error(error_msg)
            return

        self.main_window.show_status_message(f"検索実行: '{search_query.query_text}'", 3000)

        # 検索ワーカースレッドを作成して実行
        self.search_worker = SearchWorkerThread(self.main_window.search_manager, search_query)
        self.search_worker.progress_updated.connect(self.main_window.search_interface.progress_widget.update_progress)
        self.search_worker.search_completed.connect(self.handle_search_completed)
        self.search_worker.search_error.connect(self.handle_search_error)
        self.search_worker.start()

    def handle_search_cancelled(self) -> None:
        """検索キャンセル時の処理"""
        self.logger.info("検索がキャンセルされました")
        self.main_window.show_status_message("検索がキャンセルされました", 3000)

        # 実際の検索キャンセル処理
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.cancel()
            self.search_worker.wait()

    def handle_search_completed(self, results, execution_time: float) -> None:
        """検索完了時の処理

        Args:
            results: 検索結果
            execution_time: 実行時間（秒）
        """
        self.logger.info(f"検索完了: {len(results)}件, {execution_time:.1f}秒")

        # 検索結果を表示
        self.main_window.search_results_widget.display_results(results)

        # 検索インターフェースに完了を通知
        self.main_window.search_interface.on_search_completed(results, execution_time)

        # ステータス更新
        result_count = len(results)
        self.main_window.show_status_message(f"検索完了: {result_count}件の結果 ({execution_time:.1f}秒)", 5000)

    def handle_search_error(self, error_message: str) -> None:
        """検索エラー時の処理

        Args:
            error_message: エラーメッセージ
        """
        self.logger.error(f"検索エラー: {error_message}")

        # 検索インターフェースにエラーを通知
        self.main_window.search_interface.on_search_error(error_message)

        # ステータス更新
        self.main_window.show_status_message("検索エラーが発生しました", 5000)

    def handle_search_text_changed(self, text: str) -> None:
        """検索テキスト変更時の処理（検索提案を更新）

        Args:
            text: 入力されたテキスト
        """
        if hasattr(self.main_window, 'search_manager') and self.main_window.search_manager and len(text.strip()) >= 2:
            try:
                suggestions = self.main_window.search_manager.get_search_suggestions(text.strip(), limit=10)
                self.main_window.search_interface.update_search_suggestions(suggestions)
            except Exception as e:
                self.logger.debug(f"検索提案の取得に失敗: {e}")
                # エラーが発生しても検索提案は必須機能ではないため、ログのみ出力

    def handle_search_result_selected(self, result) -> None:
        """検索結果が選択された時の処理

        Args:
            result: 選択された検索結果
        """
        self.logger.info(f"検索結果が選択されました: {result.document.title}")
        self.main_window.document_selected.emit(result.document.file_path)
        self.main_window.show_status_message(f"選択: {result.document.title}", 3000)

        # プレビューペインに内容を表示
        self.main_window.preview_widget.display_document(result.document)

        # 検索語をハイライト
        if hasattr(result, 'highlighted_terms') and result.highlighted_terms:
            self.main_window.preview_widget.highlight_search_terms(result.highlighted_terms)

    def handle_preview_requested(self, result) -> None:
        """プレビューが要求された時の処理

        Args:
            result: プレビューが要求された検索結果
        """
        self.logger.info(f"プレビューが要求されました: {result.document.title}")
        self.main_window.document_selected.emit(result.document.file_path)
        self.main_window.show_status_message(f"プレビュー: {result.document.title}", 3000)

        # プレビューペインに内容を表示
        self.main_window.preview_widget.display_document(result.document)

        # 検索語をハイライト
        if hasattr(result, 'highlighted_terms') and result.highlighted_terms:
            self.main_window.preview_widget.highlight_search_terms(result.highlighted_terms)

    def handle_page_changed(self, page: int) -> None:
        """ページが変更された時の処理

        Args:
            page: 新しいページ番号
        """
        self.logger.debug(f"検索結果のページが変更されました: {page}")
        self.main_window.show_status_message(f"ページ {page} を表示中", 2000)

    def handle_sort_changed(self, sort_order) -> None:
        """ソート順が変更された時の処理

        Args:
            sort_order: 新しいソート順
        """
        self.logger.debug(f"検索結果のソート順が変更されました: {sort_order}")
        self.main_window.show_status_message("検索結果を並び替えました", 2000)

    def handle_filter_changed(self, filters: dict) -> None:
        """フィルターが変更された時の処理

        Args:
            filters: 新しいフィルター設定
        """
        self.logger.debug(f"検索結果のフィルターが変更されました: {filters}")
        self.main_window.show_status_message("検索結果をフィルタリングしました", 2000)

    def handle_preview_zoom_changed(self, zoom_level: int) -> None:
        """プレビューのズームレベルが変更された時の処理

        Args:
            zoom_level: 新しいズームレベル
        """
        self.logger.debug(f"プレビューのズームレベルが変更されました: {zoom_level}%")
        self.main_window.show_status_message(f"ズーム: {zoom_level}%", 2000)

    def handle_preview_format_changed(self, format_name: str) -> None:
        """プレビューの表示フォーマットが変更された時の処理

        Args:
            format_name: 新しい表示フォーマット名
        """
        self.logger.debug(f"プレビューの表示フォーマットが変更されました: {format_name}")
        self.main_window.show_status_message(f"表示形式: {format_name}", 2000)

    def cleanup(self) -> None:
        """検索・プレビューハンドラーマネージャーのクリーンアップ"""
        try:
            # 実行中の検索ワーカーを停止
            if self.search_worker and self.search_worker.isRunning():
                self.search_worker.cancel()
                self.search_worker.wait()
                self.search_worker = None
            
            self.logger.debug("検索・プレビューハンドラーマネージャーをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"検索・プレビューハンドラーマネージャーのクリーンアップ中にエラー: {e}")