#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索UI管理

検索インターフェースのUI状態管理を担当します。
"""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from ....data.models import SearchType


class SearchUIManager(QObject):
    """
    検索UI管理クラス
    
    検索インターフェースのUI状態管理を担当します。
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        検索UI管理を初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        
    def update_search_button_state(self, search_button, is_searching: bool) -> None:
        """
        検索ボタンの状態を更新
        
        Args:
            search_button: 検索ボタン
            is_searching: 検索中かどうか
        """
        search_button.setEnabled(not is_searching)
        search_button.setText("検索中..." if is_searching else "検索")
    
    def update_search_suggestions(self, search_input, suggestions: List[str]) -> None:
        """
        検索提案を更新
        
        Args:
            search_input: 検索入力ウィジェット
            suggestions: 提案リスト
        """
        search_input.update_suggestions(suggestions)
    
    def update_search_history(self, history_widget, recent_searches: List[Dict[str, Any]],
                            popular_searches: List[Dict[str, Any]],
                            saved_searches: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        検索履歴を更新
        
        Args:
            history_widget: 履歴ウィジェット
            recent_searches: 最近の検索リスト
            popular_searches: 人気の検索リスト
            saved_searches: 保存された検索リスト
        """
        history_widget.update_recent_searches(recent_searches)
        history_widget.update_popular_searches(popular_searches)
        
        if saved_searches is not None:
            history_widget.update_saved_searches(saved_searches)
    
    def set_interface_enabled(self, search_input, search_button, search_type_selector,
                            advanced_options, enabled: bool, is_searching: bool = False) -> None:
        """
        インターフェースの有効/無効を設定
        
        Args:
            search_input: 検索入力ウィジェット
            search_button: 検索ボタン
            search_type_selector: 検索タイプ選択
            advanced_options: 高度なオプション
            enabled: 有効かどうか
            is_searching: 検索中かどうか
        """
        search_input.setEnabled(enabled)
        search_button.setEnabled(enabled and not is_searching)
        search_type_selector.setEnabled(enabled)
        advanced_options.setEnabled(enabled)
    
    def clear_search_interface(self, search_input, advanced_options, progress_widget) -> None:
        """
        検索インターフェースをクリア
        
        Args:
            search_input: 検索入力ウィジェット
            advanced_options: 高度なオプション
            progress_widget: 進捗ウィジェット
        """
        search_input.clear()
        search_input.setFocus()
        advanced_options.reset_to_defaults()
        progress_widget.finish_search("")
        
        self.logger.info("検索インターフェースをクリアしました")
    
    def handle_search_type_change(self, search_type: SearchType, advanced_options) -> None:
        """
        検索タイプ変更時の処理
        
        Args:
            search_type: 変更された検索タイプ
            advanced_options: 高度なオプション
        """
        self.logger.debug(f"検索タイプ変更: {search_type.value}")
        
        # ハイブリッド検索以外では重み設定を無効化
        weights_group = advanced_options.findChild(QWidget, "ハイブリッド検索の重み設定")
        if weights_group:
            weights_group.setEnabled(search_type == SearchType.HYBRID)