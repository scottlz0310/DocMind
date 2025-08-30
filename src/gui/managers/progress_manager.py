"""
進捗管理マネージャー

MainWindowから進捗表示・更新・制御機能を分離
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QMainWindow, QProgressBar


class ProgressManager:
    """進捗表示と制御を管理するクラス"""

    def __init__(self, main_window: QMainWindow):
        """
        進捗管理マネージャーを初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        self.main_window = main_window
        self.progress_bar: QProgressBar | None = None
        self.progress_label: QLabel | None = None
        self.progress_hide_timer: QTimer | None = None

    def initialize(self) -> None:
        """進捗管理コンポーネントを初期化"""
        # メインウィンドウから進捗バーとラベルの参照を取得
        self.progress_bar = getattr(self.main_window, "progress_bar", None)
        self.progress_label = getattr(self.main_window, "progress_label", None)

        # 進捗非表示タイマーを初期化
        self.progress_hide_timer = QTimer()
        self.progress_hide_timer.setSingleShot(True)
        self.progress_hide_timer.timeout.connect(self._actually_hide_progress)

    def show_progress(
        self, message: str, value: int, current: int = 0, total: int = 0
    ) -> None:
        """
        進捗バーを表示し、メッセージと値を設定

        Args:
            message: 表示するメッセージ
            value: 進捗値（0-100）
            current: 現在の処理数
            total: 総処理数
        """
        if not self.progress_bar or not self.progress_label:
            return

        # 進捗非表示タイマーを停止
        if self.progress_hide_timer and self.progress_hide_timer.isActive():
            self.progress_hide_timer.stop()

        # 進捗バーの表示と値設定
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(value)

        # アイコン付きメッセージを生成
        icon_message = self._get_progress_icon_message(message, value)
        self.progress_label.setText(icon_message)
        self.progress_label.setVisible(True)

        # 色情報を取得してスタイル適用
        color_info = self._get_progress_color_info(value)
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 2px solid {color_info['border']};
                border-radius: 5px;
                text-align: center;
                background-color: {color_info['background']};
            }}
            QProgressBar::chunk {{
                background-color: {color_info['chunk']};
                border-radius: 3px;
            }}
        """
        )

        # ツールチップを設定
        tooltip = self._create_progress_tooltip(message, value, current, total)
        self.progress_bar.setToolTip(tooltip)
        self.progress_label.setToolTip(tooltip)

    def _get_progress_icon_message(self, message: str, value: int) -> str:
        """
        進捗値に応じたアイコン付きメッセージを生成

        Args:
            message: 基本メッセージ
            value: 進捗値

        Returns:
            アイコン付きメッセージ
        """
        if value >= 100:
            icon = "✅"
        elif value >= 75:
            icon = "🔄"
        elif value >= 50:
            icon = "⚡"
        elif value >= 25:
            icon = "🔍"
        else:
            icon = "⏳"

        return f"{icon} {message}"

    def _get_progress_color_info(self, value: int) -> dict:
        """
        進捗値に応じた色情報を取得

        Args:
            value: 進捗値

        Returns:
            色情報辞書
        """
        if value >= 100:
            return {"border": "#28a745", "background": "#f8f9fa", "chunk": "#28a745"}
        elif value >= 75:
            return {"border": "#17a2b8", "background": "#f8f9fa", "chunk": "#17a2b8"}
        elif value >= 50:
            return {"border": "#ffc107", "background": "#f8f9fa", "chunk": "#ffc107"}
        elif value >= 25:
            return {"border": "#fd7e14", "background": "#f8f9fa", "chunk": "#fd7e14"}
        else:
            return {"border": "#6c757d", "background": "#f8f9fa", "chunk": "#6c757d"}

    def _create_progress_tooltip(
        self, message: str, value: int, current: int, total: int
    ) -> str:
        """
        進捗ツールチップを作成

        Args:
            message: メッセージ
            value: 進捗値
            current: 現在数
            total: 総数

        Returns:
            ツールチップテキスト
        """
        tooltip_parts = [f"進捗: {value}%"]

        if total > 0:
            tooltip_parts.append(f"処理済み: {current}/{total}")

        if message:
            tooltip_parts.append(f"状態: {message}")

        return "\n".join(tooltip_parts)

    def hide_progress(self, completion_message: str = "") -> None:
        """
        進捗バーを非表示にする（遅延実行）

        Args:
            completion_message: 完了メッセージ
        """
        if completion_message and self.progress_label:
            self.progress_label.setText(f"✅ {completion_message}")

        # 2秒後に実際に非表示にする
        if self.progress_hide_timer:
            self.progress_hide_timer.start(2000)

    def _actually_hide_progress(self) -> None:
        """進捗バーを実際に非表示にする"""
        if self.progress_bar:
            self.progress_bar.setVisible(False)
        if self.progress_label:
            self.progress_label.setVisible(False)

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """
        進捗を更新

        Args:
            current: 現在の処理数
            total: 総処理数
            message: 表示メッセージ
        """
        if total > 0:
            value = int((current / total) * 100)
        else:
            value = 0

        display_message = message if message else "処理中..."
        self.show_progress(display_message, value, current, total)

    def set_progress_indeterminate(self, message: str = "処理中...") -> None:
        """
        不定進捗モードに設定

        Args:
            message: 表示メッセージ
        """
        if self.progress_bar:
            self.progress_bar.setRange(0, 0)  # 不定進捗モード
        if self.progress_label:
            self.progress_label.setText(f"⏳ {message}")
            self.progress_label.setVisible(True)

    def is_progress_visible(self) -> bool:
        """
        進捗バーが表示されているかチェック

        Returns:
            表示状態
        """
        return self.progress_bar.isVisible() if self.progress_bar else False

    def get_progress_value(self) -> int:
        """
        現在の進捗値を取得

        Returns:
            進捗値
        """
        return self.progress_bar.value() if self.progress_bar else 0

    def set_progress_style(self, style: str) -> None:
        """
        進捗バーのスタイルを設定

        Args:
            style: CSSスタイル文字列
        """
        if self.progress_bar:
            self.progress_bar.setStyleSheet(style)

    def cleanup(self) -> None:
        """リソースクリーンアップ"""
        if self.progress_hide_timer:
            self.progress_hide_timer.stop()
            self.progress_hide_timer = None
