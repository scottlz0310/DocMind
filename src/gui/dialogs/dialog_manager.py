#!/usr/bin/env python3
"""
ダイアログマネージャー

main_window.pyから分離されたダイアログ表示・管理機能を提供します。
各種確認ダイアログ、エラーダイアログ、設定ダイアログなどを統一的に管理します。
"""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from ...utils.config import Config
from ...utils.logging_config import LoggerMixin
from ..settings_dialog import SettingsDialog


class DialogManager(LoggerMixin):
    """
    ダイアログ管理クラス

    メインウィンドウから分離されたダイアログ表示機能を提供します。
    各種確認ダイアログ、エラーダイアログ、情報ダイアログを統一的に管理します。
    """

    def __init__(self, parent: QMainWindow):
        """
        ダイアログマネージャーを初期化

        Args:
            parent: 親ウィンドウ（MainWindow）
        """
        self.parent = parent
        self.config = Config()

        self.logger.info("ダイアログマネージャーを初期化しました")

    def open_folder_dialog(self) -> str | None:
        """
        フォルダ選択ダイアログを表示

        Returns:
            選択されたフォルダパス、キャンセル時はNone
        """
        folder_path = QFileDialog.getExistingDirectory(
            self.parent,
            "検索対象フォルダを選択",
            str(Path.home()),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if folder_path:
            self.logger.info(f"フォルダが選択されました: {folder_path}")
            return folder_path

        return None

    def show_search_dialog(self) -> None:
        """検索ダイアログを表示（検索インターフェースにフォーカス）"""
        if hasattr(self.parent, 'search_interface'):
            self.parent.search_interface.search_input.setFocus()
            self.parent.search_interface.search_input.selectAll()

    def show_settings_dialog(self) -> bool:
        """
        設定ダイアログを表示

        Returns:
            設定が変更された場合True
        """
        try:
            dialog = SettingsDialog(self.config, self.parent)

            if hasattr(self.parent, '_on_settings_changed'):
                dialog.settings_changed.connect(self.parent._on_settings_changed)

            if dialog.exec() == SettingsDialog.Accepted:
                self.logger.info("設定が更新されました")
                return True

            return False

        except Exception as e:
            self.logger.error(f"設定ダイアログの表示に失敗しました: {e}")
            self.show_operation_failed_dialog(
                "設定ダイアログ",
                f"設定ダイアログの表示に失敗しました:\n{e}",
                "アプリケーションを再起動してから再試行してください。"
            )
            return False

    def show_about_dialog(self) -> None:
        """バージョン情報ダイアログを表示"""
        QMessageBox.about(
            self.parent,
            "DocMindについて",
            "<h3>DocMind v1.0.0</h3>"
            "<p>ローカルAI搭載ドキュメント検索アプリケーション</p>"
            "<p>完全オフラインで動作する高性能ドキュメント検索ツール</p>"
            "<p><b>技術スタック:</b></p>"
            "<ul>"
            "<li>Python 3.11+</li>"
            "<li>PySide6 (Qt6)</li>"
            "<li>Whoosh (全文検索)</li>"
            "<li>sentence-transformers (セマンティック検索)</li>"
            "</ul>"
            "<p>© 2024 DocMind Project</p>"
        )

    def show_rebuild_confirmation_dialog(self) -> bool:
        """
        インデックス再構築確認ダイアログを表示

        Returns:
            ユーザーが再構築を承認した場合True
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle("🔄 インデックス再構築")
        msg_box.setIcon(QMessageBox.Question)

        message = (
            "検索インデックスを再構築しますか?\n\n"
            "📋 実行される処理:\n"
            "• 既存のインデックスデータを削除\n"
            "• 選択フォルダ内の全ドキュメントを再スキャン\n"
            "• 新しい検索インデックスを作成\n\n"
            "⏱️ 処理時間: ファイル数により数分～数十分\n"
            "💡 処理中も他の機能は使用可能です\n\n"
            "続行しますか？"
        )
        msg_box.setText(message)

        rebuild_button = msg_box.addButton("🚀 再構築開始", QMessageBox.AcceptRole)
        cancel_button = msg_box.addButton("❌ キャンセル", QMessageBox.RejectRole)

        rebuild_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

        msg_box.setDefaultButton(cancel_button)
        msg_box.exec()
        return msg_box.clickedButton() == rebuild_button

    def show_clear_index_confirmation_dialog(self) -> bool:
        """
        インデックスクリア確認ダイアログを表示

        Returns:
            ユーザーがクリアを承認した場合True
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle("🗑️ インデックスクリア")
        msg_box.setIcon(QMessageBox.Warning)

        message = (
            "検索インデックスをクリアしますか?\n\n"
            "⚠️ 実行される処理:\n"
            "• すべての検索インデックスデータを削除\n"
            "• 検索結果とプレビューをクリア\n"
            "• 検索提案キャッシュをリセット\n\n"
            "📋 影響:\n"
            "• 検索機能が一時的に利用不可\n"
            "• 再度インデックス作成が必要\n"
            "• この操作は取り消しできません\n\n"
            "本当にクリアしますか？"
        )
        msg_box.setText(message)

        clear_button = msg_box.addButton("🗑️ クリア実行", QMessageBox.DestructiveRole)
        cancel_button = msg_box.addButton("❌ キャンセル", QMessageBox.RejectRole)

        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)

        msg_box.setDefaultButton(cancel_button)
        msg_box.exec()
        return msg_box.clickedButton() == clear_button

    def show_folder_not_selected_dialog(self) -> None:
        """フォルダ未選択エラーダイアログを表示"""
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle("📁 フォルダが選択されていません")
        msg_box.setIcon(QMessageBox.Warning)

        message = (
            "インデックスを再構築するフォルダが選択されていません。\n\n"
            "📋 操作手順:\n"
            "1. 左ペインのフォルダツリーでフォルダを選択\n"
            "2. または「ファイル」→「フォルダを開く」でフォルダを追加\n"
            "3. 再度インデックス再構築を実行\n\n"
            "💡 ヒント: 複数フォルダがある場合は、再構築したいフォルダをクリックして選択してください。"
        )
        msg_box.setText(message)

        ok_button = msg_box.addButton("✅ 了解", QMessageBox.AcceptRole)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        msg_box.exec()

    def show_system_error_dialog(self, title: str, error_message: str, suggestion: str = "") -> None:
        """
        システムエラーダイアログを表示

        Args:
            title: エラータイトル
            error_message: エラーメッセージ
            suggestion: 対処提案（オプション）
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle(f"🚨 {title}")
        msg_box.setIcon(QMessageBox.Critical)

        message = f"システムエラーが発生しました。\n\n📋 エラー詳細:\n{error_message}\n\n"

        if suggestion:
            message += f"🔧 推奨対処:\n{suggestion}\n\n"

        message += (
            "💡 追加の対処方法:\n"
            "• アプリケーションの再起動\n"
            "• システムの再起動\n"
            "• ディスク容量の確認\n"
            "• ウイルススキャンの実行"
        )

        msg_box.setText(message)

        ok_button = msg_box.addButton("✅ 了解", QMessageBox.AcceptRole)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

        msg_box.exec()

    def show_operation_failed_dialog(self, operation_name: str, error_message: str, suggestion: str = "") -> None:
        """
        操作失敗ダイアログを表示

        Args:
            operation_name: 失敗した操作名
            error_message: エラーメッセージ
            suggestion: 対処提案（オプション）
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle(f"❌ {operation_name}に失敗")
        msg_box.setIcon(QMessageBox.Critical)

        message = f"{operation_name}の実行に失敗しました。\n\n📋 エラー詳細:\n{error_message}\n\n"

        if suggestion:
            message += f"🔧 推奨対処:\n{suggestion}\n\n"

        message += (
            "💡 一般的な対処方法:\n"
            "• 操作を再試行\n"
            "• アプリケーションの再起動\n"
            "• システムリソースの確認\n"
            "• ログファイルの確認"
        )

        msg_box.setText(message)

        retry_button = msg_box.addButton("🔄 再試行", QMessageBox.AcceptRole)
        close_button = msg_box.addButton("❌ 閉じる", QMessageBox.RejectRole)

        retry_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        close_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)

        msg_box.exec()

    def show_component_unavailable_dialog(self, component_name: str) -> None:
        """
        コンポーネント利用不可ダイアログを表示

        Args:
            component_name: 利用不可なコンポーネント名
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle(f"⚠️ {component_name}が利用できません")
        msg_box.setIcon(QMessageBox.Warning)

        message = (
            f"{component_name}が現在利用できません。\n\n"
            "🔍 考えられる原因:\n"
            "• 初期化処理が未完了\n"
            "• システムリソースの不足\n"
            "• 設定ファイルの問題\n"
            "• 権限の問題\n\n"
            "🔧 対処方法:\n"
            "• アプリケーションの再起動\n"
            "• システムリソースの確認\n"
            "• 管理者権限での実行\n\n"
            "💡 この機能は一時的に利用できませんが、他の機能は正常に動作します。"
        )
        msg_box.setText(message)

        ok_button = msg_box.addButton("✅ 了解", QMessageBox.AcceptRole)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)

        msg_box.exec()

    def show_partial_failure_dialog(self, operation_name: str, error_message: str, suggestion: str = "") -> None:
        """
        部分的失敗ダイアログを表示

        Args:
            operation_name: 部分的に失敗した操作名
            error_message: エラーメッセージ
            suggestion: 対処提案（オプション）
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle(f"⚠️ {operation_name}の一部が失敗")
        msg_box.setIcon(QMessageBox.Warning)

        message = (
            f"{operation_name}は部分的に成功しましたが、一部で問題が発生しました。\n\n"
            f"📋 問題詳細:\n{error_message}\n\n"
        )

        if suggestion:
            message += f"🔧 推奨対処:\n{suggestion}\n\n"

        message += (
            "💡 対処オプション:\n"
            "• 現在の状態で継続使用\n"
            "• アプリケーションの再起動\n"
            "• 設定のリセット\n\n"
            "✅ 他の機能は正常に動作しています。"
        )

        msg_box.setText(message)

        ok_button = msg_box.addButton("✅ 了解", QMessageBox.AcceptRole)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)

        msg_box.exec()

    def show_fallback_error_dialog(self, error_message: str) -> None:
        """
        フォールバックエラーダイアログを表示

        Args:
            error_message: エラーメッセージ
        """
        try:
            QMessageBox.critical(
                self.parent,
                "予期しないエラー",
                f"インデックス再構築中に予期しないエラーが発生しました。\n\n"
                f"エラー詳細: {error_message}\n\n"
                "アプリケーションを再起動してから再試行してください。"
            )
        except Exception as e:
            self.logger.error(f"フォールバックエラーダイアログの表示でエラー: {e}")
    def show_improved_timeout_dialog(self, thread_id: str) -> int:
        """
        改善されたタイムアウトダイアログを表示

        Args:
            thread_id: タイムアウトしたスレッドID

        Returns:
            int: ユーザーの選択（QMessageBox.Yes/No/Retry相当）
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle("⏰ 処理タイムアウト")
        msg_box.setIcon(QMessageBox.Warning)

        # 詳細なタイムアウト情報
        message = (
            "インデックス再構築が長時間応答していません。\n\n"
            f"📋 処理情報:\n"
            f"• スレッドID: {thread_id}\n"
            f"• タイムアウト時間: 30分\n\n"
            "🤔 考えられる原因:\n"
            "• 大量のファイルによる処理時間の延長\n"
            "• システムリソースの不足\n"
            "• ファイルアクセス権限の問題\n"
            "• ネットワークドライブの応答遅延\n\n"
            "どのように対処しますか？"
        )
        msg_box.setText(message)

        # カスタムボタンの設定
        force_stop_button = msg_box.addButton("🛑 強制停止", QMessageBox.DestructiveRole)
        continue_button = msg_box.addButton("⏳ 継続待機", QMessageBox.AcceptRole)
        restart_button = msg_box.addButton("🔄 再開始", QMessageBox.ActionRole)

        # ボタンのスタイリング
        force_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

        continue_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)

        restart_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        # デフォルトボタンを継続待機に設定
        msg_box.setDefaultButton(continue_button)

        # ダイアログを実行
        msg_box.exec()
        clicked_button = msg_box.clickedButton()

        if clicked_button == force_stop_button:
            return QMessageBox.Yes  # 強制停止
        elif clicked_button == continue_button:
            return QMessageBox.No   # 継続待機
        elif clicked_button == restart_button:
            return QMessageBox.Retry  # 再開始
        else:
            return QMessageBox.No   # デフォルトは継続
    def show_fallback_error_dialog(self, error_message: str) -> None:
        """
        フォールバックエラーダイアログを表示

        Args:
            error_message: エラーメッセージ
        """
        try:
            QMessageBox.critical(
                self.parent,
                "予期しないエラー",
                f"インデックス再構築中に予期しないエラーが発生しました。\n\n"
                f"エラー詳細: {error_message}\n\n"
                "アプリケーションを再起動してから再試行してください。"
            )
        except Exception as e:
            self.logger.error(f"フォールバックエラーダイアログの表示でエラー: {e}")
