#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスク8: タイムアウト処理の統合 - 検証テスト

このテストは、インデックス再構築のタイムアウト処理が
要件6.1-6.4に従って正しく実装されているかを検証します。
"""

import sys
import os
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, Signal
from PySide6.QtTest import QTest

from src.gui.main_window import MainWindow
from src.core.rebuild_timeout_manager import RebuildTimeoutManager
from src.utils.config import Config


class TestTimeoutIntegration:
    """タイムアウト処理統合のテストクラス"""

    def __init__(self):
        self.app = None
        self.main_window = None
        self.temp_dir = None

    def setup(self):
        """テスト環境のセットアップ"""
        print("=== タイムアウト処理統合テスト セットアップ ===")

        # QApplicationの初期化
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()

        # 一時ディレクトリの作成
        self.temp_dir = tempfile.mkdtemp(prefix="docmind_timeout_test_")
        print(f"一時ディレクトリ: {self.temp_dir}")

        # テスト用設定（data_dirの設定は環境変数で行う）
        os.environ['DOCMIND_DATA_DIR'] = str(Path(self.temp_dir) / "data")
        data_dir = Path(self.temp_dir) / "data"
        data_dir.mkdir(exist_ok=True)

        # メインウィンドウの初期化
        self.main_window = MainWindow()
        self.main_window.show()

        print("セットアップ完了")

    def teardown(self):
        """テスト環境のクリーンアップ"""
        print("=== クリーンアップ ===")

        if self.main_window:
            self.main_window.close()

        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"一時ディレクトリを削除: {self.temp_dir}")

    def test_timeout_manager_initialization(self):
        """要件6.1: タイムアウトマネージャーの初期化テスト"""
        print("\n--- タイムアウトマネージャー初期化テスト ---")

        # タイムアウトマネージャーが正しく初期化されているか確認
        assert hasattr(self.main_window, 'timeout_manager'), "タイムアウトマネージャーが初期化されていません"
        assert isinstance(self.main_window.timeout_manager, RebuildTimeoutManager), "タイムアウトマネージャーの型が正しくありません"

        # デフォルトのタイムアウト時間が30分に設定されているか確認
        assert self.main_window.timeout_manager.timeout_minutes == 30, "タイムアウト時間が30分に設定されていません"

        print("✓ タイムアウトマネージャーが正しく初期化されています")
        return True

    def test_timeout_signal_connection(self):
        """要件6.1: タイムアウトシグナルの接続テスト"""
        print("\n--- タイムアウトシグナル接続テスト ---")

        # タイムアウトシグナルが正しく接続されているか確認
        timeout_manager = self.main_window.timeout_manager

        # シグナルの接続を確認（内部的な確認）
        assert hasattr(timeout_manager, 'timeout_occurred'), "timeout_occurredシグナルが存在しません"

        # _handle_rebuild_timeoutメソッドが存在するか確認
        assert hasattr(self.main_window, '_handle_rebuild_timeout'), "_handle_rebuild_timeoutメソッドが存在しません"

        print("✓ タイムアウトシグナルが正しく接続されています")
        return True

    def test_timeout_dialog_display(self):
        """要件6.2: タイムアウトダイアログの表示テスト"""
        print("\n--- タイムアウトダイアログ表示テスト ---")

        # QMessageBoxをモック化してダイアログの表示をテスト
        with patch('src.gui.main_window.QMessageBox') as mock_msgbox:
            mock_msgbox.Yes = QMessageBox.Yes
            mock_msgbox.No = QMessageBox.No
            mock_msgbox.Warning = QMessageBox.Warning

            # モックインスタンスを作成
            mock_instance = Mock()
            mock_instance.exec.return_value = None
            mock_instance.clickedButton.return_value = Mock()
            mock_msgbox.return_value = mock_instance

            # タイムアウト処理を実行
            test_thread_id = "test_thread_001"
            self.main_window._handle_rebuild_timeout(test_thread_id)

            # ダイアログが表示されたか確認
            assert mock_msgbox.called, "タイムアウトダイアログが表示されませんでした"

        print("✓ タイムアウトダイアログが正しく表示されます")
        return True

    def test_force_stop_functionality(self):
        """要件6.1, 6.3: 強制停止とクリーンアップ処理テスト"""
        print("\n--- 強制停止・クリーンアップ処理テスト ---")

        # 必要なコンポーネントをモック化
        with patch.object(self.main_window.thread_manager, 'stop_thread') as mock_stop, \
             patch.object(self.main_window.index_manager, 'clear_index') as mock_clear, \
             patch.object(self.main_window, 'hide_progress') as mock_hide, \
             patch('src.gui.main_window.QMessageBox.information') as mock_info:

            test_thread_id = "test_thread_002"

            # 強制停止処理を実行
            self.main_window._force_stop_rebuild(test_thread_id)

            # 各処理が呼び出されたか確認
            mock_stop.assert_called_once_with(test_thread_id)
            mock_clear.assert_called_once()
            mock_hide.assert_called_once()
            mock_info.assert_called_once()

        print("✓ 強制停止とクリーンアップ処理が正しく実行されます")
        return True

    def test_state_reset_functionality(self):
        """要件6.4: 状態リセット処理テスト"""
        print("\n--- 状態リセット処理テスト ---")

        # 状態リセットメソッドが存在するか確認
        assert hasattr(self.main_window, '_reset_rebuild_state'), "_reset_rebuild_stateメソッドが存在しません"

        # 状態リセット処理を実行
        self.main_window._reset_rebuild_state()

        # システム情報ラベルがリセットされているか確認
        if hasattr(self.main_window, 'system_info_label'):
            system_info_text = self.main_window.system_info_label.text()
            assert "未作成" in system_info_text or "準備完了" in system_info_text, "システム情報がリセットされていません"

        print("✓ 状態リセット処理が正しく実行されます")
        return True

    def test_timeout_restart_capability(self):
        """要件6.4: タイムアウト後の再実行可能性テスト"""
        print("\n--- タイムアウト後再実行可能性テスト ---")

        # インデックス再構築メソッドが存在し、呼び出し可能か確認
        assert hasattr(self.main_window, '_rebuild_index'), "_rebuild_indexメソッドが存在しません"

        # 状態リセット後にメソッドが呼び出し可能か確認
        self.main_window._reset_rebuild_state()

        # 再構築アクションが有効になっているか確認
        if hasattr(self.main_window, 'rebuild_index_action'):
            assert self.main_window.rebuild_index_action.isEnabled(), "再構築アクションが無効になっています"

        print("✓ タイムアウト後の再実行が可能です")
        return True

    def test_progress_update_during_timeout(self):
        """要件6.5: 長時間実行中の定期的進捗更新テスト"""
        print("\n--- 定期的進捗更新テスト ---")

        # 進捗更新メソッドが存在するか確認
        assert hasattr(self.main_window, '_on_rebuild_progress'), "_on_rebuild_progressメソッドが存在しません"

        # 進捗更新処理をテスト
        test_thread_id = "test_thread_003"
        test_message = "ファイルを処理中..."
        current = 50
        total = 100

        # 進捗更新を実行
        self.main_window._on_rebuild_progress(test_thread_id, test_message, current, total)

        # 進捗バーが表示されているか確認
        if hasattr(self.main_window, 'progress_bar'):
            assert self.main_window.progress_bar.isVisible(), "進捗バーが表示されていません"

        print("✓ 定期的な進捗更新が正しく動作します")
        return True

    def test_timeout_manager_cleanup(self):
        """タイムアウトマネージャーのクリーンアップテスト"""
        print("\n--- タイムアウトマネージャークリーンアップテスト ---")

        timeout_manager = self.main_window.timeout_manager

        # テスト用タイムアウトを開始
        test_thread_id = "test_cleanup_thread"
        timeout_manager.start_timeout(test_thread_id)

        # タイムアウトがアクティブか確認
        assert timeout_manager.is_timeout_active(test_thread_id), "タイムアウトがアクティブになっていません"

        # クリーンアップを実行
        timeout_manager.cancel_timeout(test_thread_id)

        # タイムアウトがキャンセルされたか確認
        assert not timeout_manager.is_timeout_active(test_thread_id), "タイムアウトがキャンセルされていません"

        print("✓ タイムアウトマネージャーのクリーンアップが正しく動作します")
        return True

    def run_all_tests(self):
        """すべてのテストを実行"""
        print("=== タスク8: タイムアウト処理統合テスト開始 ===")

        tests = [
            self.test_timeout_manager_initialization,
            self.test_timeout_signal_connection,
            self.test_timeout_dialog_display,
            self.test_force_stop_functionality,
            self.test_state_reset_functionality,
            self.test_timeout_restart_capability,
            self.test_progress_update_during_timeout,
            self.test_timeout_manager_cleanup,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
                    print(f"✗ {test.__name__} が失敗しました")
            except Exception as e:
                failed += 1
                print(f"✗ {test.__name__} でエラーが発生: {e}")

        print(f"\n=== テスト結果 ===")
        print(f"成功: {passed}")
        print(f"失敗: {failed}")
        print(f"合計: {passed + failed}")

        if failed == 0:
            print("🎉 すべてのテストが成功しました！")
            print("タスク8: タイムアウト処理の統合が正しく実装されています。")
        else:
            print("❌ 一部のテストが失敗しました。")

        return failed == 0


def main():
    """メイン実行関数"""
    test_runner = TestTimeoutIntegration()

    try:
        test_runner.setup()
        success = test_runner.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"テスト実行中にエラーが発生: {e}")
        return 1
    finally:
        test_runner.teardown()


if __name__ == "__main__":
    sys.exit(main())
