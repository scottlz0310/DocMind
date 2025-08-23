#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索インターフェースウィジェット

オートコンプリート付きの検索入力、検索タイプ選択、高度な検索オプション、
検索履歴管理、進捗インジケーター機能を提供する統合検索インターフェースです。
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton,
    QLabel, QFrame, QGroupBox, QCheckBox, QDateEdit, QSpinBox, QSlider,
    QProgressBar, QListWidget, QListWidgetItem, QCompleter, QMenu,
    QSplitter, QTabWidget, QTextEdit, QScrollArea, QButtonGroup, QRadioButton,
    QToolButton, QSizePolicy, QMessageBox
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QThread, QStringListModel, QDate, QSize,
    QPropertyAnimation, QEasingCurve, QRect, QPoint
)
from PySide6.QtGui import (
    QIcon, QPixmap, QFont, QFontMetrics, QPalette, QColor, QKeySequence,
    QShortcut, QValidator, QRegularExpressionValidator, QAction
)

from ..data.models import SearchType, FileType, SearchQuery
from ..utils.exceptions import SearchError


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


class SearchTypeSelector(QWidget):
    """
    検索タイプ選択ウィジェット
    
    全文検索、セマンティック検索、ハイブリッド検索の選択機能を提供します。
    """
    
    # シグナル定義
    search_type_changed = Signal(SearchType)  # 検索タイプが変更された時
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        検索タイプ選択ウィジェットを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.current_search_type = SearchType.HYBRID
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self) -> None:
        """UIの設定"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ラベル
        label = QLabel("検索タイプ:")
        label.setFont(QFont("", 9))
        layout.addWidget(label)
        
        # ラジオボタングループ
        self.button_group = QButtonGroup(self)
        
        # 全文検索ラジオボタン
        self.full_text_radio = QRadioButton("全文検索")
        self.full_text_radio.setToolTip("キーワードの完全一致による検索")
        self.button_group.addButton(self.full_text_radio, 0)  # 単純な整数IDを使用
        layout.addWidget(self.full_text_radio)
        
        # セマンティック検索ラジオボタン
        self.semantic_radio = QRadioButton("セマンティック検索")
        self.semantic_radio.setToolTip("意味的類似性による検索")
        self.button_group.addButton(self.semantic_radio, 1)  # 単純な整数IDを使用
        layout.addWidget(self.semantic_radio)
        
        # ハイブリッド検索ラジオボタン（デフォルト選択）
        self.hybrid_radio = QRadioButton("ハイブリッド検索")
        self.hybrid_radio.setToolTip("全文検索とセマンティック検索の組み合わせ")
        self.hybrid_radio.setChecked(True)
        self.button_group.addButton(self.hybrid_radio, 2)  # 単純な整数IDを使用
        layout.addWidget(self.hybrid_radio)
        
        # スペーサー
        layout.addStretch()
        
        # スタイル設定
        self.setStyleSheet("""
            QRadioButton {
                font-size: 12px;
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #4CAF50;
                border-radius: 8px;
                background-color: #4CAF50;
            }
            QRadioButton::indicator:checked::after {
                content: '';
                width: 6px;
                height: 6px;
                border-radius: 3px;
                background-color: white;
                margin: 3px;
            }
        """)
    
    def _setup_connections(self) -> None:
        """シグナル接続の設定"""
        self.button_group.buttonClicked.connect(self._on_search_type_changed)
    
    def _on_search_type_changed(self, button) -> None:
        """検索タイプ変更時の処理"""
        if button == self.full_text_radio:
            self.current_search_type = SearchType.FULL_TEXT
        elif button == self.semantic_radio:
            self.current_search_type = SearchType.SEMANTIC
        elif button == self.hybrid_radio:
            self.current_search_type = SearchType.HYBRID
        
        self.search_type_changed.emit(self.current_search_type)
        self.logger.debug(f"検索タイプ変更: {self.current_search_type.value}")
    
    def get_search_type(self) -> SearchType:
        """現在の検索タイプを取得"""
        return self.current_search_type
    
    def set_search_type(self, search_type: SearchType) -> None:
        """検索タイプを設定"""
        self.current_search_type = search_type
        
        if search_type == SearchType.FULL_TEXT:
            self.full_text_radio.setChecked(True)
        elif search_type == SearchType.SEMANTIC:
            self.semantic_radio.setChecked(True)
        elif search_type == SearchType.HYBRID:
            self.hybrid_radio.setChecked(True)


class AdvancedSearchOptions(QGroupBox):
    """
    高度な検索オプションウィジェット
    
    ファイルタイプフィルター、日付範囲、フォルダ指定などの
    詳細な検索条件設定機能を提供します。
    """
    
    # シグナル定義
    options_changed = Signal(dict)  # オプションが変更された時
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        高度な検索オプションウィジェットを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__("高度な検索オプション", parent)
        
        self.logger = logging.getLogger(__name__)
        self.is_expanded = False
        
        self._setup_ui()
        self._setup_connections()
        self._setup_initial_state()
    
    def _setup_ui(self) -> None:
        """UIの設定"""
        self.setCheckable(True)
        self.setChecked(False)
        
        layout = QVBoxLayout(self)
        
        # ファイルタイプフィルター
        file_type_group = QGroupBox("ファイルタイプ")
        file_type_layout = QHBoxLayout(file_type_group)
        
        self.file_type_checkboxes = {}
        for file_type in FileType:
            if file_type != FileType.UNKNOWN:
                checkbox = QCheckBox(file_type.value.upper())
                checkbox.setChecked(True)  # デフォルトで全て選択
                checkbox.setToolTip(f"{file_type.value}ファイルを検索対象に含める")
                self.file_type_checkboxes[file_type] = checkbox
                file_type_layout.addWidget(checkbox)
        
        layout.addWidget(file_type_group)
        
        # 日付範囲フィルター
        date_group = QGroupBox("日付範囲")
        date_layout = QVBoxLayout(date_group)
        
        # 日付範囲有効化チェックボックス
        self.date_filter_enabled = QCheckBox("日付範囲でフィルタリング")
        date_layout.addWidget(self.date_filter_enabled)
        
        # 日付選択
        date_range_layout = QHBoxLayout()
        
        date_range_layout.addWidget(QLabel("開始日:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.setEnabled(False)
        date_range_layout.addWidget(self.date_from)
        
        date_range_layout.addWidget(QLabel("終了日:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setEnabled(False)
        date_range_layout.addWidget(self.date_to)
        
        date_layout.addLayout(date_range_layout)
        layout.addWidget(date_group)
        
        # 結果数制限
        limit_group = QGroupBox("結果数制限")
        limit_layout = QHBoxLayout(limit_group)
        
        limit_layout.addWidget(QLabel("最大結果数:"))
        self.result_limit = QSpinBox()
        self.result_limit.setRange(10, 1000)
        self.result_limit.setValue(100)
        self.result_limit.setSuffix(" 件")
        limit_layout.addWidget(self.result_limit)
        
        limit_layout.addStretch()
        layout.addWidget(limit_group)
        
        # ハイブリッド検索の重み設定
        weights_group = QGroupBox("ハイブリッド検索の重み設定")
        weights_layout = QVBoxLayout(weights_group)
        
        # 全文検索の重み
        full_text_layout = QHBoxLayout()
        full_text_layout.addWidget(QLabel("全文検索:"))
        self.full_text_weight = QSlider(Qt.Horizontal)
        self.full_text_weight.setRange(0, 100)
        self.full_text_weight.setValue(60)
        self.full_text_weight_label = QLabel("60%")
        full_text_layout.addWidget(self.full_text_weight)
        full_text_layout.addWidget(self.full_text_weight_label)
        weights_layout.addLayout(full_text_layout)
        
        # セマンティック検索の重み
        semantic_layout = QHBoxLayout()
        semantic_layout.addWidget(QLabel("セマンティック検索:"))
        self.semantic_weight = QSlider(Qt.Horizontal)
        self.semantic_weight.setRange(0, 100)
        self.semantic_weight.setValue(40)
        self.semantic_weight_label = QLabel("40%")
        semantic_layout.addWidget(self.semantic_weight)
        semantic_layout.addWidget(self.semantic_weight_label)
        weights_layout.addLayout(semantic_layout)
        
        layout.addWidget(weights_group)
        
        # スタイル設定
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QCheckBox, QRadioButton {
                font-weight: normal;
            }
        """)
    
    def _setup_connections(self) -> None:
        """シグナル接続の設定"""
        # グループボックスの展開/折りたたみ
        self.toggled.connect(self._on_toggled)
        
        # 日付フィルター有効化
        self.date_filter_enabled.toggled.connect(self._on_date_filter_toggled)
        
        # 重みスライダーの連動
        self.full_text_weight.valueChanged.connect(self._on_full_text_weight_changed)
        self.semantic_weight.valueChanged.connect(self._on_semantic_weight_changed)
        
        # オプション変更の通知
        for checkbox in self.file_type_checkboxes.values():
            checkbox.toggled.connect(self._emit_options_changed)
        
        self.date_filter_enabled.toggled.connect(self._emit_options_changed)
        self.date_from.dateChanged.connect(self._emit_options_changed)
        self.date_to.dateChanged.connect(self._emit_options_changed)
        self.result_limit.valueChanged.connect(self._emit_options_changed)
        self.full_text_weight.valueChanged.connect(self._emit_options_changed)
        self.semantic_weight.valueChanged.connect(self._emit_options_changed)
    
    def _setup_initial_state(self) -> None:
        """初期状態の設定"""
        # 初期状態では折りたたまれている
        self.setMaximumHeight(30)
    
    def _on_toggled(self, checked: bool) -> None:
        """展開/折りたたみ時の処理"""
        self.is_expanded = checked
        
        if checked:
            self.setMaximumHeight(16777215)  # 制限なし
            self.logger.debug("高度な検索オプションを展開")
        else:
            self.setMaximumHeight(30)
            self.logger.debug("高度な検索オプションを折りたたみ")
    
    def _on_date_filter_toggled(self, enabled: bool) -> None:
        """日付フィルター有効化時の処理"""
        self.date_from.setEnabled(enabled)
        self.date_to.setEnabled(enabled)
    
    def _on_full_text_weight_changed(self, value: int) -> None:
        """全文検索重み変更時の処理"""
        self.full_text_weight_label.setText(f"{value}%")
        # セマンティック検索の重みを自動調整
        semantic_value = 100 - value
        self.semantic_weight.setValue(semantic_value)
        self.semantic_weight_label.setText(f"{semantic_value}%")
    
    def _on_semantic_weight_changed(self, value: int) -> None:
        """セマンティック検索重み変更時の処理"""
        self.semantic_weight_label.setText(f"{value}%")
        # 全文検索の重みを自動調整
        full_text_value = 100 - value
        self.full_text_weight.setValue(full_text_value)
        self.full_text_weight_label.setText(f"{full_text_value}%")
    
    def _emit_options_changed(self) -> None:
        """オプション変更シグナルを発行"""
        options = self.get_search_options()
        self.options_changed.emit(options)
    
    def get_search_options(self) -> Dict[str, Any]:
        """現在の検索オプションを取得"""
        # 選択されたファイルタイプ
        selected_file_types = [
            file_type for file_type, checkbox in self.file_type_checkboxes.items()
            if checkbox.isChecked()
        ]
        
        # 日付範囲
        date_from = None
        date_to = None
        if self.date_filter_enabled.isChecked():
            date_from = self.date_from.date().toPython()
            date_to = self.date_to.date().toPython()
            # 時刻を設定（開始日は00:00:00、終了日は23:59:59）
            date_from = datetime.combine(date_from, datetime.min.time())
            date_to = datetime.combine(date_to, datetime.max.time())
        
        return {
            'file_types': selected_file_types,
            'date_from': date_from,
            'date_to': date_to,
            'limit': self.result_limit.value(),
            'weights': {
                'full_text': self.full_text_weight.value() / 100.0,
                'semantic': self.semantic_weight.value() / 100.0
            }
        }


