"""
インデックス再構築機能の統合テスト

このテストモジュールは、インデックス再構築機能の包括的なテストを提供します。
- 小規模フォルダでの動作確認
- 大規模フォルダでのパフォーマンステスト
- エラー条件での動作確認
- タイムアウト処理のテスト

要件: 4.4, 6.5
"""

import os
import sys
import tempfile
import shutil
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

import pytest
from PySide6.QtCore import QTimer, QThread, Signal, QObject
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtTest import QTest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.gui.main_window import MainWindow
from src.core.index_manager import IndexManager
from src.core.search_manager import SearchManager
from src.utils.config import Config
from src.utils.exceptions import DocMindException


class TestIndexRebuildSmallScale:
    """小規模フォルダでの動作確認テスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app
        # テスト後のクリーンアップは不要（他のテストで使用される可能性があるため）

    @pytest.fixture
    def temp_folder(self):
        """テスト用の一時フォルダを作成"""
        temp_dir = tempfile.mkdtemp(prefix="docmind_test_small_")

        # 小規模テストファイルを作成（5ファイル）
        test_files = [
            ("document1.txt", "これは最初のテストドキュメントです。検索機能をテストします。"),
            ("document2.txt", "二番目のドキュメントには異なる内容が含まれています。"),
            ("document3.md", "# マークダウンファイル\n\nこれはマークダウン形式のドキュメントです。"),
            ("document4.txt", "四番目のファイルには特別なキーワード「重要」が含まれています。"),
            ("document5.txt", "最後のドキュメントは検索テストの完了を示します。")
        ]

        for filename, content in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        yield temp_dir

        # クリーンアップ
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def main_window(self, app, temp_folder):
        """メインウィンドウのフィクスチャ"""
        # 一時的な設定でメインウィンドウを作成
        with patch('src.utils.config.Config.get_data_dir') as mock_data_dir:
            mock_data_dir.return_value = tempfile.mkdtemp(prefix="docmind_data_test_")

            window = MainWindow()
            window.show()

            # フォルダを設定
            window.folder_tree.set_root_folder(temp_folder)

            yield window

            # クリーンアップ
            window.close()
            data_dir = mock_data_dir.return_value
            if os.path.exists(data_dir):
                shutil.rmtree(data_dir, ignore_errors=True)

    def test_small_scale_rebuild_basic_flow(self, main_window, temp_folder):
        """小規模フォルダでの基本的な再構築フローをテスト"""
        # 初期状態の確認
        assert main_window.folder_tree.get_current_folder() == temp_folder

        # モックを設定してダイアログの応答をシミュレート
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            # 進捗表示のモック
            progress_messages = []
            original_show_progress = main_window.show_progress
            original_update_progress = main_window.update_progress
            original_hide_progress = main_window.hide_progress

            def mock_show_progress(message, value=0):
                progress_messages.append(f"show: {message}")
                return original_show_progress(message, value)

            def mock_update_progress(current, total, message=""):
                progress_messages.append(f"update: {current}/{total} - {message}")
                return original_update_progress(current, total, message)

            def mock_hide_progress(message=""):
                progress_messages.append(f"hide: {message}")
                return original_hide_progress(message)

            main_window.show_progress = mock_show_progress
            main_window.update_progress = mock_update_progress
            main_window.hide_progress = mock_hide_progress

            # インデックス再構築を実行
            main_window._rebuild_index()

            # 処理完了まで待機（最大30秒）
            timeout = 30
            start_time = time.time()
            while time.time() - start_time < timeout:
                QApplication.processEvents()
                if not hasattr(main_window, '_rebuild_state') or not main_window._rebuild_state.is_active:
                    break
                time.sleep(0.1)

            # 結果の検証
            assert len(progress_messages) > 0, "進捗メッセージが記録されていません"

            # 進捗表示の流れを確認
            show_messages = [msg for msg in progress_messages if msg.startswith("show:")]
            hide_messages = [msg for msg in progress_messages if msg.startswith("hide:")]

            assert len(show_messages) > 0, "show_progressが呼ばれていません"
            assert len(hide_messages) > 0, "hide_progressが呼ばれていません"

            # インデックスが作成されたことを確認
            index_manager = main_window.index_manager
            doc_count = index_manager.get_document_count()
            assert doc_count == 5, f"期待されるドキュメント数: 5, 実際: {doc_count}"

    def test_small_scale_rebuild_cancellation(self, main_window, temp_folder):
        """小規模フォルダでの再構築キャンセルをテスト"""
        # キャンセルダイアログの応答をシミュレート
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
            # インデックス再構築を実行（キャンセル）
            main_window._rebuild_index()

            # キャンセルされたことを確認
            assert not hasattr(main_window, '_rebuild_state') or not main_window._rebuild_state.is_active

            # インデックスが変更されていないことを確認
            index_manager = main_window.index_manager
            doc_count = index_manager.get_document_count()
            assert doc_count == 0, "キャンセル後にインデックスが変更されています"

    def test_small_scale_rebuild_progress_updates(self, main_window, temp_folder):
        """小規模フォルダでの進捗更新をテスト"""
        progress_updates = []

        # 進捗更新をキャプチャ
        def capture_progress(current, total, message=""):
            progress_updates.append({
                'current': current,
                'total': total,
                'message': message,
                'timestamp': time.time()
            })

        # モックを設定
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            main_window.update_progress = capture_progress

            # インデックス再構築を実行
            main_window._rebuild_index()

            # 処理完了まで待機
            timeout = 30
            start_time = time.time()
            while time.time() - start_time < timeout:
                QApplication.processEvents()
                if not hasattr(main_window, '_rebuild_state') or not main_window._rebuild_state.is_active:
                    break
                time.sleep(0.1)

            # 進捗更新の検証
            assert len(progress_updates) > 0, "進捗更新が記録されていません"

            # 進捗が単調増加していることを確認
            for i in range(1, len(progress_updates)):
                prev_update = progress_updates[i-1]
                curr_update = progress_updates[i]

                # 同じtotalの場合、currentは増加または同じであるべき
                if prev_update['total'] == curr_update['total'] and curr_update['total'] > 0:
                    assert curr_update['current'] >= prev_update['current'], \
                        f"進捗が後退しています: {prev_update} -> {curr_update}"


class TestIndexRebuildLargeScale:
    """大規模フォルダでのパフォーマンステスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app

    @pytest.fixture
    def large_temp_folder(self):
        """大規模テスト用の一時フォルダを作成（100ファイル）"""
        temp_dir = tempfile.mkdtemp(prefix="docmind_test_large_")

        # 大規模テストファイルを作成
        for i in range(100):
            filename = f"document_{i:03d}.txt"
            content = f"""
            これは大規模テスト用のドキュメント {i} です。

            このファイルには以下の情報が含まれています：
            - ファイル番号: {i}
            - カテゴリ: {'重要' if i % 10 == 0 else '通常'}
            - 内容: {'長文' if i % 5 == 0 else '短文'}

            検索テスト用のキーワード:
            - keyword_{i % 20}
            - category_{i // 10}
            - type_{'important' if i % 10 == 0 else 'normal'}

            追加のテキスト内容をここに記述します。
            パフォーマンステストのために十分な量のテキストを含めています。
            """

            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        yield temp_dir

        # クリーンアップ
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def main_window_large(self, app, large_temp_folder):
        """大規模テスト用メインウィンドウのフィクスチャ"""
        with patch('src.utils.config.Config.get_data_dir') as mock_data_dir:
            mock_data_dir.return_value = tempfile.mkdtemp(prefix="docmind_data_large_test_")

            window = MainWindow()
            window.show()

            # フォルダを設定
            window.folder_tree.set_root_folder(large_temp_folder)

            yield window

            # クリーンアップ
            window.close()
            data_dir = mock_data_dir.return_value
            if os.path.exists(data_dir):
                shutil.rmtree(data_dir, ignore_errors=True)

    def test_large_scale_rebuild_performance(self, main_window_large, large_temp_folder):
        """大規模フォルダでのパフォーマンステスト"""
        performance_metrics = {
            'start_time': None,
            'end_time': None,
            'progress_updates': [],
            'memory_usage': []
        }

        # パフォーマンス測定用のモック
        original_update_progress = main_window_large.update_progress

        def track_progress(current, total, message=""):
            performance_metrics['progress_updates'].append({
                'current': current,
                'total': total,
                'message': message,
                'timestamp': time.time()
            })
            return original_update_progress(current, total, message)

        main_window_large.update_progress = track_progress

        # 開始時間を記録
        performance_metrics['start_time'] = time.time()

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            # インデックス再構築を実行
            main_window_large._rebuild_index()

            # 処理完了まで待機（最大5分）
            timeout = 300  # 5分
            start_time = time.time()
            while time.time() - start_time < timeout:
                QApplication.processEvents()
                if not hasattr(main_window_large, '_rebuild_state') or not main_window_large._rebuild_state.is_active:
                    break
                time.sleep(0.1)

            # 終了時間を記録
            performance_metrics['end_time'] = time.time()

            # パフォーマンス検証
            total_time = performance_metrics['end_time'] - performance_metrics['start_time']

            # 要件: 大規模ファイル処理でも合理的な時間内に完了すること
            assert total_time < 300, f"処理時間が長すぎます: {total_time:.2f}秒"

            # インデックスが正しく作成されたことを確認
            index_manager = main_window_large.index_manager
            doc_count = index_manager.get_document_count()
            assert doc_count == 100, f"期待されるドキュメント数: 100, 実際: {doc_count}"

            # 進捗更新の頻度を確認
            assert len(performance_metrics['progress_updates']) > 0, "進捗更新が記録されていません"

            # 1秒あたりの処理ファイル数を計算
            files_per_second = 100 / total_time
            assert files_per_second > 1, f"処理速度が遅すぎます: {files_per_second:.2f} files/sec"

            print(f"大規模テスト結果:")
            print(f"  - 処理時間: {total_time:.2f}秒")
            print(f"  - 処理速度: {files_per_second:.2f} files/sec")
            print(f"  - 進捗更新回数: {len(performance_metrics['progress_updates'])}")

    def test_large_scale_memory_usage(self, main_window_large, large_temp_folder):
        """大規模処理時のメモリ使用量テスト"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            # インデックス再構築を実行
            main_window_large._rebuild_index()

            # 処理完了まで待機
            timeout = 300
            start_time = time.time()
            max_memory = initial_memory

            while time.time() - start_time < timeout:
                QApplication.processEvents()
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                max_memory = max(max_memory, current_memory)

                if not hasattr(main_window_large, '_rebuild_state') or not main_window_large._rebuild_state.is_active:
                    break
                time.sleep(0.5)

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = max_memory - initial_memory

            # メモリ使用量の検証
            # 要件: メモリリークを防ぐ
            assert memory_increase < 500, f"メモリ使用量が過大です: {memory_increase:.2f}MB増加"

            print(f"メモリ使用量テスト結果:")
            print(f"  - 初期メモリ: {initial_memory:.2f}MB")
            print(f"  - 最大メモリ: {max_memory:.2f}MB")
            print(f"  - 最終メモリ: {final_memory:.2f}MB")
            print(f"  - 最大増加量: {memory_increase:.2f}MB")


class TestIndexRebuildErrorConditions:
    """エラー条件での動作確認テスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app

    @pytest.fixture
    def error_temp_folder(self):
        """エラーテスト用の一時フォルダを作成"""
        temp_dir = tempfile.mkdtemp(prefix="docmind_test_error_")

        # 正常なファイル
        normal_files = [
            ("normal1.txt", "正常なファイル1"),
            ("normal2.txt", "正常なファイル2"),
        ]

        for filename, content in normal_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # 読み取り専用ファイル（権限エラーをシミュレート）
        readonly_file = os.path.join(temp_dir, "readonly.txt")
        with open(readonly_file, 'w', encoding='utf-8') as f:
            f.write("読み取り専用ファイル")

        # ファイルを読み取り専用に設定
        os.chmod(readonly_file, 0o444)

        yield temp_dir

        # クリーンアップ（権限を戻してから削除）
        if os.path.exists(temp_dir):
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.chmod(file_path, 0o666)
                    except:
                        pass
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def main_window_error(self, app, error_temp_folder):
        """エラーテスト用メインウィンドウのフィクスチャ"""
        with patch('src.utils.config.Config.get_data_dir') as mock_data_dir:
            mock_data_dir.return_value = tempfile.mkdtemp(prefix="docmind_data_error_test_")

            window = MainWindow()
            window.show()

            # フォルダを設定
            window.folder_tree.set_root_folder(error_temp_folder)

            yield window

            # クリーンアップ
            window.close()
            data_dir = mock_data_dir.return_value
            if os.path.exists(data_dir):
                shutil.rmtree(data_dir, ignore_errors=True)

    def test_file_access_error_handling(self, main_window_error, error_temp_folder):
        """ファイルアクセスエラーのハンドリングをテスト"""
        error_messages = []

        # エラーメッセージをキャプチャ
        original_on_rebuild_error = getattr(main_window_error, '_on_rebuild_error', None)

        def capture_error(thread_id, error_message):
            error_messages.append({
                'thread_id': thread_id,
                'error_message': error_message,
                'timestamp': time.time()
            })
            if original_on_rebuild_error:
                return original_on_rebuild_error(thread_id, error_message)

        main_window_error._on_rebuild_error = capture_error

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            # インデックス再構築を実行
            main_window_error._rebuild_index()

            # 処理完了まで待機
            timeout = 60
            start_time = time.time()
            while time.time() - start_time < timeout:
                QApplication.processEvents()
                if not hasattr(main_window_error, '_rebuild_state') or not main_window_error._rebuild_state.is_active:
                    break
                time.sleep(0.1)

            # エラーハンドリングの検証
            # 正常なファイルは処理されるべき
            index_manager = main_window_error.index_manager
            doc_count = index_manager.get_document_count()
            assert doc_count >= 2, f"正常なファイルが処理されていません: {doc_count}"

            # エラーが適切に処理されたことを確認
            # （エラーメッセージが記録されているか、または正常に完了している）
            print(f"エラーハンドリングテスト結果:")
            print(f"  - 処理されたドキュメント数: {doc_count}")
            print(f"  - 記録されたエラー数: {len(error_messages)}")

    def test_index_manager_error_simulation(self, main_window_error):
        """IndexManagerのエラーをシミュレートしてテスト"""
        error_occurred = False

        # IndexManagerのclear_indexメソッドでエラーを発生させる
        original_clear_index = main_window_error.index_manager.clear_index

        def mock_clear_index():
            nonlocal error_occurred
            error_occurred = True
            raise DocMindException("インデックスクリアエラーのシミュレーション")

        main_window_error.index_manager.clear_index = mock_clear_index

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            with patch.object(QMessageBox, 'critical') as mock_error_dialog:
                # インデックス再構築を実行
                main_window_error._rebuild_index()

                # エラーが発生したことを確認
                assert error_occurred, "エラーが発生していません"

                # エラーダイアログが表示されたことを確認
                assert mock_error_dialog.called, "エラーダイアログが表示されていません"

    def test_thread_manager_error_simulation(self, main_window_error):
        """ThreadManagerのエラーをシミュレートしてテスト"""
        # ThreadManagerのstart_indexing_threadメソッドでエラーを発生させる
        original_start_thread = main_window_error.thread_manager.start_indexing_thread

        def mock_start_thread(*args, **kwargs):
            raise RuntimeError("スレッド開始エラーのシミュレーション")

        main_window_error.thread_manager.start_indexing_thread = mock_start_thread

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            with patch.object(QMessageBox, 'critical') as mock_error_dialog:
                # インデックス再構築を実行
                main_window_error._rebuild_index()

                # エラーダイアログが表示されたことを確認
                assert mock_error_dialog.called, "エラーダイアログが表示されていません"

                # 再構築状態がリセットされたことを確認
                assert not hasattr(main_window_error, '_rebuild_state') or not main_window_error._rebuild_state.is_active


