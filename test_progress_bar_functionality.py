#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
進捗バー表示機能のテストスクリプト

タスク15で実装した進捗バー機能をテストします。
"""

import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtCore import QTimer, QThread, Signal
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton

from src.gui.main_window import MainWindow


class ProgressTestThread(QThread):
    """進捗テスト用のスレッド"""
    
    progress_updated = Signal(str, int, int, int)  # message, current, total, percentage
    
    def __init__(self, test_type="normal"):
        super().__init__()
        self.test_type = test_type
        
    def run(self):
        """テスト実行"""
        if self.test_type == "normal":
            self._test_normal_progress()
        elif self.test_type == "indeterminate":
            self._test_indeterminate_progress()
        elif self.test_type == "error":
            self._test_error_progress()
            
    def _test_normal_progress(self):
        """通常の進捗テスト"""
        total_files = 50
        
        # スキャン段階
        self.progress_updated.emit("ファイルをスキャン中...", 0, 0, 0)
        time.sleep(1)
        
        # 処理段階
        for i in range(total_files + 1):
            if i < total_files:
                filename = f"document_{i:03d}.pdf"
                message = f"処理中: {filename}"
                self.progress_updated.emit(message, i, total_files, int((i / total_files) * 100))
                time.sleep(0.1)
            else:
                # 完了
                self.progress_updated.emit("インデックス作成完了", total_files, total_files, 100)
                
    def _test_indeterminate_progress(self):
        """不定進捗テスト"""
        messages = [
            "ファイルシステムをスキャン中...",
            "ディレクトリ構造を解析中...",
            "ファイル形式を判定中...",
            "メタデータを収集中..."
        ]
        
        for message in messages:
            self.progress_updated.emit(message, 0, 0, 0)
            time.sleep(2)
            
    def _test_error_progress(self):
        """エラー進捗テスト"""
        total_files = 20
        
        # 正常処理
        for i in range(10):
            filename = f"document_{i:03d}.pdf"
            message = f"処理中: {filename}"
            self.progress_updated.emit(message, i, total_files, int((i / total_files) * 100))
            time.sleep(0.2)
            
        # エラー発生
        self.progress_updated.emit("エラー: ファイルアクセス権限がありません", 10, total_files, 50)


class ProgressTestWidget(QWidget):
    """進捗テスト用のウィジェット"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.test_thread = None
        self._setup_ui()
        
    def _setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # テストボタン
        self.normal_btn = QPushButton("通常進捗テスト")
        self.normal_btn.clicked.connect(self._test_normal_progress)
        layout.addWidget(self.normal_btn)
        
        self.indeterminate_btn = QPushButton("不定進捗テスト")
        self.indeterminate_btn.clicked.connect(self._test_indeterminate_progress)
        layout.addWidget(self.indeterminate_btn)
        
        self.error_btn = QPushButton("エラー進捗テスト")
        self.error_btn.clicked.connect(self._test_error_progress)
        layout.addWidget(self.error_btn)
        
        self.hide_btn = QPushButton("進捗バー非表示")
        self.hide_btn.clicked.connect(self._hide_progress)
        layout.addWidget(self.hide_btn)
        
        self.style_btn = QPushButton("スタイル変更テスト")
        self.style_btn.clicked.connect(self._test_styles)
        layout.addWidget(self.style_btn)
        
    def _test_normal_progress(self):
        """通常進捗テスト"""
        if self.test_thread and self.test_thread.isRunning():
            return
            
        self.test_thread = ProgressTestThread("normal")
        self.test_thread.progress_updated.connect(self._on_progress_updated)
        self.test_thread.start()
        
    def _test_indeterminate_progress(self):
        """不定進捗テスト"""
        if self.test_thread and self.test_thread.isRunning():
            return
            
        self.test_thread = ProgressTestThread("indeterminate")
        self.test_thread.progress_updated.connect(self._on_progress_updated)
        self.test_thread.start()
        
    def _test_error_progress(self):
        """エラー進捗テスト"""
        if self.test_thread and self.test_thread.isRunning():
            return
            
        self.test_thread = ProgressTestThread("error")
        self.test_thread.progress_updated.connect(self._on_progress_updated)
        self.test_thread.start()
        
    def _hide_progress(self):
        """進捗バー非表示"""
        self.main_window.hide_progress("テスト完了")
        
    def _test_styles(self):
        """スタイル変更テスト"""
        styles = ['success', 'warning', 'error', 'info']
        
        for i, style in enumerate(styles):
            QTimer.singleShot(i * 1000, lambda s=style: self._apply_style(s))
            
    def _apply_style(self, style):
        """スタイル適用"""
        self.main_window.set_progress_style(style)
        self.main_window.update_progress(50, 100, f"スタイルテスト: {style}")
        
    def _on_progress_updated(self, message, current, total, percentage):
        """進捗更新ハンドラー"""
        if total > 0:
            self.main_window.update_progress(current, total, message)
        else:
            self.main_window.set_progress_indeterminate(message)


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    
    # メインウィンドウを作成
    main_window = MainWindow()
    main_window.show()
    
    # テストウィジェットを作成
    test_widget = ProgressTestWidget(main_window)
    test_widget.setWindowTitle("進捗バーテスト")
    test_widget.resize(300, 200)
    test_widget.show()
    
    print("進捗バー機能テストを開始します")
    print("テストウィジェットのボタンをクリックして各機能をテストしてください")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()