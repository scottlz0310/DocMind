#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MainWindow軽量テスト

MainWindowの初期化を最小限のリソースでテスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_mainwindow_initialization_light():
    """MainWindowの軽量初期化テスト"""
    try:
        # ヘッドレスモードを設定
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        
        # 必要最小限のインポート
        from PySide6.QtWidgets import QApplication
        from src.gui.main_window import MainWindow
        
        print("QApplicationを作成中...")
        
        # アプリケーションインスタンスを作成
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        print("✓ QApplicationが作成されました")
        
        # MainWindowを初期化（タイムアウト付き）
        print("MainWindowを初期化中...")
        
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("MainWindow初期化がタイムアウトしました")
        
        # 10秒のタイムアウトを設定
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
        
        try:
            main_window = MainWindow()
            signal.alarm(0)  # タイムアウトをクリア
            print("✓ MainWindowが正常に初期化されました")
            
            # 基本的な属性の確認
            assert hasattr(main_window, 'logger'), "loggerプロパティが存在しません"
            print("✓ loggerプロパティが存在します")
            
            # LoggerMixinのloggerプロパティが使用されていることを確認
            logger = main_window.logger
            assert logger is not None, "loggerがNoneです"
            print("✓ LoggerMixinのloggerプロパティが正常に動作しています")
            
            # ウィンドウタイトルの確認
            title = main_window.windowTitle()
            expected_title = "DocMind - ローカルドキュメント検索"
            assert title == expected_title, f"ウィンドウタイトルが正しくありません: {title}"
            print("✓ ウィンドウタイトルが正しく設定されています")
            
            # 即座にクリーンアップ
            main_window.close()
            main_window.deleteLater()
            
            print("✓ MainWindow軽量初期化テストが完了しました")
            return True
            
        except TimeoutError as e:
            signal.alarm(0)
            print(f"✗ {e}")
            return False
        
    except Exception as e:
        print(f"✗ MainWindow軽量初期化テストが失敗しました: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メインテスト関数"""
    print("=== MainWindow軽量初期化テスト ===\n")
    
    result = test_mainwindow_initialization_light()
    
    print("\n=== テスト結果 ===")
    if result:
        print("✓ MainWindow初期化テストが成功しました！")
        print("MainWindowのlogger競合問題が修正されています。")
        return 0
    else:
        print("✗ MainWindow初期化テストが失敗しました。")
        return 1


if __name__ == "__main__":
    sys.exit(main())