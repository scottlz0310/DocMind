#!/usr/bin/env python3
"""
DocMind メニュー管理マネージャー

メインウィンドウのメニューバー作成・管理・アクション処理を専門的に担当します。
ファイル、検索、表示、ツール、ヘルプメニューの統合管理を提供します。
"""


from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMenuBar

from src.gui.resources import get_search_icon, get_settings_icon
from src.utils.logging_config import LoggerMixin


class MenuManager(QObject, LoggerMixin):
    """
    メニューバー管理マネージャー

    メインウィンドウのメニューバー作成、アクション設定、
    ショートカット管理を統合的に処理します。
    """

    def __init__(self, main_window: QMainWindow):
        """
        メニュー管理マネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window
        self.menubar: QMenuBar | None = None

        # アクション参照を保持
        self.actions = {}

        self.logger.debug("メニュー管理マネージャーが初期化されました")

    def setup_menu_bar(self) -> None:
        """メニューバーを設定"""
        try:
            self.menubar = self.main_window.menuBar()

            # 各メニューを作成
            self._create_file_menu()
            self._create_search_menu()
            self._create_view_menu()
            self._create_tools_menu()
            self._create_help_menu()

            self.logger.info("メニューバーの設定が完了しました")

        except Exception as e:
            self.logger.error(f"メニューバー設定中にエラーが発生: {e}")
            raise

    def _create_file_menu(self) -> None:
        """ファイルメニューを作成"""
        file_menu = self.menubar.addMenu("ファイル(&F)")

        # フォルダを開くアクション
        self.actions["open_folder"] = QAction("フォルダを開く(&O)...", self.main_window)
        self.actions["open_folder"].setShortcut(QKeySequence.Open)
        self.actions["open_folder"].setStatusTip("検索対象のフォルダを選択します")
        self.actions["open_folder"].triggered.connect(
            self.main_window.dialog_manager.open_folder_dialog
        )
        file_menu.addAction(self.actions["open_folder"])

        file_menu.addSeparator()

        # 終了アクション
        self.actions["exit"] = QAction("終了(&X)", self.main_window)
        self.actions["exit"].setShortcut(QKeySequence.Quit)
        self.actions["exit"].setStatusTip("アプリケーションを終了します")
        self.actions["exit"].triggered.connect(self.main_window.close)
        file_menu.addAction(self.actions["exit"])

    def _create_search_menu(self) -> None:
        """検索メニューを作成"""
        search_menu = self.menubar.addMenu("検索(&S)")

        # 検索実行アクション
        self.actions["search"] = QAction(
            get_search_icon(), "検索(&S)...", self.main_window
        )
        self.actions["search"].setShortcut(QKeySequence.Find)
        self.actions["search"].setStatusTip("ドキュメント検索を実行します")
        self.actions["search"].triggered.connect(
            self.main_window.dialog_manager.show_search_dialog
        )
        search_menu.addAction(self.actions["search"])

        # インデックス再構築アクション
        self.actions["rebuild_index"] = QAction(
            "インデックス再構築(&R)", self.main_window
        )
        self.actions["rebuild_index"].setShortcut(QKeySequence("Ctrl+R"))
        self.actions["rebuild_index"].setStatusTip("検索インデックスを再構築します")
        self.actions["rebuild_index"].triggered.connect(
            self.main_window.index_controller.rebuild_index
        )
        search_menu.addAction(self.actions["rebuild_index"])

        # インデックスクリアアクション
        self.actions["clear_index"] = QAction(
            "インデックスクリア(&C)", self.main_window
        )
        self.actions["clear_index"].setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.actions["clear_index"].setStatusTip("検索インデックスをクリアします")
        self.actions["clear_index"].triggered.connect(
            self.main_window.index_controller.clear_index
        )
        search_menu.addAction(self.actions["clear_index"])

    def _create_view_menu(self) -> None:
        """表示メニューを作成"""
        view_menu = self.menubar.addMenu("表示(&V)")

        # プレビューペイン表示切り替え
        self.actions["toggle_preview"] = QAction(
            "プレビューペイン(&P)", self.main_window
        )
        self.actions["toggle_preview"].setCheckable(True)
        self.actions["toggle_preview"].setChecked(True)
        self.actions["toggle_preview"].setShortcut(QKeySequence("F3"))
        self.actions["toggle_preview"].setStatusTip(
            "プレビューペインの表示を切り替えます"
        )
        self.actions["toggle_preview"].triggered.connect(self._toggle_preview_pane)
        view_menu.addAction(self.actions["toggle_preview"])

    def _create_tools_menu(self) -> None:
        """ツールメニューを作成"""
        tools_menu = self.menubar.addMenu("ツール(&T)")

        # 設定アクション
        self.actions["settings"] = QAction(
            get_settings_icon(), "設定(&S)...", self.main_window
        )
        self.actions["settings"].setShortcut(QKeySequence.Preferences)
        self.actions["settings"].setStatusTip("アプリケーション設定を開きます")
        self.actions["settings"].triggered.connect(self._show_settings_dialog)
        tools_menu.addAction(self.actions["settings"])

    def _create_help_menu(self) -> None:
        """ヘルプメニューを作成"""
        help_menu = self.menubar.addMenu("ヘルプ(&H)")

        # バージョン情報アクション
        self.actions["about"] = QAction("DocMindについて(&A)...", self.main_window)
        self.actions["about"].setStatusTip("アプリケーションの情報を表示します")
        self.actions["about"].triggered.connect(
            self.main_window.dialog_manager.show_about_dialog
        )
        help_menu.addAction(self.actions["about"])

    def _toggle_preview_pane(self) -> None:
        """プレビューペインの表示を切り替え"""
        is_visible = self.main_window.preview_widget.isVisible()
        self.main_window.preview_widget.setVisible(not is_visible)

        status_msg = (
            "プレビューペインを非表示にしました"
            if is_visible
            else "プレビューペインを表示しました"
        )
        self.main_window.show_status_message(status_msg, 2000)

    def _show_settings_dialog(self) -> None:
        """設定ダイアログを表示"""
        if self.main_window.dialog_manager.show_settings_dialog():
            self.main_window.show_status_message("設定が保存されました", 3000)

    def get_action(self, action_name: str) -> QAction | None:
        """
        指定されたアクションを取得

        Args:
            action_name: アクション名

        Returns:
            QAction: 対応するアクション、存在しない場合はNone
        """
        return self.actions.get(action_name)

    def enable_action(self, action_name: str, enabled: bool = True) -> None:
        """
        指定されたアクションの有効/無効を設定

        Args:
            action_name: アクション名
            enabled: 有効にするかどうか
        """
        action = self.get_action(action_name)
        if action:
            action.setEnabled(enabled)
            self.logger.debug(
                f"アクション '{action_name}' を{'有効' if enabled else '無効'}にしました"
            )

    def cleanup(self) -> None:
        """メニュー管理マネージャーのクリーンアップ"""
        try:
            # アクション参照をクリア
            self.actions.clear()
            self.menubar = None

            self.logger.debug("メニュー管理マネージャーをクリーンアップしました")

        except Exception as e:
            self.logger.error(
                f"メニュー管理マネージャーのクリーンアップ中にエラー: {e}"
            )
