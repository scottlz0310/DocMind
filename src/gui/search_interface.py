#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索インターフェースウィジェット

分離されたコンポーネントを統合した検索インターフェースを提供します。
"""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

from ..data.models import SearchQuery, SearchType
from .search.widgets.input_widget import SearchInputWidget
from .search.widgets.type_selector import SearchTypeSelector
from .search.widgets.advanced_options import AdvancedSearchOptions
from .search.widgets.progress_widget import SearchProgressWidget
from .search.widgets.history_widget import SearchHistoryWidget




class SearchInterface(QWidget):
    """
    統合検索インターフェースウィジェット

    分離されたコンポーネントを統合した検索インターフェースを提供します。
    """

    # シグナル定義
    search_requested = Signal(SearchQuery)  # 検索が要求された時
    search_cancelled = Signal()             # 検索がキャンセルされた時

    def __init__(self, parent: Optional[QWidget] = None):
        """
        統合検索インターフェースを初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.is_searching = False

        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        """UIの設定"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # メイン検索エリア
        main_search_frame = QFrame()
        main_search_frame.setFrameStyle(QFrame.StyledPanel)
        main_search_layout = QVBoxLayout(main_search_frame)

        # 検索入力行
        search_input_layout = QHBoxLayout()

        # 検索入力ウィジェット
        self.search_input = SearchInputWidget()
        self.search_input.setMinimumWidth(400)
        search_input_layout.addWidget(self.search_input)

        # 検索ボタン
        self.search_button = QPushButton("検索")
        self.search_button.setMinimumWidth(80)
        self.search_button.setMinimumHeight(35)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        search_input_layout.addWidget(self.search_button)

        # クリアボタン
        self.clear_button = QPushButton("クリア")
        self.clear_button.setMinimumWidth(80)
        self.clear_button.setMinimumHeight(35)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        search_input_layout.addWidget(self.clear_button)

        main_search_layout.addLayout(search_input_layout)

        # 検索タイプ選択
        self.search_type_selector = SearchTypeSelector()
        main_search_layout.addWidget(self.search_type_selector)

        layout.addWidget(main_search_frame)

        # 進捗表示ウィジェット
        self.progress_widget = SearchProgressWidget()
        layout.addWidget(self.progress_widget)

        # 高度な検索オプション
        self.advanced_options = AdvancedSearchOptions()
        layout.addWidget(self.advanced_options)

        # 検索履歴ウィジェット
        self.history_widget = SearchHistoryWidget()
        layout.addWidget(self.history_widget)

        # スペーサー
        layout.addStretch()

        # 全体のスタイル設定
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)

    def _setup_connections(self) -> None:
        """シグナル接続の設定"""
        # 検索実行
        self.search_input.search_requested.connect(self._execute_search)
        self.search_button.clicked.connect(self._execute_search)

        # クリアボタン
        self.clear_button.clicked.connect(self._clear_all)

        # 検索提案選択
        self.search_input.suggestion_selected.connect(self._on_suggestion_selected)

        # 検索タイプ変更
        self.search_type_selector.search_type_changed.connect(self._on_search_type_changed)

        # 高度なオプション変更
        self.advanced_options.options_changed.connect(self._on_options_changed)

        # 進捗キャンセル
        self.progress_widget.cancel_requested.connect(self._cancel_search)

        # 履歴選択
        self.history_widget.history_selected.connect(self._on_history_selected)
        self.history_widget.history_deleted.connect(self._on_history_deleted)

        # 保存された検索
        self.history_widget.search_save_requested.connect(self._on_search_save_requested)
        self.history_widget.saved_search_selected.connect(self._on_saved_search_selected)
        self.history_widget.saved_search_deleted.connect(self._on_saved_search_deleted)

    def _setup_shortcuts(self) -> None:
        """キーボードショートカットの設定"""
        # Ctrl+Enterで検索実行
        search_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        search_shortcut.activated.connect(self._execute_search)

        # F3で高度なオプション切り替え
        options_shortcut = QShortcut(QKeySequence("F3"), self)
        options_shortcut.activated.connect(self._toggle_advanced_options)

    def _execute_search(self) -> None:
        """検索を実行"""
        if self.is_searching:
            self.logger.warning("既に検索が実行中です")
            return

        query_text = self.search_input.text().strip()
        if not query_text:
            QMessageBox.warning(self, "検索エラー", "検索キーワードを入力してください。")
            self.search_input.setFocus()
            return

        try:
            # 検索クエリを構築
            search_query = self._build_search_query(query_text)

            # 検索状態を更新
            self.is_searching = True
            self.search_button.setEnabled(False)
            self.search_button.setText("検索中...")

            # 進捗表示開始
            self.progress_widget.start_search(f"'{query_text}' を検索中...")

            # 検索要求シグナルを発行
            self.search_requested.emit(search_query)

            self.logger.info(f"検索実行: '{query_text}' ({search_query.search_type.value})")

        except Exception as e:
            self.logger.error(f"検索実行エラー: {e}")
            QMessageBox.critical(self, "検索エラー", f"検索の実行に失敗しました:\n{e}")
            self._reset_search_state()

    def _build_search_query(self, query_text: str) -> SearchQuery:
        """検索クエリオブジェクトを構築"""
        search_type = self.search_type_selector.get_search_type()
        options = self.advanced_options.get_search_options()

        return SearchQuery(
            query_text=query_text,
            search_type=search_type,
            limit=options['limit'],
            file_types=options['file_types'],
            date_from=options['date_from'],
            date_to=options['date_to'],
            weights=options['weights']
        )

    def _cancel_search(self) -> None:
        """検索をキャンセル"""
        if self.is_searching:
            self.search_cancelled.emit()
            self.progress_widget.finish_search("検索がキャンセルされました")
            self._reset_search_state()
            self.logger.info("検索がキャンセルされました")

    def _reset_search_state(self) -> None:
        """検索状態をリセット"""
        self.is_searching = False
        self.search_button.setEnabled(True)
        self.search_button.setText("検索")

    def _clear_all(self) -> None:
        """すべての検索関連データをクリア"""
        try:
            # 検索入力フィールドをクリア
            self.search_input.clear()
            self.search_input.setFocus()

            # 検索状態をリセット
            self._reset_search_state()

            # 高度なオプションをデフォルトにリセット
            self.advanced_options.reset_to_defaults()

            # 進捗表示をクリア
            self.progress_widget.finish_search("")

            self.logger.info("検索インターフェースをクリアしました")

        except Exception as e:
            self.logger.error(f"クリア処理に失敗しました: {e}")
            QMessageBox.warning(self, "警告", f"クリア処理に失敗しました:\n{e}")

    def _on_suggestion_selected(self, suggestion: str) -> None:
        """検索提案選択時の処理"""
        self.search_input.setText(suggestion)
        self._execute_search()

    def _on_search_type_changed(self, search_type: SearchType) -> None:
        """検索タイプ変更時の処理"""
        self.logger.debug(f"検索タイプ変更: {search_type.value}")

        # ハイブリッド検索以外では重み設定を無効化
        weights_group = self.advanced_options.findChild(QGroupBox, "ハイブリッド検索の重み設定")
        if weights_group:
            weights_group.setEnabled(search_type == SearchType.HYBRID)

    def _on_options_changed(self, options: Dict[str, Any]) -> None:
        """検索オプション変更時の処理"""
        self.logger.debug(f"検索オプション変更: {options}")

    def _on_history_selected(self, query: str) -> None:
        """検索履歴選択時の処理"""
        self.search_input.setText(query)
        self.search_input.setFocus()
        self.logger.debug(f"検索履歴選択: {query}")

    def _on_history_deleted(self, query: str) -> None:
        """検索履歴削除時の処理"""
        self.logger.info(f"検索履歴削除: {query}")
        # TODO: 実際の履歴削除処理を実装

    def _on_search_save_requested(self, query: str) -> None:
        """検索保存要求時の処理"""
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            "検索を保存",
            f"検索「{query}」の保存名を入力してください:",
            text=query
        )

        if ok and name.strip():
            # TODO: 実際の検索保存処理を実装
            self.logger.info(f"検索保存要求: {name} - {query}")
            QMessageBox.information(self, "保存完了", f"検索「{name}」を保存しました。")

    def _on_saved_search_selected(self, search_data: Dict[str, Any]) -> None:
        """保存された検索選択時の処理"""
        query = search_data['query']
        search_type = search_data['search_type']
        search_options = search_data.get('search_options', {})

        # 検索テキストを設定
        self.search_input.setText(query)

        # 検索タイプを設定
        self.search_type_selector.set_search_type(search_type)

        # 検索オプションを設定
        if search_options:
            self._apply_search_options(search_options)

        self.logger.info(f"保存された検索選択: {search_data['name']}")

    def _on_saved_search_deleted(self, search_id: int) -> None:
        """保存された検索削除時の処理"""
        self.logger.info(f"保存された検索削除: ID {search_id}")
        # TODO: 実際の削除処理を実装

    def _apply_search_options(self, options: Dict[str, Any]) -> None:
        """検索オプションを適用"""
        try:
            # ファイルタイプフィルター
            if 'file_types' in options:
                file_types = options['file_types']
                for file_type, checkbox in self.advanced_options.file_type_checkboxes.items():
                    checkbox.setChecked(file_type.value in file_types)

            # 日付範囲
            if 'date_from' in options and 'date_to' in options:
                if options['date_from'] and options['date_to']:
                    self.advanced_options.date_filter_enabled.setChecked(True)
                    # TODO: 日付の設定処理を実装

            # 結果数制限
            if 'limit' in options:
                self.advanced_options.result_limit.setValue(options['limit'])

            # 重み設定
            if 'weights' in options:
                weights = options['weights']
                if 'full_text' in weights:
                    self.advanced_options.full_text_weight.setValue(int(weights['full_text'] * 100))
                if 'semantic' in weights:
                    self.advanced_options.semantic_weight.setValue(int(weights['semantic'] * 100))

        except Exception as e:
            self.logger.error(f"検索オプション適用エラー: {e}")

    def _toggle_advanced_options(self) -> None:
        """高度なオプションの表示切り替え"""
        current_state = self.advanced_options.isChecked()
        self.advanced_options.setChecked(not current_state)

    def on_search_completed(self, results: List[Any], execution_time: float) -> None:
        """
        検索完了時の処理

        Args:
            results: 検索結果
            execution_time: 実行時間（秒）
        """
        result_count = len(results)
        message = f"検索完了: {result_count}件の結果 ({execution_time:.1f}秒)"

        self.progress_widget.finish_search(message)
        self._reset_search_state()

        self.logger.info(f"検索完了: {result_count}件, {execution_time:.1f}秒")

    def on_search_error(self, error_message: str) -> None:
        """
        検索エラー時の処理

        Args:
            error_message: エラーメッセージ
        """
        self.progress_widget.finish_search("検索エラーが発生しました")
        self._reset_search_state()

        QMessageBox.critical(self, "検索エラー", f"検索中にエラーが発生しました:\n{error_message}")
        self.logger.error(f"検索エラー: {error_message}")

    def update_search_suggestions(self, suggestions: List[str]) -> None:
        """
        検索提案を更新

        Args:
            suggestions: 提案リスト
        """
        self.search_input.update_suggestions(suggestions)

    def update_search_history(self, recent_searches: List[Dict[str, Any]],
                            popular_searches: List[Dict[str, Any]],
                            saved_searches: List[Dict[str, Any]] = None) -> None:
        """
        検索履歴を更新

        Args:
            recent_searches: 最近の検索リスト
            popular_searches: 人気の検索リスト
            saved_searches: 保存された検索リスト
        """
        self.history_widget.update_recent_searches(recent_searches)
        self.history_widget.update_popular_searches(popular_searches)

        if saved_searches is not None:
            self.history_widget.update_saved_searches(saved_searches)

    def set_search_text(self, text: str) -> None:
        """
        検索テキストを設定

        Args:
            text: 設定するテキスト
        """
        self.search_input.setText(text)
        self.search_input.setFocus()

    def get_search_text(self) -> str:
        """現在の検索テキストを取得"""
        return self.search_input.text().strip()

    def clear_search(self) -> None:
        """検索フィールドをクリア"""
        self.search_input.clear()
        self.search_input.setFocus()

    def set_enabled(self, enabled: bool) -> None:
        """インターフェースの有効/無効を設定"""
        self.search_input.setEnabled(enabled)
        self.search_button.setEnabled(enabled and not self.is_searching)
        self.search_type_selector.setEnabled(enabled)
        self.advanced_options.setEnabled(enabled)