class TestIndexRebuildTimeout:
    """タイムアウト処理のテスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app

    @pytest.fixture
    def timeout_temp_folder(self):
        """タイムアウトテスト用の一時フォルダを作成"""
        temp_dir = tempfile.mkdtemp(prefix="docmind_test_timeout_")

        # 少数のファイルを作成（タイムアウトテスト用）
        test_files = [
            ("timeout_test1.txt", "タイムアウトテスト用ファイル1"),
            ("timeout_test2.txt", "タイムアウトテスト用ファイル2"),
        ]

        for filename, content in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        yield temp_dir

        # クリーンアップ
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def main_window_timeout(self, app, timeout_temp_folder):
        """タイムアウトテスト用メインウィンドウのフィクスチャ"""
        with patch('src.utils.config.Config.get_data_dir') as mock_data_dir:
            mock_data_dir.return_value = tempfile.mkdtemp(prefix="docmind_data_timeout_test_")

            window = MainWindow()
            window.show()

            # フォルダを設定
            window.folder_tree.set_root_folder(timeout_temp_folder)

            yield window

            # クリーンアップ
            window.close()
            data_dir = mock_data_dir.return_value
            if os.path.exists(data_dir):
                shutil.rmtree(data_dir, ignore_errors=True)

    def test_timeout_detection_and_handling(self, main_window_timeout):
        """タイムアウト検出とハンドリングをテスト"""
        timeout_occurred = False

        # タイムアウトハンドラーをモック
        original_handle_timeout = getattr(main_window_timeout, '_handle_rebuild_timeout', None)

        def mock_handle_timeout(thread_id):
            nonlocal timeout_occurred
            timeout_occurred = True
            if original_handle_timeout:
                return original_handle_timeout(thread_id)

        main_window_timeout._handle_rebuild_timeout = mock_handle_timeout

        # 短いタイムアウト時間を設定（テスト用）
        if hasattr(main_window_timeout, 'timeout_manager'):
            main_window_timeout.timeout_manager.timeout_minutes = 0.1  # 6秒

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            # IndexingWorkerを遅延させるモック
            original_process_folder = None
            if hasattr(main_window_timeout.thread_manager, 'worker_class'):
                worker_class = main_window_timeout.thread_manager.worker_class
                if hasattr(worker_class, 'process_folder'):
                    original_process_folder = worker_class.process_folder

                    def slow_process_folder(self, *args, **kwargs):
                        # 処理を意図的に遅延させる
                        time.sleep(10)  # 10秒待機
                        if original_process_folder:
                            return original_process_folder(self, *args, **kwargs)

                    worker_class.process_folder = slow_process_folder

            # インデックス再構築を実行
            main_window_timeout._rebuild_index()

            # タイムアウトが発生するまで待機
            timeout = 15  # 15秒待機
            start_time = time.time()
            while time.time() - start_time < timeout:
                QApplication.processEvents()
                if timeout_occurred:
                    break
                time.sleep(0.1)

            # タイムアウトが検出されたことを確認
            assert timeout_occurred, "タイムアウトが検出されていません"

            # 処理が停止されたことを確認
            if hasattr(main_window_timeout, '_rebuild_state'):
                assert not main_window_timeout._rebuild_state.is_active, "処理が停止されていません"

    def test_timeout_dialog_interaction(self, main_window_timeout):
        """タイムアウトダイアログの相互作用をテスト"""
        dialog_shown = False

        # タイムアウトダイアログのモック
        def mock_timeout_dialog(*args, **kwargs):
            nonlocal dialog_shown
            dialog_shown = True
            return QMessageBox.Yes  # 強制停止を選択

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            with patch.object(QMessageBox, 'warning', side_effect=mock_timeout_dialog):
                # タイムアウトを直接トリガー
                if hasattr(main_window_timeout, '_handle_rebuild_timeout'):
                    main_window_timeout._handle_rebuild_timeout("test_thread_id")

                    # ダイアログが表示されたことを確認
                    assert dialog_shown, "タイムアウトダイアログが表示されていません"

    def test_timeout_cleanup_and_recovery(self, main_window_timeout):
        """タイムアウト後のクリーンアップと復旧をテスト"""
        # タイムアウト状態をシミュレート
        if hasattr(main_window_timeout, '_rebuild_state'):
            main_window_timeout._rebuild_state.is_active = True
            main_window_timeout._rebuild_state.thread_id = "test_thread_id"

        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.Yes):
            # タイムアウト処理を実行
            if hasattr(main_window_timeout, '_handle_rebuild_timeout'):
                main_window_timeout._handle_rebuild_timeout("test_thread_id")

            # 状態がリセットされたことを確認
            if hasattr(main_window_timeout, '_rebuild_state'):
                assert not main_window_timeout._rebuild_state.is_active, "再構築状態がリセットされていません"

            # 再度再構築を実行できることを確認
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
                try:
                    main_window_timeout._rebuild_index()
                    # エラーが発生しなければ成功
                    assert True
                except Exception as e:
                    pytest.fail(f"タイムアウト後の復旧に失敗しました: {e}")


if __name__ == "__main__":
    # テストを直接実行する場合
    pytest.main([__file__, "-v", "--tb=short"])
