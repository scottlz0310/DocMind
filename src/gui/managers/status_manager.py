#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind ステータス管理マネージャー

メインウィンドウのステータスバー管理・状態表示・システム情報表示を専門的に担当します。
ステータスメッセージ、システム情報、進捗状況の統合管理を提供します。
"""

from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QLabel, QMainWindow, QProgressBar, QStatusBar

from src.utils.logging_config import LoggerMixin


class StatusManager(QObject, LoggerMixin):
    """
    ステータス管理マネージャー
    
    メインウィンドウのステータスバー作成、メッセージ表示、
    システム情報管理を統合的に処理します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        ステータス管理マネージャーの初期化
        
        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window
        
        # ステータスバーコンポーネント
        self.status_bar: Optional[QStatusBar] = None
        self.status_label: Optional[QLabel] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.system_info_label: Optional[QLabel] = None
        
        self.logger.debug("ステータス管理マネージャーが初期化されました")

    def setup_status_bar(self) -> None:
        """ステータスバーを設定"""
        try:
            self.status_bar = self.main_window.statusBar()

            # メインステータスラベル
            self.status_label = QLabel("準備完了")
            self.status_bar.addWidget(self.status_label)

            # 進捗バー（通常は非表示）
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.progress_bar.setMaximumWidth(200)
            self.status_bar.addPermanentWidget(self.progress_bar)

            # システム情報ラベル
            self.system_info_label = QLabel("インデックス: 未作成")
            self.status_bar.addPermanentWidget(self.system_info_label)

            # アクセシビリティ設定
            self._setup_accessibility()

            # 初期メッセージを表示
            self.show_status_message("DocMindが起動しました", 3000)
            
            self.logger.info("ステータスバーの設定が完了しました")
            
        except Exception as e:
            self.logger.error(f"ステータスバー設定中にエラーが発生: {e}")
            raise

    def _setup_accessibility(self) -> None:
        """アクセシビリティ機能を設定"""
        if self.status_label:
            self.status_label.setAccessibleName("ステータス情報")
        if self.progress_bar:
            self.progress_bar.setAccessibleName("進捗インジケーター")
        if self.system_info_label:
            self.system_info_label.setAccessibleName("システム情報")

    def show_status_message(self, message: str, timeout: int = 0) -> None:
        """
        ステータスバーにメッセージを表示
        
        Args:
            message: 表示するメッセージ
            timeout: 表示時間（ミリ秒、0で永続表示）
        """
        if self.status_bar:
            self.status_bar.showMessage(message, timeout)
            self.logger.debug(f"ステータスメッセージ: {message}")

    def update_system_info(self, info: str) -> None:
        """
        システム情報を更新
        
        Args:
            info: システム情報文字列
        """
        if self.system_info_label:
            self.system_info_label.setText(info)
            self.logger.debug(f"システム情報更新: {info}")

    def set_system_info_tooltip(self, tooltip: str) -> None:
        """
        システム情報ラベルのツールチップを設定
        
        Args:
            tooltip: ツールチップテキスト
        """
        if self.system_info_label:
            self.system_info_label.setToolTip(tooltip)

    def show_progress_bar(self, visible: bool = True) -> None:
        """
        進捗バーの表示/非表示を設定
        
        Args:
            visible: 表示するかどうか
        """
        if self.progress_bar:
            self.progress_bar.setVisible(visible)

    def set_progress_value(self, value: int) -> None:
        """
        進捗バーの値を設定
        
        Args:
            value: 進捗値（0-100）
        """
        if self.progress_bar:
            self.progress_bar.setValue(value)

    def set_progress_range(self, minimum: int, maximum: int) -> None:
        """
        進捗バーの範囲を設定
        
        Args:
            minimum: 最小値
            maximum: 最大値
        """
        if self.progress_bar:
            self.progress_bar.setRange(minimum, maximum)

    def get_progress_value(self) -> int:
        """
        現在の進捗値を取得
        
        Returns:
            int: 現在の進捗値
        """
        if self.progress_bar:
            return self.progress_bar.value()
        return 0

    def is_progress_visible(self) -> bool:
        """
        進捗バーが表示されているか確認
        
        Returns:
            bool: 表示されている場合True
        """
        if self.progress_bar:
            return self.progress_bar.isVisible()
        return False

    def set_progress_style(self, style: str) -> None:
        """
        進捗バーのスタイルを設定
        
        Args:
            style: スタイル名（'info', 'success', 'warning', 'error'）
        """
        if not self.progress_bar:
            return
            
        style_sheets = {
            'info': """
                QProgressBar {
                    border: 1px solid #d0d0d0;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #2196F3;
                    border-radius: 2px;
                }
            """,
            'success': """
                QProgressBar {
                    border: 1px solid #d0d0d0;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 2px;
                }
            """,
            'warning': """
                QProgressBar {
                    border: 1px solid #d0d0d0;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #FF9800;
                    border-radius: 2px;
                }
            """,
            'error': """
                QProgressBar {
                    border: 1px solid #d0d0d0;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #F44336;
                    border-radius: 2px;
                }
            """
        }
        
        stylesheet = style_sheets.get(style, style_sheets['info'])
        self.progress_bar.setStyleSheet(stylesheet)

    def clear_status(self) -> None:
        """ステータス情報をクリア"""
        if self.status_bar:
            self.status_bar.clearMessage()
        if self.system_info_label:
            self.system_info_label.setText("準備完了")
        if self.progress_bar:
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)

    def get_status_components(self) -> dict:
        """
        ステータスバーコンポーネントを取得
        
        Returns:
            dict: ステータスバーコンポーネントの辞書
        """
        return {
            'status_bar': self.status_bar,
            'status_label': self.status_label,
            'progress_bar': self.progress_bar,
            'system_info_label': self.system_info_label
        }

    def cleanup(self) -> None:
        """ステータス管理マネージャーのクリーンアップ"""
        try:
            # コンポーネント参照をクリア
            self.status_bar = None
            self.status_label = None
            self.progress_bar = None
            self.system_info_label = None
            
            self.logger.debug("ステータス管理マネージャーをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"ステータス管理マネージャーのクリーンアップ中にエラー: {e}")