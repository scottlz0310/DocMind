#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind ツールバー管理マネージャー

メインウィンドウのツールバー作成・管理・アクション処理を専門的に担当します。
検索、インデックス、設定などの主要機能への素早いアクセスを提供します。
"""

import logging
from typing import Optional

from PySide6.QtCore import QObject, QSize, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMainWindow, QToolBar

from src.gui.resources import get_app_icon, get_search_icon, get_settings_icon
from src.utils.logging_config import LoggerMixin


class ToolbarManager(QObject, LoggerMixin):
    """
    ツールバー管理マネージャー
    
    メインウィンドウのツールバー作成、アクション設定、
    アイコン管理を統合的に処理します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        ツールバー管理マネージャーの初期化
        
        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window
        self.toolbar: Optional[QToolBar] = None
        
        # ツールバーアクション参照を保持
        self.toolbar_actions = {}
        
        self.logger.debug("ツールバー管理マネージャーが初期化されました")

    def setup_toolbar(self) -> None:
        """ツールバーを設定"""
        try:
            # メインツールバーを作成
            self.toolbar = self.main_window.addToolBar("メインツールバー")
            self.toolbar.setObjectName("MainToolBar")
            self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            self.toolbar.setIconSize(QSize(24, 24))
            
            # ツールバーアクションを追加
            self._add_folder_actions()
            self.toolbar.addSeparator()
            self._add_search_actions()
            self.toolbar.addSeparator()
            self._add_index_actions()
            self.toolbar.addSeparator()
            self._add_settings_actions()
            
            self.logger.info("ツールバーの設定が完了しました")
            
        except Exception as e:
            self.logger.error(f"ツールバー設定中にエラーが発生: {e}")
            raise

    def _add_folder_actions(self) -> None:
        """フォルダ関連のアクションを追加"""
        # フォルダを開くアクション
        self.toolbar_actions['open_folder'] = QAction(
            get_app_icon(), "フォルダを開く", self.main_window
        )
        self.toolbar_actions['open_folder'].setStatusTip("検索対象のフォルダを選択します")
        self.toolbar_actions['open_folder'].triggered.connect(
            self.main_window.dialog_manager.open_folder_dialog
        )
        self.toolbar.addAction(self.toolbar_actions['open_folder'])

    def _add_search_actions(self) -> None:
        """検索関連のアクションを追加"""
        # 検索アクション
        self.toolbar_actions['search'] = QAction(
            get_search_icon(), "検索", self.main_window
        )
        self.toolbar_actions['search'].setStatusTip("ドキュメント検索を実行します")
        self.toolbar_actions['search'].triggered.connect(
            self.main_window.dialog_manager.show_search_dialog
        )
        self.toolbar.addAction(self.toolbar_actions['search'])

    def _add_index_actions(self) -> None:
        """インデックス関連のアクションを追加"""
        # インデックス再構築アクション
        self.toolbar_actions['rebuild_index'] = QAction(
            QIcon(), "インデックス再構築", self.main_window
        )
        self.toolbar_actions['rebuild_index'].setStatusTip("検索インデックスを再構築します")
        self.toolbar_actions['rebuild_index'].triggered.connect(
            self.main_window.index_controller.rebuild_index
        )
        self.toolbar.addAction(self.toolbar_actions['rebuild_index'])

        # インデックスクリアアクション
        self.toolbar_actions['clear_index'] = QAction(
            QIcon(), "インデックスクリア", self.main_window
        )
        self.toolbar_actions['clear_index'].setStatusTip("検索インデックスをクリアします")
        self.toolbar_actions['clear_index'].triggered.connect(
            self.main_window.index_controller.clear_index
        )
        self.toolbar.addAction(self.toolbar_actions['clear_index'])

    def _add_settings_actions(self) -> None:
        """設定関連のアクションを追加"""
        # 設定アクション
        self.toolbar_actions['settings'] = QAction(
            get_settings_icon(), "設定", self.main_window
        )
        self.toolbar_actions['settings'].setStatusTip("アプリケーション設定を開きます")
        self.toolbar_actions['settings'].triggered.connect(self._show_settings_dialog)
        self.toolbar.addAction(self.toolbar_actions['settings'])

    def _show_settings_dialog(self) -> None:
        """設定ダイアログを表示"""
        if self.main_window.dialog_manager.show_settings_dialog():
            self.main_window.show_status_message("設定が保存されました", 3000)

    def get_toolbar_action(self, action_name: str) -> Optional[QAction]:
        """
        指定されたツールバーアクションを取得
        
        Args:
            action_name: アクション名
            
        Returns:
            QAction: 対応するアクション、存在しない場合はNone
        """
        return self.toolbar_actions.get(action_name)

    def enable_toolbar_action(self, action_name: str, enabled: bool = True) -> None:
        """
        指定されたツールバーアクションの有効/無効を設定
        
        Args:
            action_name: アクション名
            enabled: 有効にするかどうか
        """
        action = self.get_toolbar_action(action_name)
        if action:
            action.setEnabled(enabled)
            self.logger.debug(f"ツールバーアクション '{action_name}' を{'有効' if enabled else '無効'}にしました")

    def set_toolbar_visible(self, visible: bool = True) -> None:
        """
        ツールバーの表示/非表示を設定
        
        Args:
            visible: 表示するかどうか
        """
        if self.toolbar:
            self.toolbar.setVisible(visible)
            self.logger.debug(f"ツールバーを{'表示' if visible else '非表示'}にしました")

    def cleanup(self) -> None:
        """ツールバー管理マネージャーのクリーンアップ"""
        try:
            # ツールバーアクション参照をクリア
            self.toolbar_actions.clear()
            
            # ツールバーを削除
            if self.toolbar:
                self.main_window.removeToolBar(self.toolbar)
                self.toolbar = None
            
            self.logger.debug("ツールバー管理マネージャーをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"ツールバー管理マネージャーのクリーンアップ中にエラー: {e}")