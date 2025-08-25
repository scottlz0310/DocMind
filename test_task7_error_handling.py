#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスク7: エラーハンドリングシステムの実装テスト

インデックス再構築のエラーハンドリング機能をテストします。
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer
from src.gui.main_window import MainWindow
from src.utils.logging_config import setup_logging


class ErrorHandlingTester:
    """エラーハンドリング機能のテスター"""

    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.main_window = None
        self.test_folder = None

    def setup_test_environment(self):
        """テスト環境をセットアップ"""
        # ログ設定
        setup_logging(level="DEBUG", enable_console=True)

        # テスト用フォルダを作成
        self.test_folder = tempfile.mkdtemp(prefix="docmind_error_test_")
        print(f"テスト用フォルダ: {self.test_folder}")

        # テスト用ファイルを作成
        test_files = [
            "test1.txt",
            "test2.pdf",
            "test3.docx"
        ]

        for filename in test_files:
            file_path = Path(self.test_folder) / filename
            file_path.write_text(f"テストファイル: {filename}")

        print(f"テストファイルを作成しました: {test_files}")

    def cleanup_test_environment(self):
        """テスト環境をクリーンアップ"""
        if self.test_folder and os.path.exists(self.test_folder):
            shutil.rmtree(self.test_folder)
            print(f"テスト用フォルダを削除しました: {self.test_folder}")

    def test_error_analysis(self):
        """エラー分析機能のテスト"""
        print("\n=== エラー分析機能のテスト ===")

        # メインウィンドウを作成
        self.main_window = MainWindow()

        # 各種エラーメッセージのテスト
        test_cases = [
            ("ファイルが見つかりません", "file_access"),
            ("アクセスが拒否されました", "permission"),
            ("メモリ不足です", "resource"),
            ("ディスク容量が不足しています", "disk_space"),
            ("データが破損しています", "corruption"),
            ("タイムアウトが発生しました", "timeout"),
            ("予期しないエラー", "system")
        ]

        for error_message, expected_type in test_cases:
            result_type = self.main_window._analyze_error_type(error_message)
            status = "✅" if result_type == expected_type else "❌"
            print(f"{status} '{error_message}' -> {result_type} (期待値: {expected_type})")

    def test_error_handling_methods(self):
        """エラーハンドリングメソッドのテスト"""
        print("\n=== エラーハンドリングメソッドのテスト ===")

        if not self.main_window:
            self.main_window = MainWindow()

        # モックのスレッド情報を作成
        class MockThreadInfo:
            def __init__(self, folder_path):
                self.folder_path = folder_path

        thread_info = MockThreadInfo(self.test_folder)

        # 各エラーハンドリングメソッドの存在確認
        error_methods = [
            "_handle_file_access_error",
            "_handle_permission_error",
            "_handle_resource_error",
            "_handle_disk_space_error",
            "_handle_corruption_error",
            "_handle_system_error"
        ]

        for method_name in error_methods:
            if hasattr(self.main_window, method_name):
                print(f"✅ {method_name} メソッドが実装されています")
            else:
                print(f"❌ {method_name} メソッドが見つかりません")

    def test_cleanup_functionality(self):
        """クリーンアップ機能のテスト"""
        print("\n=== クリーンアップ機能のテスト ===")

        if not self.main_window:
            self.main_window = MainWindow()

        # クリーンアップメソッドの存在確認
        cleanup_methods = [
            "_cleanup_partial_index",
            "_perform_error_cleanup"
        ]

        for method_name in cleanup_methods:
            if hasattr(self.main_window, method_name):
                print(f"✅ {method_name} メソッドが実装されています")

                # 実際にメソッドを呼び出してエラーが発生しないかテスト
                try:
                    if method_name == "_cleanup_partial_index":
                        self.main_window._cleanup_partial_index()
                        print(f"  ✅ {method_name} の実行が成功しました")
                    elif method_name == "_perform_error_cleanup":
                        # モックパラメータでテスト
                        class MockThreadInfo:
                            def __init__(self, folder_path):
                                self.folder_path = folder_path

                        mock_thread_info = MockThreadInfo(self.test_folder)
                        self.main_window._perform_error_cleanup("test_thread", "test", mock_thread_info)
                        print(f"  ✅ {method_name} の実行が成功しました")
                except Exception as e:
                    print(f"  ❌ {method_name} の実行でエラー: {e}")
            else:
                print(f"❌ {method_name} メソッドが見つかりません")

    def test_signal_connections(self):
        """シグナル接続のテスト"""
        print("\n=== シグナル接続のテスト ===")

        if not self.main_window:
            self.main_window = MainWindow()

        # スレッドマネージャーのシグナル接続確認
        if hasattr(self.main_window, 'thread_manager'):
            thread_manager = self.main_window.thread_manager

            # thread_errorシグナルの存在確認
            if hasattr(thread_manager, 'thread_error'):
                print("✅ thread_errorシグナルが存在します")

                # _on_thread_errorメソッドの存在確認
                if hasattr(self.main_window, '_on_thread_error'):
                    print("✅ _on_thread_errorメソッドが実装されています")
                else:
                    print("❌ _on_thread_errorメソッドが見つかりません")
            else:
                print("❌ thread_errorシグナルが見つかりません")
        else:
            print("❌ thread_managerが見つかりません")

        # タイムアウトマネージャーのシグナル接続確認
        if hasattr(self.main_window, 'timeout_manager'):
            timeout_manager = self.main_window.timeout_manager

            if hasattr(timeout_manager, 'timeout_occurred'):
                print("✅ timeout_occurredシグナルが存在します")

                # _handle_rebuild_timeoutメソッドの存在確認
                if hasattr(self.main_window, '_handle_rebuild_timeout'):
                    print("✅ _handle_rebuild_timeoutメソッドが実装されています")
                else:
                    print("❌ _handle_rebuild_timeoutメソッドが見つかりません")
            else:
                print("❌ timeout_occurredシグナルが見つかりません")
        else:
            print("❌ timeout_managerが見つかりません")

        # _on_rebuild_errorメソッドの存在確認
        if hasattr(self.main_window, '_on_rebuild_error'):
            print("✅ _on_rebuild_errorメソッドが実装されています")
        else:
            print("❌ _on_rebuild_errorメソッドが見つかりません")

    def run_tests(self):
        """すべてのテストを実行"""
        print("タスク7: エラーハンドリングシステムの実装テスト開始")
        print("=" * 60)

        try:
            self.setup_test_environment()

            # 各テストを実行
            self.test_error_analysis()
            self.test_error_handling_methods()
            self.test_cleanup_functionality()
            self.test_signal_connections()

            print("\n" + "=" * 60)
            print("✅ すべてのテストが完了しました")

        except Exception as e:
            print(f"\n❌ テスト実行中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.cleanup_test_environment()

            # メインウィンドウを閉じる
            if self.main_window:
                self.main_window.close()


def main():
    """メイン関数"""
    tester = ErrorHandlingTester()

    # テストを実行
    tester.run_tests()

    print("\nテスト完了。Enterキーを押して終了してください...")
    input()


if __name__ == "__main__":
    main()
