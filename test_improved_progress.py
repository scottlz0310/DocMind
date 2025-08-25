#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改善された進捗表示のテストスクリプト（タスク10検証用）

このスクリプトは、改善された進捗表示の動作を確認します。
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer

# メインウィンドウから改善された進捗表示メソッドをインポート
from src.gui.main_window import MainWindow


class ProgressTestWindow(QMainWindow):
    """
    改善された進捗表示をテストするためのウィンドウ
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 改善された進捗表示のテスト")
        self.setGeometry(100, 100, 600, 400)

        # メインウィンドウのインスタンスを作成（進捗表示メソッドを使用するため）
        self.main_window = MainWindow()

        # タイマーとカウンター
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        self.current_progress = 0
        self.total_files = 100

        # UI設定
        self._setup_ui()

    def _setup_ui(self):
        """テスト用UIを設定"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # 説明ラベル
        from PySide6.QtWidgets import QLabel
        info_label = QLabel("📊 改善された進捗表示のテスト")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(info_label)

        # 進捗表示テストボタン
        progress_buttons = [
            ("🔍 スキャン進捗（不定）", self._test_scanning_progress),
            ("⚙️ 処理進捗（定進捗）", self._test_processing_progress),
            ("📚 インデックス作成進捗", self._test_indexing_progress),
            ("✅ 完了表示", self._test_completion_display),
            ("❌ エラー表示", self._test_error_display),
            ("⏹️ 進捗停止", self._stop_progress),
        ]

        for text, callback in progress_buttons:
            button = QPushButton(text)
            button.clicked.connect(callback)
            button.setStyleSheet("""
                QPushButton {
                    padding: 10px;
                    font-size: 12px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: #f0f0f0;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            layout.addWidget(button)

        # 進捗シミュレーションボタン
        layout.addWidget(QLabel("🎬 進捗シミュレーション"))

        sim_layout = QHBoxLayout()

        sim_buttons = [
            ("🚀 高速進捗", self._simulate_fast_progress),
            ("🐌 低速進捗", self._simulate_slow_progress),
            ("⚡ 段階的進捗", self._simulate_staged_progress),
        ]

        for text, callback in sim_buttons:
            button = QPushButton(text)
            button.clicked.connect(callback)
            button.setStyleSheet("""
                QPushButton {
                    padding: 8px;
                    font-size: 11px;
                    border: 1px solid #4CAF50;
                    border-radius: 4px;
                    background-color: #E8F5E8;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #C8E6C9;
                }
            """)
            sim_layout.addWidget(button)

        layout.addLayout(sim_layout)

        # メインウィンドウの進捗バーを表示するためのコンテナ
        layout.addWidget(QLabel("📊 進捗バー表示エリア（メインウィンドウのステータスバーを確認）"))

        # メインウィンドウを表示
        self.main_window.show()
        self.main_window.move(self.x() + self.width() + 20, self.y())

    def _test_scanning_progress(self):
        """スキャン進捗（不定進捗）をテスト"""
        self.main_window.show_progress("ファイルをスキャン中...", 0)
        print("スキャン進捗（不定進捗）を表示しました")

    def _test_processing_progress(self):
        """処理進捗（定進捗）をテスト"""
        self.main_window.show_progress("ドキュメントを処理中...", 45, 45, 100)
        print("処理進捗（定進捗）を表示しました")

    def _test_indexing_progress(self):
        """インデックス作成進捗をテスト"""
        self.main_window.show_progress("インデックスを作成中...", 75, 750, 1000)
        print("インデックス作成進捗を表示しました")

    def _test_completion_display(self):
        """完了表示をテスト"""
        self.main_window.hide_progress("インデックス再構築が完了しました")
        print("完了表示をテストしました")

    def _test_error_display(self):
        """エラー表示をテスト"""
        self.main_window.hide_progress("インデックス再構築でエラーが発生しました")
        print("エラー表示をテストしました")

    def _stop_progress(self):
        """進捗を停止"""
        self.progress_timer.stop()
        self.main_window.hide_progress("処理を停止しました")
        print("進捗を停止しました")

    def _simulate_fast_progress(self):
        """高速進捗をシミュレート"""
        self.current_progress = 0
        self.total_files = 50
        self.progress_timer.start(100)  # 100ms間隔
        print("高速進捗シミュレーションを開始しました")

    def _simulate_slow_progress(self):
        """低速進捗をシミュレート"""
        self.current_progress = 0
        self.total_files = 200
        self.progress_timer.start(500)  # 500ms間隔
        print("低速進捗シミュレーションを開始しました")

    def _simulate_staged_progress(self):
        """段階的進捗をシミュレート"""
        self.current_progress = 0
        self.total_files = 100
        self.progress_timer.start(200)  # 200ms間隔
        print("段階的進捗シミュレーションを開始しました")

    def _update_progress(self):
        """進捗を更新"""
        if self.current_progress >= self.total_files:
            self.progress_timer.stop()
            self.main_window.hide_progress("シミュレーション完了")
            return

        self.current_progress += 1
        percentage = int((self.current_progress / self.total_files) * 100)

        # 段階に応じてメッセージを変更
        if percentage < 20:
            message = "ファイルをスキャン中..."
        elif percentage < 60:
            message = f"ドキュメントを処理中... (sample_file_{self.current_progress}.pdf)"
        elif percentage < 90:
            message = "インデックスを作成中..."
        else:
            message = "最終処理中..."

        self.main_window.show_progress(message, percentage, self.current_progress, self.total_files)

    def closeEvent(self, event):
        """ウィンドウクローズ時の処理"""
        self.progress_timer.stop()
        self.main_window.close()
        event.accept()


def main():
    """メイン関数"""
    app = QApplication(sys.argv)

    # アプリケーションスタイルを設定
    app.setStyle('Fusion')

    # テストウィンドウを作成して表示
    window = ProgressTestWindow()
    window.show()

    print("📊 改善された進捗表示のテストを開始します")
    print("各ボタンをクリックして、改善された進捗表示の動作を確認してください。")
    print("右側のメインウィンドウのステータスバーで進捗バーの変化を確認できます。")
    print("ESCキーまたはウィンドウを閉じてテストを終了します。")

    # アプリケーションを実行
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