class SearchProgressWidget(QWidget):
    """
    検索進捗表示ウィジェット
    
    検索の進捗状況、キャンセル機能、実行時間表示を提供します。
    """
    
    # シグナル定義
    cancel_requested = Signal()  # キャンセルが要求された時
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        検索進捗ウィジェットを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.start_time: Optional[datetime] = None
        self.timer = QTimer()
        
        self._setup_ui()
        self._setup_connections()
        self.hide()  # 初期状態では非表示
    
    def _setup_ui(self) -> None:
        """UIの設定"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 進捗バー
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不定進捗
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(20)
        layout.addWidget(self.progress_bar)
        
        # ステータスラベル
        self.status_label = QLabel("検索中...")
        self.status_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(self.status_label)
        
        # 経過時間ラベル
        self.time_label = QLabel("0.0秒")
        self.time_label.setStyleSheet("font-size: 12px; color: #666;")
        self.time_label.setMinimumWidth(50)
        layout.addWidget(self.time_label)
        
        # キャンセルボタン
        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.setMaximumWidth(80)
        self.cancel_button.setMaximumHeight(25)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        layout.addWidget(self.cancel_button)
        
        # 全体のスタイル
        self.setStyleSheet("""
            QWidget {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 4px;
            }
        """)
    
    def _setup_connections(self) -> None:
        """シグナル接続の設定"""
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.timer.timeout.connect(self._update_elapsed_time)
    
    def start_search(self, status_message: str = "検索中...") -> None:
        """検索開始"""
        self.start_time = datetime.now()
        self.status_label.setText(status_message)
        self.time_label.setText("0.0秒")
        self.progress_bar.setRange(0, 0)  # 不定進捗
        
        self.timer.start(100)  # 100ms間隔で更新
        self.show()
        
        self.logger.debug(f"検索進捗表示開始: {status_message}")
    
    def update_progress(self, message: str, progress: Optional[int] = None) -> None:
        """進捗更新"""
        self.status_label.setText(message)
        
        if progress is not None:
            if self.progress_bar.maximum() == 0:
                self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(progress)
        
        self.logger.debug(f"検索進捗更新: {message} ({progress}%)")
    
    def finish_search(self, result_message: str = "") -> None:
        """検索完了"""
        self.timer.stop()
        
        if result_message:
            self.status_label.setText(result_message)
        
        # 2秒後に非表示
        QTimer.singleShot(2000, self.hide)
        
        elapsed_time = self._get_elapsed_time()
        self.logger.info(f"検索完了: {elapsed_time:.1f}秒")
    
    def _update_elapsed_time(self) -> None:
        """経過時間の更新"""
        if self.start_time:
            elapsed = self._get_elapsed_time()
            self.time_label.setText(f"{elapsed:.1f}秒")
    
    def _get_elapsed_time(self) -> float:
        """経過時間を取得"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0
    
    def _on_cancel_clicked(self) -> None:
        """キャンセルボタンクリック時の処理"""
        self.cancel_requested.emit()
        self.status_label.setText("キャンセル中...")
        self.cancel_button.setEnabled(False)
        self.logger.info("検索キャンセルが要求されました")


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
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        検索履歴ウィジェットを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.recent_searches: List[Dict[str, Any]] = []
        self.popular_searches: List[Dict[str, Any]] = []
        self.saved_searches: List[Dict[str, Any]] = []
        
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
    
    def update_recent_searches(self, searches: List[Dict[str, Any]]) -> None:
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
    
    def update_popular_searches(self, searches: List[Dict[str, Any]]) -> None:
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
    
    def update_saved_searches(self, searches: List[Dict[str, Any]]) -> None:
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
    
    def _rename_saved_search(self, search_data: Dict[str, Any]) -> None:
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
    
    def _delete_saved_search(self, search_data: Dict[str, Any]) -> None:
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


