"""
エラーダイアログとユーザー通知機能

ユーザーフレンドリーなエラーメッセージの表示と、
システム状態の通知機能を提供します。
"""

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..utils.graceful_degradation import get_global_degradation_manager
from ..utils.logging_config import LoggerMixin


class ErrorDialog(QDialog, LoggerMixin):
    """
    詳細なエラー情報を表示するダイアログ

    ユーザーフレンドリーなメッセージと技術的な詳細情報を
    分けて表示し、適切なアクションを提案します。
    """

    def __init__(
        self,
        title: str,
        message: str,
        details: str = None,
        recovery_suggestions: list = None,
        parent: QWidget = None,
    ):
        """
        エラーダイアログを初期化

        Args:
            title: エラーのタイトル
            message: ユーザー向けメッセージ
            details: 技術的な詳細情報
            recovery_suggestions: 回復のための提案リスト
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(500, 300)

        self._setup_ui(message, details, recovery_suggestions)
        self.logger.debug(f"エラーダイアログを作成: {title}")

    def _setup_ui(self, message: str, details: str, recovery_suggestions: list):
        """UIを設定"""
        layout = QVBoxLayout(self)

        # エラーアイコンとメッセージ
        message_layout = QHBoxLayout()

        # エラーアイコン
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(self.style().SP_MessageBoxCritical).pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignTop)
        message_layout.addWidget(icon_label)

        # メッセージテキスト
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 12px; margin: 10px;")
        message_layout.addWidget(message_label, 1)

        layout.addLayout(message_layout)

        # 回復提案
        if recovery_suggestions:
            suggestions_group = QGroupBox("推奨される対処法:")
            suggestions_layout = QVBoxLayout(suggestions_group)

            for suggestion in recovery_suggestions:
                suggestion_label = QLabel(f"• {suggestion}")
                suggestion_label.setWordWrap(True)
                suggestion_label.setStyleSheet("margin: 2px 10px;")
                suggestions_layout.addWidget(suggestion_label)

            layout.addWidget(suggestions_group)

        # 詳細情報(折りたたみ可能)
        if details:
            self._add_details_section(layout, details)

        # ボタン
        button_layout = QHBoxLayout()

        # システム状態ボタン
        status_button = QPushButton("システム状態を確認")
        status_button.clicked.connect(self._show_system_status)
        button_layout.addWidget(status_button)

        button_layout.addStretch()

        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _add_details_section(self, layout: QVBoxLayout, details: str):
        """詳細情報セクションを追加"""
        details_group = QGroupBox("技術的な詳細情報:")
        details_layout = QVBoxLayout(details_group)

        # 詳細情報を表示するテキストエリア
        details_text = QTextEdit()
        details_text.setPlainText(details)
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(150)
        details_text.setStyleSheet("font-family: monospace; font-size: 10px;")
        details_layout.addWidget(details_text)

        layout.addWidget(details_group)

    def _show_system_status(self):
        """システム状態ダイアログを表示"""
        status_dialog = SystemStatusDialog(self)
        status_dialog.exec()


class SystemStatusDialog(QDialog, LoggerMixin):
    """
    システム全体の健全性状態を表示するダイアログ
    """

    def __init__(self, parent: QWidget = None):
        """システム状態ダイアログを初期化"""
        super().__init__(parent)
        self.setWindowTitle("システム状態")
        self.setModal(True)
        self.setMinimumSize(600, 400)

        self._setup_ui()
        self._update_status()

        # 定期的に状態を更新
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(5000)  # 5秒間隔

    def _setup_ui(self):
        """UIを設定"""
        layout = QVBoxLayout(self)

        # 全体的な健全性表示
        self.overall_health_label = QLabel()
        self.overall_health_label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
        layout.addWidget(self.overall_health_label)

        # プログレスバー
        self.health_progress = QProgressBar()
        self.health_progress.setRange(0, 100)
        layout.addWidget(self.health_progress)

        # コンポーネント状態リスト
        scroll_area = QScrollArea()
        self.components_widget = QWidget()
        self.components_layout = QVBoxLayout(self.components_widget)
        scroll_area.setWidget(self.components_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # ボタン
        button_layout = QHBoxLayout()

        refresh_button = QPushButton("更新")
        refresh_button.clicked.connect(self._update_status)
        button_layout.addWidget(refresh_button)

        button_layout.addStretch()

        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _update_status(self):
        """システム状態を更新"""
        try:
            degradation_manager = get_global_degradation_manager()
            health = degradation_manager.get_system_health()

            # 全体的な健全性を更新
            overall_health = health.get("overall_health", "unknown")
            total_components = health.get("total_components", 0)
            healthy_count = health.get("healthy", 0)

            if overall_health == "healthy":
                self.overall_health_label.setText("✅ システムは正常に動作しています")
                self.overall_health_label.setStyleSheet(
                    "color: green; font-size: 14px; font-weight: bold; margin: 10px;"
                )
                health_percentage = 100
            elif overall_health == "degraded":
                self.overall_health_label.setText("⚠️ システムは制限付きで動作しています")
                self.overall_health_label.setStyleSheet(
                    "color: orange; font-size: 14px; font-weight: bold; margin: 10px;"
                )
                health_percentage = int((healthy_count / total_components) * 100) if total_components > 0 else 0
            else:
                self.overall_health_label.setText("❌ システムに重大な問題があります")
                self.overall_health_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold; margin: 10px;")
                health_percentage = int((healthy_count / total_components) * 100) if total_components > 0 else 0

            self.health_progress.setValue(health_percentage)

            # コンポーネント状態を更新
            self._update_components_display(health.get("components", {}))

        except Exception as e:
            self.logger.error(f"システム状態の更新に失敗: {e}")
            self.overall_health_label.setText("❓ システム状態を取得できません")
            self.overall_health_label.setStyleSheet("color: gray; font-size: 14px; font-weight: bold; margin: 10px;")

    def _update_components_display(self, components: dict[str, Any]):
        """コンポーネント表示を更新"""
        # 既存のウィジェットをクリア
        for i in reversed(range(self.components_layout.count())):
            child = self.components_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # 各コンポーネントの状態を表示
        for component_name, component_info in components.items():
            component_widget = self._create_component_widget(component_name, component_info)
            self.components_layout.addWidget(component_widget)

        self.components_layout.addStretch()

    def _create_component_widget(self, name: str, info: dict[str, Any]) -> QWidget:
        """コンポーネント表示ウィジェットを作成"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Box)
        widget.setStyleSheet("margin: 2px; padding: 5px;")

        layout = QVBoxLayout(widget)

        # コンポーネント名と状態
        header_layout = QHBoxLayout()

        # 状態アイコン
        status = info.get("status", "unknown")
        if status == "healthy":
            status_icon = "✅"
            status_color = "green"
        elif status == "degraded":
            status_icon = "⚠️"
            status_color = "orange"
        elif status == "failed":
            status_icon = "❌"
            status_color = "red"
        else:
            status_icon = "❓"
            status_color = "gray"

        name_label = QLabel(f"{status_icon} {name}")
        name_label.setStyleSheet(f"font-weight: bold; color: {status_color};")
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        # フォールバック状態
        if info.get("fallback_active", False):
            fallback_label = QLabel("(フォールバック動作中)")
            fallback_label.setStyleSheet("color: blue; font-style: italic;")
            header_layout.addWidget(fallback_label)

        layout.addLayout(header_layout)

        # エラーメッセージ
        error_message = info.get("error_message")
        if error_message:
            error_label = QLabel(f"エラー: {error_message}")
            error_label.setStyleSheet("color: red; font-size: 10px; margin-left: 20px;")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)

        # 機能状態
        capabilities = info.get("capabilities", {})
        if capabilities:
            caps_layout = QHBoxLayout()
            caps_label = QLabel("機能:")
            caps_label.setStyleSheet("font-size: 10px; margin-left: 20px;")
            caps_layout.addWidget(caps_label)

            for cap_name, cap_enabled in capabilities.items():
                cap_status = "✅" if cap_enabled else "❌"
                cap_widget = QLabel(f"{cap_status} {cap_name}")
                cap_widget.setStyleSheet("font-size: 10px; margin: 0 5px;")
                caps_layout.addWidget(cap_widget)

            caps_layout.addStretch()
            layout.addLayout(caps_layout)

        return widget

    def closeEvent(self, event):
        """ダイアログが閉じられる時の処理"""
        if hasattr(self, "update_timer"):
            self.update_timer.stop()
        super().closeEvent(event)


