#!/usr/bin/env python3
"""
検索進捗表示ウィジェット

検索の進捗状況、キャンセル機能、実行時間表示を提供します。
"""

import logging
from datetime import datetime

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QWidget


class SearchProgressWidget(QWidget):
    """
    検索進捗表示ウィジェット

    検索の進捗状況、キャンセル機能、実行時間表示を提供します。
    """

    # シグナル定義
    cancel_requested = Signal()  # キャンセルが要求された時

    def __init__(self, parent: QWidget | None = None):
        """
        検索進捗ウィジェットを初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.start_time: datetime | None = None
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

    def update_progress(self, message: str, progress: int | None = None) -> None:
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
