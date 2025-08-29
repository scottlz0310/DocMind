#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索入力ウィジェット

オートコンプリート機能付きの検索入力ウィジェットを提供します。
"""

import logging
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QCompleter, QLineEdit, QWidget
from PySide6.QtCore import QStringListModel


class SearchInputWidget(QLineEdit):
    """
    オートコンプリート機能付きの検索入力ウィジェット

    検索履歴に基づく自動補完、検索提案、入力検証機能を提供します。
    """

    # シグナル定義
    search_requested = Signal(str)  # 検索が要求された時
    suggestion_selected = Signal(str)  # 提案が選択された時

    def __init__(self, parent: Optional[QWidget] = None):
        """
        検索入力ウィジェットを初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.suggestions: List[str] = []
        self.completer: Optional[QCompleter] = None

        self._setup_ui()
        self._setup_completer()
        self._setup_shortcuts()
        self._setup_validation()

    def _setup_ui(self) -> None:
        """UIの基本設定"""
        self.setPlaceholderText("検索キーワードを入力してください...")
        self.setMinimumHeight(35)
        self.setMaximumHeight(35)

        # スタイルシートを適用
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #d0d0d0;
                border-radius: 18px;
                padding: 8px 15px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
                background-color: #fafafa;
            }
            QLineEdit:hover {
                border-color: #a0a0a0;
            }
        """)

        # アクセシビリティ設定
        self.setAccessibleName("検索入力フィールド")
        self.setAccessibleDescription("検索したいキーワードを入力してください")

    def _setup_completer(self) -> None:
        """オートコンプリート機能の設定"""
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setMaxVisibleItems(10)

        # コンプリーターのスタイル設定
        popup = self.completer.popup()
        popup.setStyleSheet("""
            QListView {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #e3f2fd;
                font-size: 13px;
            }
            QListView::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListView::item:hover {
                background-color: #f5f5f5;
            }
        """)

        self.setCompleter(self.completer)

        # コンプリーター選択時のシグナル接続
        self.completer.activated.connect(self._on_suggestion_selected)

    def _setup_shortcuts(self) -> None:
        """キーボードショートカットの設定"""
        # Enterキーで検索実行
        self.returnPressed.connect(self._on_search_requested)

        # Ctrl+Kで検索フィールドにフォーカス
        focus_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        focus_shortcut.activated.connect(self.setFocus)

        # Escキーで入力をクリア
        clear_shortcut = QShortcut(QKeySequence("Escape"), self)
        clear_shortcut.activated.connect(self.clear)

    def _setup_validation(self) -> None:
        """入力検証の設定"""
        # 最大文字数制限
        self.setMaxLength(500)

        # 入力変更時の処理
        self.textChanged.connect(self._on_text_changed)

    def update_suggestions(self, suggestions: List[str]) -> None:
        """
        検索提案を更新

        Args:
            suggestions: 提案リスト
        """
        self.suggestions = suggestions

        if self.completer:
            model = QStringListModel(suggestions)
            self.completer.setModel(model)

        self.logger.debug(f"検索提案を更新: {len(suggestions)}件")

    def _on_text_changed(self, text: str) -> None:
        """テキスト変更時の処理"""
        # 空白のみの入力を防ぐ
        if text.strip() != text:
            cursor_pos = self.cursorPosition()
            self.setText(text.strip())
            self.setCursorPosition(min(cursor_pos, len(text.strip())))

    def _on_search_requested(self) -> None:
        """検索要求時の処理"""
        query_text = self.text().strip()
        if query_text:
            self.search_requested.emit(query_text)
            self.logger.info(f"検索要求: '{query_text}'")

    def _on_suggestion_selected(self, suggestion: str) -> None:
        """提案選択時の処理"""
        self.suggestion_selected.emit(suggestion)
        self.logger.debug(f"提案選択: '{suggestion}'")