class UserNotificationManager(LoggerMixin):
    """
    ユーザー通知を管理するクラス

    エラー、警告、情報メッセージを適切な形式で表示し、
    システム状態に応じた通知を提供します。
    """

    def __init__(self, parent_widget: QWidget = None):
        """
        通知マネージャーを初期化

        Args:
            parent_widget: 親ウィジェット
        """
        self.parent_widget = parent_widget

    def show_error(
        self,
        title: str,
        message: str,
        details: str = None,
        recovery_suggestions: list = None,
    ):
        """
        エラーダイアログを表示

        Args:
            title: エラーのタイトル
            message: ユーザー向けメッセージ
            details: 技術的な詳細情報
            recovery_suggestions: 回復のための提案リスト
        """
        try:
            dialog = ErrorDialog(title, message, details, recovery_suggestions, self.parent_widget)
            dialog.exec()
        except Exception as e:
            self.logger.error(f"エラーダイアログの表示に失敗: {e}")
            # フォールバック: 標準メッセージボックス
            QMessageBox.critical(self.parent_widget, title, message)

    def show_warning(self, title: str, message: str):
        """
        警告メッセージを表示

        Args:
            title: 警告のタイトル
            message: 警告メッセージ
        """
        try:
            QMessageBox.warning(self.parent_widget, title, message)
        except Exception as e:
            self.logger.error(f"警告ダイアログの表示に失敗: {e}")

    def show_info(self, title: str, message: str):
        """
        情報メッセージを表示

        Args:
            title: 情報のタイトル
            message: 情報メッセージ
        """
        try:
            QMessageBox.information(self.parent_widget, title, message)
        except Exception as e:
            self.logger.error(f"情報ダイアログの表示に失敗: {e}")

    def show_system_degradation_warning(self):
        """システム劣化の警告を表示"""
        try:
            degradation_manager = get_global_degradation_manager()
            health = degradation_manager.get_system_health()

            if health["overall_health"] == "degraded":
                message = (
                    "システムの一部機能に問題が発生しています。\n"
                    "一部の機能が制限される可能性があります。\n\n"
                    f"健全なコンポーネント: {health['healthy']}/{health['total_components']}\n"
                    f"劣化したコンポーネント: {health['degraded']}\n"
                    f"失敗したコンポーネント: {health['failed']}"
                )

                recovery_suggestions = [
                    "アプリケーションを再起動してください",
                    "システム状態を確認して詳細情報を確認してください",
                    "問題が継続する場合は、ログファイルを確認してください",
                ]

                self.show_error(
                    "システム劣化警告",
                    message,
                    recovery_suggestions=recovery_suggestions,
                )

            elif health["overall_health"] == "critical":
                message = (
                    "システムに重大な問題が発生しています。\n"
                    "多くの機能が利用できない可能性があります。\n\n"
                    f"健全なコンポーネント: {health['healthy']}/{health['total_components']}\n"
                    f"劣化したコンポーネント: {health['degraded']}\n"
                    f"失敗したコンポーネント: {health['failed']}"
                )

                recovery_suggestions = [
                    "アプリケーションを再起動してください",
                    "データディレクトリの権限を確認してください",
                    "ディスク容量を確認してください",
                    "システム管理者にお問い合わせください",
                ]

                self.show_error(
                    "システム重大エラー",
                    message,
                    recovery_suggestions=recovery_suggestions,
                )

        except Exception as e:
            self.logger.error(f"システム劣化警告の表示に失敗: {e}")

    def show_component_failure_notification(self, component_name: str, error_message: str):
        """
        コンポーネント障害の通知を表示

        Args:
            component_name: 障害が発生したコンポーネント名
            error_message: エラーメッセージ
        """
        try:
            title = f"{component_name} 機能エラー"
            message = f"{component_name}で問題が発生しました。\n\n詳細: {error_message}"

            recovery_suggestions = [
                "機能を再試行してください",
                "アプリケーションを再起動してください",
                "システム状態を確認してください",
            ]

            self.show_error(title, message, recovery_suggestions=recovery_suggestions)

        except Exception as e:
            self.logger.error(f"コンポーネント障害通知の表示に失敗: {e}")
