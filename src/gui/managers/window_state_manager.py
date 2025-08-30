#!/usr/bin/env python3
"""
DocMind ウィンドウ状態管理マネージャー

メインウィンドウのサイズ・位置・設定の保存復元・レイアウト状態管理を専門的に担当します。
ウィンドウ状態の永続化、表示設定、キーボードショートカット管理を提供します。
"""


from PySide6.QtCore import QObject, QPoint, QSettings, QSize
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMainWindow

from src.utils.logging_config import LoggerMixin


class WindowStateManager(QObject, LoggerMixin):
    """
    ウィンドウ状態管理マネージャー

    メインウィンドウのサイズ・位置・設定の保存復元、
    キーボードショートカット、表示設定を統合的に処理します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        ウィンドウ状態管理マネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window
        self.settings = QSettings("DocMind", "MainWindow")

        # ショートカット参照を保持
        self.shortcuts = {}

        self.logger.debug("ウィンドウ状態管理マネージャーが初期化されました")

    def setup_window_properties(self) -> None:
        """ウィンドウの基本プロパティを設定"""
        try:
            # ウィンドウタイトルとアイコン
            self.main_window.setWindowTitle("DocMind - ローカルドキュメント検索")

            # 最小サイズを設定
            self.main_window.setMinimumSize(800, 600)

            # 保存された設定を復元
            self.restore_window_state()

            # ウィンドウを画面中央に配置（初回起動時）
            if not self.settings.contains("geometry"):
                self._center_window()

            self.logger.info("ウィンドウプロパティの設定が完了しました")

        except Exception as e:
            self.logger.error(f"ウィンドウプロパティ設定中にエラーが発生: {e}")
            raise

    def setup_shortcuts(self) -> None:
        """キーボードショートカットを設定"""
        try:
            # Escキーでプレビューペインをクリア
            self.shortcuts['clear_preview'] = QShortcut(QKeySequence("Escape"), self.main_window)
            self.shortcuts['clear_preview'].activated.connect(self._clear_preview)

            # F5キーでリフレッシュ
            self.shortcuts['refresh'] = QShortcut(QKeySequence("F5"), self.main_window)
            self.shortcuts['refresh'].activated.connect(self._refresh_view)

            self.logger.info("キーボードショートカットの設定が完了しました")

        except Exception as e:
            self.logger.error(f"ショートカット設定中にエラーが発生: {e}")
            raise

    def setup_accessibility(self) -> None:
        """アクセシビリティ機能を設定"""
        try:
            # ウィンドウのアクセシブル名と説明を設定
            self.main_window.setAccessibleName("DocMind メインウィンドウ")
            self.main_window.setAccessibleDescription("ローカルドキュメント検索アプリケーションのメインウィンドウ")

            # 各ペインにアクセシブル名を設定
            if hasattr(self.main_window, 'folder_tree_container'):
                self.main_window.folder_tree_container.setAccessibleName("フォルダツリーペイン")
                self.main_window.folder_tree_container.setAccessibleDescription("検索対象フォルダの階層構造を表示します")

            if hasattr(self.main_window, 'search_results_widget'):
                self.main_window.search_results_widget.setAccessibleName("検索結果ペイン")
                self.main_window.search_results_widget.setAccessibleDescription("検索結果の一覧を表示します")

            if hasattr(self.main_window, 'preview_widget'):
                self.main_window.preview_widget.setAccessibleName("プレビューペイン")
                self.main_window.preview_widget.setAccessibleDescription("選択されたドキュメントの内容をプレビュー表示します")

            # タブオーダーの設定（キーボードナビゲーション用）
            if all(hasattr(self.main_window, attr) for attr in ['folder_tree_container', 'search_results_widget', 'preview_widget']):
                self.main_window.setTabOrder(self.main_window.folder_tree_container, self.main_window.search_results_widget)
                self.main_window.setTabOrder(self.main_window.search_results_widget, self.main_window.preview_widget)

            self.logger.info("アクセシビリティ機能の設定が完了しました")

        except Exception as e:
            self.logger.error(f"アクセシビリティ設定中にエラーが発生: {e}")

    def save_window_state(self) -> None:
        """ウィンドウ状態を保存"""
        try:
            self.settings.setValue("geometry", self.main_window.saveGeometry())
            self.settings.setValue("windowState", self.main_window.saveState())
            self.settings.setValue("size", self.main_window.size())
            self.settings.setValue("position", self.main_window.pos())

            self.logger.debug("ウィンドウ状態を保存しました")

        except Exception as e:
            self.logger.error(f"ウィンドウ状態保存中にエラーが発生: {e}")

    def restore_window_state(self) -> None:
        """ウィンドウ状態を復元"""
        try:
            # ジオメトリとウィンドウ状態を復元
            geometry = self.settings.value("geometry")
            if geometry:
                self.main_window.restoreGeometry(geometry)

            window_state = self.settings.value("windowState")
            if window_state:
                self.main_window.restoreState(window_state)

            # サイズと位置を復元（フォールバック）
            size = self.settings.value("size", QSize(1200, 800))
            position = self.settings.value("position")

            if isinstance(size, QSize):
                self.main_window.resize(size)

            if isinstance(position, QPoint):
                self.main_window.move(position)

            self.logger.debug("ウィンドウ状態を復元しました")

        except Exception as e:
            self.logger.error(f"ウィンドウ状態復元中にエラーが発生: {e}")
            # エラー時はデフォルトサイズを設定
            self.main_window.resize(1200, 800)

    def apply_theme(self, theme: str) -> None:
        """
        UIテーマを適用

        Args:
            theme: テーマ名（'light', 'dark', 'system'）
        """
        try:
            if theme == "dark":
                # ダークテーマの適用（将来の拡張用）
                self.logger.info("ダークテーマが選択されました（実装予定）")
            elif theme == "light":
                # ライトテーマの適用
                self.logger.info("ライトテーマが適用されました")
            elif theme == "system":
                # システムテーマの適用
                self.logger.info("システムテーマが適用されました")

            # テーマ設定を保存
            self.settings.setValue("theme", theme)

        except Exception as e:
            self.logger.error(f"テーマ適用中にエラーが発生: {e}")

    def apply_font_settings(self, font_family: str, font_size: int) -> None:
        """
        フォント設定を適用

        Args:
            font_family: フォントファミリー
            font_size: フォントサイズ
        """
        try:
            from PySide6.QtGui import QFont

            if font_family != "システムデフォルト":
                font = QFont(font_family, font_size)
                self.main_window.setFont(font)
                QApplication.instance().setFont(font)

                # フォント設定を保存
                self.settings.setValue("font_family", font_family)
                self.settings.setValue("font_size", font_size)

                self.logger.info(f"フォント設定を適用しました: {font_family}, {font_size}pt")

        except Exception as e:
            self.logger.error(f"フォント設定適用中にエラーが発生: {e}")

    def _center_window(self) -> None:
        """ウィンドウを画面中央に配置"""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                window_geometry = self.main_window.frameGeometry()
                center_point = screen_geometry.center()
                window_geometry.moveCenter(center_point)
                self.main_window.move(window_geometry.topLeft())

                self.logger.debug("ウィンドウを画面中央に配置しました")

        except Exception as e:
            self.logger.error(f"ウィンドウ中央配置中にエラーが発生: {e}")

    def _clear_preview(self) -> None:
        """プレビューペインをクリア"""
        if hasattr(self.main_window, 'preview_widget'):
            self.main_window.preview_widget.clear_preview()
            self.main_window.show_status_message("プレビューをクリアしました", 2000)

    def _refresh_view(self) -> None:
        """ビューをリフレッシュ"""
        # TODO: 実際のリフレッシュ処理を実装
        self.main_window.show_status_message("ビューをリフレッシュしました", 2000)

    def get_window_settings(self) -> dict:
        """
        現在のウィンドウ設定を取得

        Returns:
            dict: ウィンドウ設定の辞書
        """
        return {
            'size': self.main_window.size(),
            'position': self.main_window.pos(),
            'theme': self.settings.value("theme", "system"),
            'font_family': self.settings.value("font_family", "システムデフォルト"),
            'font_size': self.settings.value("font_size", 10)
        }

    def cleanup(self) -> None:
        """ウィンドウ状態管理マネージャーのクリーンアップ"""
        try:
            # ウィンドウ状態を保存
            self.save_window_state()

            # ショートカット参照をクリア
            self.shortcuts.clear()

            self.logger.debug("ウィンドウ状態管理マネージャーをクリーンアップしました")

        except Exception as e:
            self.logger.error(f"ウィンドウ状態管理マネージャーのクリーンアップ中にエラー: {e}")
