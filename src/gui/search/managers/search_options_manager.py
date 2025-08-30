#!/usr/bin/env python3
"""
検索オプション管理

検索オプションの適用・管理を担当します。
"""

import logging
from typing import Any

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget


class SearchOptionsManager(QObject):
    """
    検索オプション管理クラス

    検索オプションの適用・管理を担当します。
    """

    def __init__(self, parent: QWidget | None = None):
        """
        検索オプション管理を初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

    def apply_search_options(self, options: dict[str, Any], advanced_options) -> None:
        """
        検索オプションを適用

        Args:
            options: 適用するオプション
            advanced_options: 高度なオプションウィジェット
        """
        try:
            # ファイルタイプフィルター
            if "file_types" in options:
                self._apply_file_type_filters(options["file_types"], advanced_options)

            # 日付範囲
            if "date_from" in options and "date_to" in options:
                self._apply_date_range(
                    options["date_from"], options["date_to"], advanced_options
                )

            # 結果数制限
            if "limit" in options:
                self._apply_result_limit(options["limit"], advanced_options)

            # 重み設定
            if "weights" in options:
                self._apply_weights(options["weights"], advanced_options)

        except Exception as e:
            self.logger.error(f"検索オプション適用エラー: {e}")

    def _apply_file_type_filters(self, file_types: list, advanced_options) -> None:
        """ファイルタイプフィルターを適用"""
        for file_type, checkbox in advanced_options.file_type_checkboxes.items():
            checkbox.setChecked(file_type.value in file_types)

    def _apply_date_range(self, date_from, date_to, advanced_options) -> None:
        """日付範囲を適用"""
        if date_from and date_to:
            advanced_options.date_filter_enabled.setChecked(True)
            # TODO: 日付の設定処理を実装

    def _apply_result_limit(self, limit: int, advanced_options) -> None:
        """結果数制限を適用"""
        advanced_options.result_limit.setValue(limit)

    def _apply_weights(self, weights: dict[str, float], advanced_options) -> None:
        """重み設定を適用"""
        if "full_text" in weights:
            advanced_options.full_text_weight.setValue(int(weights["full_text"] * 100))
        if "semantic" in weights:
            advanced_options.semantic_weight.setValue(int(weights["semantic"] * 100))
