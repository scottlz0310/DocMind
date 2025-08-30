#!/usr/bin/env python3
"""
検索履歴表示ウィジェット

最近の検索履歴、人気の検索、保存された検索の管理機能を提供します。
"""

import logging
from typing import Any

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SearchHistoryWidget(QWidget):
    """
    検索履歴表示ウィジェット

    最近の検索履歴、人気の検索、保存された検索の管理機能を提供します。
    """

    # シグナル定義
    history_selected = Signal(str)  # 履歴が選択された時
    history_deleted = Signal(str)   # 履歴が削除された時
    search_save_requested = Signal(str)  # 検索保存が要求された時
    saved_search_selected = Signal(dict)  # 保存された検索が選択された時
    saved_search_deleted = Signal(int)    # 保存された検索が削除された時

    def __init__(self, parent: QWidget | None = None):
        """
        検索履歴ウィジェットを初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.recent_searches: list[dict[str, Any]] = []
        self.popular_searches: list[dict[str, Any]] = []
        self.saved_searches: list[dict[str, Any]] = []

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """UIの設定"""
        layout = QVBoxLayout(self)

        # タブウィジェット
        self.tab_widget = QTabWidget()

        # 最近の検索タブ
        self.recent_tab = QWidget()
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(200)
        recent_layout = QVBoxLayout(self.recent_tab)
        recent_layout.addWidget(self.recent_list)
        self.tab_widget.addTab(self.recent_tab, "最近の検索")

        # 人気の検索タブ
        self.popular_tab = QWidget()
        self.popular_list = QListWidget()
        self.popular_list.setMaximumHeight(200)
        popular_layout = QVBoxLayout(self.popular_tab)
        popular_layout.addWidget(self.popular_list)
        self.tab_widget.addTab(self.popular_tab, "人気の検索")

        # 保存された検索タブ
        self.saved_tab = QWidget()
        saved_layout = QVBoxLayout(self.saved_tab)

        # 保存された検索リスト
        self.saved_list = QListWidget()
        self.saved_list.setMaximumHeight(180)
        saved_layout.addWidget(self.saved_list)

        # 保存ボタン
        save_button_layout = QHBoxLayout()
        self.save_search_button = QPushButton("現在の検索を保存")
        self.save_search_button.setMaximumHeight(30)
        self.save_search_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        save_button_layout.addWidget(self.save_search_button)
        save_button_layout.addStretch()
        saved_layout.addLayout(save_button_layout)

        self.tab_widget.addTab(self.saved_tab, "保存された検索")

        layout.addWidget(self.tab_widget)

        # スタイル設定
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QListWidget {
                border: none;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)

    def _setup_connections(self) -> None:
        """シグナル接続の設定"""
        self.recent_list.itemDoubleClicked.connect(self._on_recent_item_selected)
        self.popular_list.itemDoubleClicked.connect(self._on_popular_item_selected)
        self.saved_list.itemDoubleClicked.connect(self._on_saved_item_selected)

        # 保存ボタン
        self.save_search_button.clicked.connect(self._on_save_search_clicked)

        # コンテキストメニュー
        self.recent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent_list.customContextMenuRequested.connect(self._show_recent_context_menu)

        self.saved_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.saved_list.customContextMenuRequested.connect(self._show_saved_context_menu)

    def update_recent_searches(self, searches: list[dict[str, Any]]) -> None:
        """最近の検索を更新"""
        self.recent_searches = searches
        self.recent_list.clear()

        for search in searches[:20]:  # 最大20件
            query = search['query']
            timestamp = search['timestamp']
            result_count = search['result_count']

            item_text = f"{query} ({result_count}件) - {timestamp.strftime('%m/%d %H:%M')}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, query)
            item.setToolTip(f"検索: {query}\n結果: {result_count}件\n日時: {timestamp}")

            self.recent_list.addItem(item)

        self.logger.debug(f"最近の検索を更新: {len(searches)}件")

    def update_popular_searches(self, searches: list[dict[str, Any]]) -> None:
        """人気の検索を更新"""
        self.popular_searches = searches
        self.popular_list.clear()

        for search in searches[:15]:  # 最大15件
            query = search['query']
            search_count = search['search_count']
            avg_results = search['avg_results']

            item_text = f"{query} ({search_count}回, 平均{avg_results:.0f}件)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, query)
            item.setToolTip(f"検索: {query}\n検索回数: {search_count}回\n平均結果数: {avg_results:.1f}件")

            self.popular_list.addItem(item)

        self.logger.debug(f"人気の検索を更新: {len(searches)}件")

    def update_saved_searches(self, searches: list[dict[str, Any]]) -> None:
        """保存された検索を更新"""
        self.saved_searches = searches
        self.saved_list.clear()

        for search in searches:
            name = search['name']
            query = search['query']
            use_count = search['use_count']
            search_type = search['search_type']

            item_text = f"{name} - {query} ({use_count}回使用)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, search)
            item.setToolTip(f"名前: {name}\n検索: {query}\n種類: {search_type.value}\n使用回数: {use_count}回")

            self.saved_list.addItem(item)

        self.logger.debug(f"保存された検索を更新: {len(searches)}件")

    def _on_recent_item_selected(self, item: QListWidgetItem) -> None:
        """最近の検索項目選択時の処理"""
        query = item.data(Qt.UserRole)
        if query:
            self.history_selected.emit(query)
            self.logger.debug(f"最近の検索選択: {query}")

    def _on_popular_item_selected(self, item: QListWidgetItem) -> None:
        """人気の検索項目選択時の処理"""
        query = item.data(Qt.UserRole)
        if query:
            self.history_selected.emit(query)
            self.logger.debug(f"人気の検索選択: {query}")

    def _on_saved_item_selected(self, item: QListWidgetItem) -> None:
        """保存された検索項目選択時の処理"""
        search_data = item.data(Qt.UserRole)
        if search_data:
            self.saved_search_selected.emit(search_data)
            self.logger.debug(f"保存された検索選択: {search_data['name']}")

    def _on_save_search_clicked(self) -> None:
        """検索保存ボタンクリック時の処理"""
        # 現在の検索テキストを取得（親ウィジェットから）
        parent_interface = self.parent()
        while parent_interface and not hasattr(parent_interface, 'get_search_text'):
            parent_interface = parent_interface.parent()

        if parent_interface:
            current_query = parent_interface.get_search_text()
            if current_query.strip():
                self.search_save_requested.emit(current_query)
            else:
                QMessageBox.warning(self, "保存エラー", "保存する検索キーワードを入力してください。")
        else:
            QMessageBox.warning(self, "保存エラー", "現在の検索を取得できませんでした。")

    def _show_recent_context_menu(self, position: QPoint) -> None:
        """最近の検索のコンテキストメニュー表示"""
        item = self.recent_list.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        # 検索実行アクション
        search_action = QAction("この検索を実行", self)
        search_action.triggered.connect(lambda: self._on_recent_item_selected(item))
        menu.addAction(search_action)

        menu.addSeparator()

        # 履歴削除アクション
        delete_action = QAction("履歴から削除", self)
        delete_action.triggered.connect(lambda: self._delete_history_item(item))
        menu.addAction(delete_action)

        menu.exec(self.recent_list.mapToGlobal(position))

    def _show_saved_context_menu(self, position: QPoint) -> None:
        """保存された検索のコンテキストメニュー表示"""
        item = self.saved_list.itemAt(position)
        if not item:
            return

        search_data = item.data(Qt.UserRole)
        if not search_data:
            return

        menu = QMenu(self)

        # 検索実行アクション
        execute_action = QAction("この検索を実行", self)
        execute_action.triggered.connect(lambda: self._on_saved_item_selected(item))
        menu.addAction(execute_action)

        menu.addSeparator()

        # 名前変更アクション
        rename_action = QAction("名前を変更", self)
        rename_action.triggered.connect(lambda: self._rename_saved_search(search_data))
        menu.addAction(rename_action)

        # 削除アクション
        delete_action = QAction("削除", self)
        delete_action.triggered.connect(lambda: self._delete_saved_search(search_data))
        menu.addAction(delete_action)

        menu.exec(self.saved_list.mapToGlobal(position))

    def _delete_history_item(self, item: QListWidgetItem) -> None:
        """履歴項目を削除"""
        query = item.data(Qt.UserRole)
        if query:
            reply = QMessageBox.question(
                self,
                "履歴削除",
                f"検索履歴「{query}」を削除しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.history_deleted.emit(query)
                self.recent_list.takeItem(self.recent_list.row(item))
                self.logger.info(f"検索履歴を削除: {query}")

    def _rename_saved_search(self, search_data: dict[str, Any]) -> None:
        """保存された検索の名前変更"""
        from PySide6.QtWidgets import QInputDialog

        current_name = search_data['name']
        new_name, ok = QInputDialog.getText(
            self,
            "名前変更",
            "新しい名前を入力してください:",
            text=current_name
        )

        if ok and new_name.strip() and new_name != current_name:
            # TODO: 実際の名前変更処理を実装
            self.logger.info(f"保存された検索の名前変更: {current_name} -> {new_name}")

    def _delete_saved_search(self, search_data: dict[str, Any]) -> None:
        """保存された検索を削除"""
        reply = QMessageBox.question(
            self,
            "検索削除",
            f"保存された検索「{search_data['name']}」を削除しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.saved_search_deleted.emit(search_data['id'])
            self.logger.info(f"保存された検索を削除: {search_data['name']}")
