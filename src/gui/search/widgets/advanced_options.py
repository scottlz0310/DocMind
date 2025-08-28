#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高度な検索オプションウィジェット

ファイルタイプフィルター、日付範囲、フォルダ指定などの
詳細な検索条件設定機能を提供します。
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QDateEdit, QGroupBox, QHBoxLayout, 
                               QLabel, QSlider, QSpinBox, QVBoxLayout, QWidget)

from ....data.models import FileType


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

    def reset_to_defaults(self) -> None:
        """デフォルト設定にリセット"""
        # ファイルタイプを全て選択
        for checkbox in self.file_type_checkboxes.values():
            checkbox.setChecked(True)
        
        # 日付フィルターを無効化
        self.date_filter_enabled.setChecked(False)
        
        # 結果数制限をデフォルトに
        self.result_limit.setValue(100)
        
        # 重みをデフォルトに
        self.full_text_weight.setValue(60)
        self.semantic_weight.setValue(40)