class SearchInterface(QWidget):
    """
    統合検索インターフェースウィジェット
    
    検索入力、検索タイプ選択、高度なオプション、進捗表示、履歴管理を
    統合した完全な検索インターフェースを提供します。
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


class SearchWorkerThread(QThread):
    """
    検索処理を別スレッドで実行するワーカークラス
    
    UIをブロックすることなく検索処理を実行し、
    進捗更新とキャンセル機能を提供します。
    """
    
    # シグナル定義
    progress_updated = Signal(str, int)      # 進捗更新 (メッセージ, 進捗%)
    search_completed = Signal(list, float)   # 検索完了 (結果, 実行時間)
    search_error = Signal(str)               # 検索エラー (エラーメッセージ)
    
    def __init__(self, search_manager, query: SearchQuery, parent: Optional[QWidget] = None):
        """
        検索ワーカーを初期化
        
        Args:
            search_manager: 検索マネージャー
            query: 検索クエリ
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.search_manager = search_manager
        self.query = query
        self.is_cancelled = False
        self.logger = logging.getLogger(__name__)
    
    def run(self) -> None:
        """検索処理を実行"""
        try:
            start_time = datetime.now()
            
            # 検索実行
            self.progress_updated.emit("検索を実行中...", 10)
            
            if self.is_cancelled:
                return
            
            results = self.search_manager.search(self.query)
            
            if self.is_cancelled:
                return
            
            self.progress_updated.emit("結果を処理中...", 90)
            
            # 実行時間を計算
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.progress_updated.emit("完了", 100)
            self.search_completed.emit(results, execution_time)
            
        except Exception as e:
            if not self.is_cancelled:
                self.logger.error(f"検索スレッドエラー: {e}")
                self.search_error.emit(str(e))
    
    def cancel(self) -> None:
        """検索をキャンセル"""
        self.is_cancelled = True
        self.logger.debug("検索スレッドのキャンセルが要求されました")