#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改善されたダイアログのテストスクリプト（タスク10検証用）

このスクリプトは、改善されたユーザーインターフェースの動作を確認します。
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PySide6.QtCore import Qt

# メインウィンドウから改善されたダイアログメソッドをインポート
from src.gui.main_window import MainWindow


class DialogTestWindow(QMainWindow):
    """
    改善されたダイアログをテストするためのウィンドウ
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧪 改善されたダイアログのテスト")
        self.setGeometry(100, 100, 400, 300)

        # メインウィンドウのインスタンスを作成（ダイアログメソッドを使用するため）
        self.main_window = MainWindow()

        # UI設定
        self._setup_ui()

    def _setup_ui(self):
        """テスト用UIを設定"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # テストボタンを作成
        buttons = [
            ("🔄 インデックス再構築確認ダイアログ", self._test_rebuild_confirmation),
            ("📁 フォルダ未選択ダイアログ", self._test_folder_not_selected),
            ("⚠️ スレッド開始エラーダイアログ", self._test_thread_start_error),
            ("🚨 システムエラーダイアログ", self._test_system_error),
            ("⏰ タイムアウトダイアログ", self._test_timeout_dialog),
            ("🗑️ インデックスクリア確認ダイアログ", self._test_clear_confirmation),
            ("⚠️ コンポーネント利用不可ダイアログ", self._test_component_unavailable),
            ("❌ 操作失敗ダイアログ", self._test_operation_failed),
            ("⚠️ 部分的失敗ダイアログ", self._test_partial_failure),
        ]

        for text, callback in buttons:
            button = QPushButton(text)
            button.clicked.connect(callback)
            button.setStyleSheet("""
                QPushButton {
                    padding: 10px;
                    font-size: 12px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: #f0f0f0;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            layout.addWidget(button)

    def _test_rebuild_confirmation(self):
        """インデックス再構築確認ダイアログをテスト"""
        result = self.main_window._show_rebuild_confirmation_dialog()
        print(f"再構築確認ダイアログ結果: {result}")

    def _test_folder_not_selected(self):
        """フォルダ未選択ダイアログをテスト"""
        self.main_window._show_folder_not_selected_dialog()
        print("フォルダ未選択ダイアログを表示しました")

    def _test_thread_start_error(self):
        """スレッド開始エラーダイアログをテスト"""
        error_msg = "最大同時実行数に達しています (2/2)。\n他の処理が完了してから再試行してください。"
        self.main_window._show_thread_start_error_dialog(error_msg)
        print("スレッド開始エラーダイアログを表示しました")

    def _test_system_error(self):
        """システムエラーダイアログをテスト"""
        self.main_window._show_system_error_dialog(
            "インデックス再構築エラー",
            "メモリ不足により処理が中断されました。",
            "他のアプリケーションを終了してから再試行してください。"
        )
        print("システムエラーダイアログを表示しました")

    def _test_timeout_dialog(self):
        """タイムアウトダイアログをテスト"""
        result = self.main_window._show_improved_timeout_dialog("test_thread_001")
        print(f"タイムアウトダイアログ結果: {result}")

    def _test_clear_confirmation(self):
        """インデックスクリア確認ダイアログをテスト"""
        result = self.main_window._show_clear_index_confirmation_dialog()
        print(f"クリア確認ダイアログ結果: {result}")

    def _test_component_unavailable(self):
        """コンポーネント利用不可ダイアログをテスト"""
        self.main_window._show_component_unavailable_dialog("インデックスマネージャー")
        print("コンポーネント利用不可ダイアログを表示しました")

    def _test_operation_failed(self):
        """操作失敗ダイアログをテスト"""
        self.main_window._show_operation_failed_dialog(
            "インデックスクリア",
            "ファイルアクセス権限が不足しています。",
            "管理者権限でアプリケーションを実行してください。"
        )
        print("操作失敗ダイアログを表示しました")

    def _test_partial_failure(self):
        """部分的失敗ダイアログをテスト"""
        self.main_window._show_partial_failure_dialog(
            "設定変更",
            "フォント設定の適用に失敗しました。",
            "アプリケーションを再起動すると正しく適用されます。"
        )
        print("部分的失敗ダイアログを表示しました")


def main():
    """メイン関数"""
    app = QApplication(sys.argv)

    # アプリケーションスタイルを設定
    app.setStyle('Fusion')

    # テストウィンドウを作成して表示
    window = DialogTestWindow()
    window.show()

    print("🧪 改善されたダイアログのテストを開始します")
    print("各ボタンをクリックして、改善されたダイアログの動作を確認してください。")
    print("ESCキーまたはウィンドウを閉じてテストを終了します。")

    # アプリケーションを実行
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
