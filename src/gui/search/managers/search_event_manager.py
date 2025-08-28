#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索イベント管理

検索インターフェースのイベント処理を担当します。
"""

import logging
from typing import Any, Dict

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

from ....data.models import SearchType


class SearchEventManager(QObject):
    """
    検索イベント管理クラス
    
    検索インターフェースのイベント処理を担当します。
    """
    
    def __init__(self, parent: QWidget = None):
        """
        検索イベント管理を初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.parent_widget = parent
        
    def handle_suggestion_selected(self, suggestion: str, search_input, execute_callback) -> None:
        """検索提案選択時の処理"""
        search_input.setText(suggestion)
        execute_callback()
        
    def handle_search_type_changed(self, search_type: SearchType, ui_manager, advanced_options) -> None:
        """検索タイプ変更時の処理"""
        ui_manager.handle_search_type_change(search_type, advanced_options)
        
    def handle_options_changed(self, options: Dict[str, Any]) -> None:
        """検索オプション変更時の処理"""
        self.logger.debug(f"検索オプション変更: {options}")
        
    def handle_history_selected(self, query: str, search_input) -> None:
        """検索履歴選択時の処理"""
        search_input.setText(query)
        search_input.setFocus()
        self.logger.debug(f"検索履歴選択: {query}")
        
    def handle_history_deleted(self, query: str) -> None:
        """検索履歴削除時の処理"""
        self.logger.info(f"検索履歴削除: {query}")
        # TODO: 実際の履歴削除処理を実装
        
    def handle_search_save_requested(self, query: str) -> None:
        """検索保存要求時の処理"""
        name, ok = QInputDialog.getText(
            self.parent_widget,
            "検索を保存",
            f"検索「{query}」の保存名を入力してください:",
            text=query
        )

        if ok and name.strip():
            # TODO: 実際の検索保存処理を実装
            self.logger.info(f"検索保存要求: {name} - {query}")
            QMessageBox.information(self.parent_widget, "保存完了", f"検索「{name}」を保存しました。")
            
    def handle_saved_search_selected(self, search_data: Dict[str, Any], search_input, 
                                   search_type_selector, apply_options_callback) -> None:
        """保存された検索選択時の処理"""
        query = search_data['query']
        search_type = search_data['search_type']
        search_options = search_data.get('search_options', {})

        # 検索テキストを設定
        search_input.setText(query)

        # 検索タイプを設定
        search_type_selector.set_search_type(search_type)

        # 検索オプションを設定
        if search_options:
            apply_options_callback(search_options)

        self.logger.info(f"保存された検索選択: {search_data['name']}")
        
    def handle_saved_search_deleted(self, search_id: int) -> None:
        """保存された検索削除時の処理"""
        self.logger.info(f"保存された検索削除: ID {search_id}")
        # TODO: 実際の削除処理を実装