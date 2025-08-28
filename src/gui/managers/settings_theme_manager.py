#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind 設定・テーマ管理マネージャー

アプリケーションの設定変更、テーマ適用、フォント設定を管理します。
main_window.pyから分離された設定関連の処理を統合管理します。
"""

import logging
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QFont

from src.utils.logging_config import LoggerMixin


class SettingsThemeManager(QObject, LoggerMixin):
    """
    設定・テーマ管理マネージャー
    
    アプリケーションの設定変更、UIテーマ適用、フォント設定を管理します。
    メインウィンドウから設定関連の責務を分離し、独立した管理を提供します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        設定・テーマ管理マネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(parent=main_window)
        self.main_window = main_window
        self.logger.info("設定・テーマ管理マネージャーが初期化されました")

    def handle_settings_changed(self, settings: Dict[str, Any]) -> None:
        """
        設定変更時の処理
        
        Args:
            settings: 変更された設定の辞書
        """
        try:
            # ログ設定の更新
            self._update_logging_settings(settings)

            # ウィンドウサイズの更新
            self._update_window_size(settings)

            # UIテーマの更新
            self._update_ui_theme(settings)

            # フォント設定の更新
            self._update_font_settings(settings)

            self.logger.info("設定変更が適用されました")

        except Exception as e:
            self.logger.error(f"設定変更の適用に失敗しました: {e}")
            if hasattr(self.main_window, 'dialog_manager'):
                self.main_window.dialog_manager.show_partial_failure_dialog(
                    "設定変更",
                    f"一部の設定変更の適用に失敗しました:\\n{e}",
                    "アプリケーションを再起動すると設定が正しく適用される可能性があります。"
                )

    def _update_logging_settings(self, settings: Dict[str, Any]) -> None:
        """
        ログ設定の更新
        
        Args:
            settings: 設定辞書
        """
        try:
            log_level = settings.get("log_level")
            console_logging = settings.get("console_logging")
            file_logging = settings.get("file_logging")
            
            if any([log_level, console_logging is not None, file_logging is not None]):
                from src.utils.logging_config import reconfigure_logging
                reconfigure_logging(
                    level=log_level,
                    enable_console=console_logging,
                    enable_file=file_logging
                )
                self.logger.debug("ログ設定を更新しました")
                
        except Exception as e:
            self.logger.warning(f"ログ設定の更新に失敗: {e}")

    def _update_window_size(self, settings: Dict[str, Any]) -> None:
        """
        ウィンドウサイズの更新
        
        Args:
            settings: 設定辞書
        """
        try:
            window_width = settings.get("window_width")
            window_height = settings.get("window_height")
            
            if window_width and window_height:
                self.main_window.resize(window_width, window_height)
                self.logger.debug(f"ウィンドウサイズを更新: {window_width}x{window_height}")
                
        except Exception as e:
            self.logger.warning(f"ウィンドウサイズの更新に失敗: {e}")

    def _update_ui_theme(self, settings: Dict[str, Any]) -> None:
        """
        UIテーマの更新
        
        Args:
            settings: 設定辞書
        """
        try:
            ui_theme = settings.get("ui_theme")
            if ui_theme:
                self.apply_theme(ui_theme)
                self.logger.debug(f"UIテーマを更新: {ui_theme}")
                
        except Exception as e:
            self.logger.warning(f"UIテーマの更新に失敗: {e}")

    def _update_font_settings(self, settings: Dict[str, Any]) -> None:
        """
        フォント設定の更新
        
        Args:
            settings: 設定辞書
        """
        try:
            font_family = settings.get("font_family")
            font_size = settings.get("font_size")
            
            if font_family or font_size:
                self.apply_font_settings(settings)
                self.logger.debug(f"フォント設定を更新: {font_family}, {font_size}")
                
        except Exception as e:
            self.logger.warning(f"フォント設定の更新に失敗: {e}")

    def apply_theme(self, theme: str) -> None:
        """
        UIテーマを適用
        
        Args:
            theme: テーマ名 ("dark", "light", "system")
        """
        try:
            if theme == "dark":
                # ダークテーマの適用（将来の拡張用）
                self._apply_dark_theme()
            elif theme == "light":
                # ライトテーマの適用
                self._apply_light_theme()
            elif theme == "system":
                # システムテーマの適用
                self._apply_system_theme()
            else:
                # デフォルトテーマは現在のスタイルを維持
                self.logger.debug(f"未知のテーマ: {theme}、デフォルトテーマを維持")
                
            self.logger.info(f"テーマを適用しました: {theme}")
            
        except Exception as e:
            self.logger.error(f"テーマの適用に失敗: {e}")

    def _apply_dark_theme(self) -> None:
        """ダークテーマの適用（将来の拡張用）"""
        # 将来のダークテーマ実装用のプレースホルダー
        self.logger.debug("ダークテーマ適用（未実装）")

    def _apply_light_theme(self) -> None:
        """ライトテーマの適用"""
        # 将来のライトテーマ実装用のプレースホルダー
        self.logger.debug("ライトテーマ適用（未実装）")

    def _apply_system_theme(self) -> None:
        """システムテーマの適用"""
        # システムのテーマ設定に従う
        self.logger.debug("システムテーマ適用（未実装）")

    def apply_font_settings(self, settings: Dict[str, Any]) -> None:
        """
        フォント設定を適用
        
        Args:
            settings: フォント設定を含む設定辞書
        """
        try:
            font_family = settings.get("font_family", "システムデフォルト")
            font_size = settings.get("font_size", 10)

            if font_family != "システムデフォルト":
                font = QFont(font_family, font_size)
                self.main_window.setFont(font)
                
                # アプリケーション全体にフォントを適用
                app = QApplication.instance()
                if app:
                    app.setFont(font)
                    
                self.logger.info(f"フォント設定を適用: {font_family}, {font_size}pt")
            else:
                self.logger.debug("システムデフォルトフォントを使用")
                
        except Exception as e:
            self.logger.error(f"フォント設定の適用に失敗: {e}")

    def get_current_theme(self) -> str:
        """
        現在のテーマを取得
        
        Returns:
            str: 現在のテーマ名
        """
        # 将来の実装用プレースホルダー
        return "system"

    def get_available_themes(self) -> list:
        """
        利用可能なテーマ一覧を取得
        
        Returns:
            list: 利用可能なテーマ名のリスト
        """
        return ["system", "light", "dark"]

    def reset_to_defaults(self) -> None:
        """設定をデフォルトに戻す"""
        try:
            default_settings = {
                "ui_theme": "system",
                "font_family": "システムデフォルト",
                "font_size": 10
            }
            
            self.handle_settings_changed(default_settings)
            self.logger.info("設定をデフォルトに戻しました")
            
        except Exception as e:
            self.logger.error(f"デフォルト設定の適用に失敗: {e}")