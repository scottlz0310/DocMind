#!/usr/bin/env python3
"""
DocMind イベント・UI処理管理マネージャー

フォルダ、検索結果、プレビューなどのUIイベント処理を管理します。
main_window.pyから分離されたイベント処理関連の処理を統合管理します。
"""

import os
from typing import Any

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from src.utils.logging_config import LoggerMixin


class EventUIManager(QObject, LoggerMixin):
    """
    イベント・UI処理管理マネージャー

    フォルダ、検索結果、プレビューなどのUIイベント処理を管理します。
    メインウィンドウからイベント処理関連の責務を分離し、独立した管理を提供します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        イベント・UI処理管理マネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(parent=main_window)
        self.main_window = main_window
        self.logger.info("イベント・UI処理管理マネージャーが初期化されました")

    def handle_folder_excluded(self, folder_path: str) -> None:
        """
        フォルダが除外された時の処理

        Args:
            folder_path: 除外されたフォルダのパス
        """
        try:
            self.logger.info(f"フォルダが除外されました: {folder_path}")

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(
                    f"除外: {os.path.basename(folder_path)}", 3000
                )

            # システム情報を更新
            self._update_folder_system_info()

        except Exception as e:
            self.logger.error(f"フォルダ除外処理でエラー: {e}")

    def handle_folder_refresh(self) -> None:
        """
        フォルダツリーがリフレッシュされた時の処理
        """
        try:
            self.logger.info("フォルダツリーがリフレッシュされました")

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(
                    "フォルダツリーを更新しました", 2000
                )

            # システム情報を更新
            self._update_folder_system_info()

        except Exception as e:
            self.logger.error(f"フォルダリフレッシュ処理でエラー: {e}")

    def _update_folder_system_info(self) -> None:
        """フォルダ関連のシステム情報を更新"""
        try:
            indexed_count = 0
            excluded_count = 0

            if hasattr(self.main_window, "folder_tree_container"):
                indexed_count = len(
                    self.main_window.folder_tree_container.get_indexed_folders()
                )
                excluded_count = len(
                    self.main_window.folder_tree_container.get_excluded_folders()
                )

            info_text = f"インデックス: {indexed_count}フォルダ"
            if excluded_count > 0:
                info_text += f", 除外: {excluded_count}フォルダ"

            if hasattr(self.main_window, "update_system_info"):
                self.main_window.update_system_info(info_text)

        except Exception as e:
            self.logger.warning(f"フォルダシステム情報の更新に失敗: {e}")

    def handle_search_result_selected(self, result) -> None:
        """
        検索結果が選択された時の処理

        Args:
            result: 選択された検索結果
        """
        try:
            self.logger.info(f"検索結果が選択されました: {result.document.title}")

            # シグナルを発信
            if hasattr(self.main_window, "document_selected"):
                self.main_window.document_selected.emit(result.document.file_path)

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(
                    f"選択: {result.document.title}", 3000
                )

            # プレビューペインに内容を表示
            if hasattr(self.main_window, "preview_widget"):
                self.main_window.preview_widget.display_document(result.document)

                # 検索語をハイライト
                if hasattr(result, "highlighted_terms") and result.highlighted_terms:
                    self.main_window.preview_widget.highlight_search_terms(
                        result.highlighted_terms
                    )

        except Exception as e:
            self.logger.error(f"検索結果選択処理でエラー: {e}")

    def handle_preview_requested(self, result) -> None:
        """
        プレビューが要求された時の処理

        Args:
            result: プレビューが要求された検索結果
        """
        try:
            self.logger.info(f"プレビューが要求されました: {result.document.title}")

            # シグナルを発信
            if hasattr(self.main_window, "document_selected"):
                self.main_window.document_selected.emit(result.document.file_path)

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(
                    f"プレビュー: {result.document.title}", 3000
                )

            # プレビューペインに内容を表示
            if hasattr(self.main_window, "preview_widget"):
                self.main_window.preview_widget.display_document(result.document)

                # 検索語をハイライト
                if hasattr(result, "highlighted_terms") and result.highlighted_terms:
                    self.main_window.preview_widget.highlight_search_terms(
                        result.highlighted_terms
                    )

        except Exception as e:
            self.logger.error(f"プレビュー要求処理でエラー: {e}")

    def handle_page_changed(self, page: int) -> None:
        """
        ページが変更された時の処理

        Args:
            page: 新しいページ番号
        """
        try:
            self.logger.debug(f"検索結果のページが変更されました: {page}")

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(f"ページ {page} を表示中", 2000)

        except Exception as e:
            self.logger.error(f"ページ変更処理でエラー: {e}")

    def handle_sort_changed(self, sort_order) -> None:
        """
        ソート順が変更された時の処理

        Args:
            sort_order: 新しいソート順
        """
        try:
            self.logger.debug(f"検索結果のソート順が変更されました: {sort_order}")

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message("検索結果を並び替えました", 2000)

        except Exception as e:
            self.logger.error(f"ソート変更処理でエラー: {e}")

    def handle_filter_changed(self, filters: dict[str, Any]) -> None:
        """
        フィルターが変更された時の処理

        Args:
            filters: 新しいフィルター設定
        """
        try:
            self.logger.debug(f"検索結果のフィルターが変更されました: {filters}")

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(
                    "検索結果をフィルタリングしました", 2000
                )

        except Exception as e:
            self.logger.error(f"フィルター変更処理でエラー: {e}")

    def handle_preview_zoom_changed(self, zoom_level: int) -> None:
        """
        プレビューのズームレベルが変更された時の処理

        Args:
            zoom_level: 新しいズームレベル
        """
        try:
            self.logger.debug(
                f"プレビューのズームレベルが変更されました: {zoom_level}%"
            )

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(f"ズーム: {zoom_level}%", 2000)

        except Exception as e:
            self.logger.error(f"ズーム変更処理でエラー: {e}")

    def handle_preview_format_changed(self, format_name: str) -> None:
        """
        プレビューの表示フォーマットが変更された時の処理

        Args:
            format_name: 新しい表示フォーマット名
        """
        try:
            self.logger.debug(
                f"プレビューの表示フォーマットが変更されました: {format_name}"
            )

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(f"表示形式: {format_name}", 2000)

        except Exception as e:
            self.logger.error(f"フォーマット変更処理でエラー: {e}")

    def handle_document_opened(self, file_path: str) -> None:
        """
        ドキュメントが開かれた時の処理

        Args:
            file_path: 開かれたドキュメントのファイルパス
        """
        try:
            self.logger.info(f"ドキュメントが開かれました: {file_path}")

            file_name = os.path.basename(file_path)
            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(f"開く: {file_name}", 3000)

        except Exception as e:
            self.logger.error(f"ドキュメント開く処理でエラー: {e}")

    def handle_export_requested(self, export_format: str, file_path: str) -> None:
        """
        エクスポートが要求された時の処理

        Args:
            export_format: エクスポート形式
            file_path: エクスポート先ファイルパス
        """
        try:
            self.logger.info(
                f"エクスポートが要求されました: {export_format} -> {file_path}"
            )

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(
                    f"エクスポート中: {export_format}", 3000
                )

        except Exception as e:
            self.logger.error(f"エクスポート処理でエラー: {e}")

    def handle_print_requested(self, document_title: str) -> None:
        """
        印刷が要求された時の処理

        Args:
            document_title: 印刷対象ドキュメントのタイトル
        """
        try:
            self.logger.info(f"印刷が要求されました: {document_title}")

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(f"印刷中: {document_title}", 3000)

        except Exception as e:
            self.logger.error(f"印刷処理でエラー: {e}")

    def handle_bookmark_added(
        self, document_path: str, page_number: int | None = None
    ) -> None:
        """
        ブックマークが追加された時の処理

        Args:
            document_path: ブックマーク対象ドキュメントのパス
            page_number: ページ番号（オプション）
        """
        try:
            document_name = os.path.basename(document_path)
            if page_number:
                self.logger.info(
                    f"ブックマークが追加されました: {document_name} (ページ {page_number})"
                )
                status_message = f"ブックマーク追加: {document_name} (p.{page_number})"
            else:
                self.logger.info(f"ブックマークが追加されました: {document_name}")
                status_message = f"ブックマーク追加: {document_name}"

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(status_message, 3000)

        except Exception as e:
            self.logger.error(f"ブックマーク追加処理でエラー: {e}")

    def handle_annotation_added(self, document_path: str, annotation_text: str) -> None:
        """
        注釈が追加された時の処理

        Args:
            document_path: 注釈対象ドキュメントのパス
            annotation_text: 注釈テキスト
        """
        try:
            document_name = os.path.basename(document_path)
            self.logger.info(
                f"注釈が追加されました: {document_name} - {annotation_text[:50]}..."
            )

            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(f"注釈追加: {document_name}", 3000)

        except Exception as e:
            self.logger.error(f"注釈追加処理でエラー: {e}")
