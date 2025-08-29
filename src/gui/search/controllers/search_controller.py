#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索ロジック制御

検索実行、クエリ構築、検索状態管理を担当します。
"""

import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from ....data.models import SearchQuery, SearchType


class SearchController(QObject):
    """
    検索ロジック制御クラス
    
    検索実行、クエリ構築、検索状態管理を担当します。
    """
    
    # シグナル定義
    search_requested = Signal(SearchQuery)  # 検索が要求された時
    search_cancelled = Signal()             # 検索がキャンセルされた時
    search_state_changed = Signal(bool)     # 検索状態が変更された時
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        検索コントローラーを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.is_searching = False
        
    def execute_search(self, query_text: str, search_type: SearchType, 
                      search_options: Dict[str, Any]) -> None:
        """
        検索を実行
        
        Args:
            query_text: 検索テキスト
            search_type: 検索タイプ
            search_options: 検索オプション
        """
        if self.is_searching:
            self.logger.warning("既に検索が実行中です")
            return
            
        if not query_text.strip():
            QMessageBox.warning(None, "検索エラー", "検索キーワードを入力してください。")
            return
            
        try:
            # 検索クエリを構築
            search_query = self._build_search_query(query_text, search_type, search_options)
            
            # 検索状態を更新
            self._set_searching_state(True)
            
            # 検索要求シグナルを発行
            self.search_requested.emit(search_query)
            
            self.logger.info(f"検索実行: '{query_text}' ({search_type.value})")
            
        except Exception as e:
            self.logger.error(f"検索実行エラー: {e}")
            QMessageBox.critical(None, "検索エラー", f"検索の実行に失敗しました:\n{e}")
            self._set_searching_state(False)
    
    def cancel_search(self) -> None:
        """検索をキャンセル"""
        if self.is_searching:
            self.search_cancelled.emit()
            self._set_searching_state(False)
            self.logger.info("検索がキャンセルされました")
    
    def on_search_completed(self, results: list, execution_time: float) -> None:
        """
        検索完了時の処理
        
        Args:
            results: 検索結果
            execution_time: 実行時間（秒）
        """
        self._set_searching_state(False)
        result_count = len(results)
        self.logger.info(f"検索完了: {result_count}件, {execution_time:.1f}秒")
    
    def on_search_error(self, error_message: str) -> None:
        """
        検索エラー時の処理
        
        Args:
            error_message: エラーメッセージ
        """
        self._set_searching_state(False)
        QMessageBox.critical(None, "検索エラー", f"検索中にエラーが発生しました:\n{error_message}")
        self.logger.error(f"検索エラー: {error_message}")
    
    def _build_search_query(self, query_text: str, search_type: SearchType, 
                           options: Dict[str, Any]) -> SearchQuery:
        """
        検索クエリオブジェクトを構築
        
        Args:
            query_text: 検索テキスト
            search_type: 検索タイプ
            options: 検索オプション
            
        Returns:
            構築された検索クエリ
        """
        return SearchQuery(
            query_text=query_text,
            search_type=search_type,
            limit=options.get('limit', 100),
            file_types=options.get('file_types', []),
            date_from=options.get('date_from'),
            date_to=options.get('date_to'),
            weights=options.get('weights', {'full_text': 0.6, 'semantic': 0.4})
        )
    
    def _set_searching_state(self, is_searching: bool) -> None:
        """
        検索状態を設定
        
        Args:
            is_searching: 検索中かどうか
        """
        if self.is_searching != is_searching:
            self.is_searching = is_searching
            self.search_state_changed.emit(is_searching)
    
    def get_searching_state(self) -> bool:
        """現在の検索状態を取得"""
        return self.is_searching