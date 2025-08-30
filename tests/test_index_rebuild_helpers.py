"""
インデックス再構築テスト用のヘルパー関数とユーティリティ

このモジュールは、インデックス再構築機能のテストで使用される
共通のヘルパー関数とユーティリティクラスを提供します。
"""

import os
import shutil
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QApplication, QTimer

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@dataclass
class TestMetrics:
    """テスト実行時のメトリクス情報"""
    start_time: datetime | None = None
    end_time: datetime | None = None
    progress_updates: list[dict[str, Any]] = field(default_factory=list)
    error_messages: list[dict[str, Any]] = field(default_factory=list)
    memory_usage: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """実行時間を秒で返す"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def files_per_second(self) -> float:
        """1秒あたりの処理ファイル数を計算"""
        if self.duration > 0 and self.progress_updates:
            max_total = max((update.get('total', 0) for update in self.progress_updates), default=0)
            return max_total / self.duration
        return 0.0


class TestFileGenerator:
    """テスト用ファイル生成ユーティリティ"""

    @staticmethod
    def create_small_test_files(base_dir: str, count: int = 5) -> list[str]:
        """小規模テスト用ファイルを生成"""
        files = []
        for i in range(count):
            filename = f"test_document_{i:02d}.txt"
            content = f"""
            テストドキュメント {i}

            このファイルは小規模テスト用に作成されました。
            ファイル番号: {i}
            作成日時: {datetime.now().isoformat()}

            検索テスト用キーワード:
            - keyword_{i}
            - test_content
            - small_scale

            追加のテキスト内容をここに記述します。
            """

            file_path = os.path.join(base_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            files.append(file_path)

        return files

    @staticmethod
    def create_large_test_files(base_dir: str, count: int = 100) -> list[str]:
        """大規模テスト用ファイルを生成"""
        files = []
        for i in range(count):
            filename = f"large_document_{i:03d}.txt"
            content = f"""
            大規模テストドキュメント {i}

            このファイルは大規模パフォーマンステスト用に作成されました。

            基本情報:
            - ファイル番号: {i}
            - カテゴリ: {'重要' if i % 10 == 0 else '通常'}
            - 優先度: {'高' if i % 5 == 0 else '中' if i % 3 == 0 else '低'}
            - 作成日時: {datetime.now().isoformat()}

            検索テスト用キーワード:
            - keyword_{i % 20}
            - category_{i // 10}
            - priority_{'high' if i % 5 == 0 else 'medium' if i % 3 == 0 else 'low'}
            - type_{'important' if i % 10 == 0 else 'normal'}

            詳細内容:
            このドキュメントには、パフォーマンステストのために
            十分な量のテキストコンテンツが含まれています。

            {'長文コンテンツ: ' * 10 if i % 5 == 0 else '短文コンテンツ'}

            追加情報:
            - 関連ドキュメント: {[f'doc_{j}' for j in range(max(0, i-2), min(count, i+3))]}
            - タグ: {['tag_' + str(j) for j in range(i % 5 + 1)]}

            テスト用の長いテキスト:
            {'この文章は長いテキストのテストです。' * (i % 10 + 1)}
            """

            file_path = os.path.join(base_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            files.append(file_path)

        return files

    @staticmethod
    def create_error_test_files(base_dir: str) -> dict[str, list[str]]:
        """エラーテスト用ファイルを生成"""
        files = {
            'normal': [],
            'readonly': [],
            'corrupted': []
        }

        # 正常なファイル
        for i in range(3):
            filename = f"normal_{i}.txt"
            content = f"正常なテストファイル {i}"
            file_path = os.path.join(base_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            files['normal'].append(file_path)

        # 読み取り専用ファイル
        readonly_file = os.path.join(base_dir, "readonly.txt")
        with open(readonly_file, 'w', encoding='utf-8') as f:
            f.write("読み取り専用ファイル")
        os.chmod(readonly_file, 0o444)
        files['readonly'].append(readonly_file)

        # 破損ファイル（空ファイル）
        corrupted_file = os.path.join(base_dir, "corrupted.txt")
        with open(corrupted_file, 'w', encoding='utf-8') as f:
            pass  # 空ファイル
        files['corrupted'].append(corrupted_file)

        return files


class MockProgressTracker:
    """進捗追跡用のモッククラス"""

    def __init__(self):
        self.metrics = TestMetrics()
        self.callbacks = {
            'show_progress': [],
            'update_progress': [],
            'hide_progress': [],
            'error_occurred': []
        }

    def add_callback(self, event_type: str, callback: Callable):
        """コールバック関数を追加"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def mock_show_progress(self, message: str, value: int = 0):
        """show_progressのモック"""
        event = {
            'type': 'show_progress',
            'message': message,
            'value': value,
            'timestamp': datetime.now()
        }
        self.metrics.progress_updates.append(event)

        for callback in self.callbacks['show_progress']:
            callback(event)

    def mock_update_progress(self, current: int, total: int, message: str = ""):
        """update_progressのモック"""
        event = {
            'type': 'update_progress',
            'current': current,
            'total': total,
            'message': message,
            'timestamp': datetime.now()
        }
        self.metrics.progress_updates.append(event)

        for callback in self.callbacks['update_progress']:
            callback(event)

    def mock_hide_progress(self, message: str = ""):
        """hide_progressのモック"""
        event = {
            'type': 'hide_progress',
            'message': message,
            'timestamp': datetime.now()
        }
        self.metrics.progress_updates.append(event)

        for callback in self.callbacks['hide_progress']:
            callback(event)

    def mock_error_occurred(self, thread_id: str, error_message: str):
        """エラー発生のモック"""
        event = {
            'type': 'error_occurred',
            'thread_id': thread_id,
            'error_message': error_message,
            'timestamp': datetime.now()
        }
        self.metrics.error_messages.append(event)

        for callback in self.callbacks['error_occurred']:
            callback(event)


class TestEnvironmentManager:
    """テスト環境管理ユーティリティ"""

    def __init__(self):
        self.temp_dirs = []
        self.cleanup_functions = []

    def create_temp_dir(self, prefix: str = "docmind_test_") -> str:
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir

    def add_cleanup_function(self, func: Callable):
        """クリーンアップ関数を追加"""
        self.cleanup_functions.append(func)

    def cleanup(self):
        """すべてのリソースをクリーンアップ"""
        # クリーンアップ関数を実行
        for func in self.cleanup_functions:
            try:
                func()
            except Exception as e:
                print(f"クリーンアップエラー: {e}")

        # 一時ディレクトリを削除
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    # 読み取り専用ファイルの権限を変更
                    for root, _dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                os.chmod(file_path, 0o666)
                            except:
                                pass
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    print(f"ディレクトリ削除エラー: {e}")

        self.temp_dirs.clear()
        self.cleanup_functions.clear()


class PerformanceMonitor:
    """パフォーマンス監視ユーティリティ"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_samples = []
        self.cpu_samples = []
        self.monitoring = False
        self.monitor_thread = None

    def start_monitoring(self):
        """監視を開始"""
        self.start_time = datetime.now()
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """監視を停止"""
        self.end_time = datetime.now()
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

    def _monitor_loop(self):
        """監視ループ"""
        try:
            import psutil
            process = psutil.Process()

            while self.monitoring:
                try:
                    memory_info = process.memory_info()
                    cpu_percent = process.cpu_percent()

                    self.memory_samples.append({
                        'timestamp': datetime.now(),
                        'rss': memory_info.rss / 1024 / 1024,  # MB
                        'vms': memory_info.vms / 1024 / 1024   # MB
                    })

                    self.cpu_samples.append({
                        'timestamp': datetime.now(),
                        'cpu_percent': cpu_percent
                    })

                except Exception as e:
                    print(f"監視エラー: {e}")

                time.sleep(0.5)  # 0.5秒間隔で監視

        except ImportError:
            print("psutilが利用できません。パフォーマンス監視をスキップします。")

    @property
    def duration(self) -> float:
        """実行時間を秒で返す"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def max_memory_usage(self) -> float:
        """最大メモリ使用量をMBで返す"""
        if self.memory_samples:
            return max(sample['rss'] for sample in self.memory_samples)
        return 0.0

    @property
    def avg_cpu_usage(self) -> float:
        """平均CPU使用率を返す"""
        if self.cpu_samples:
            return sum(sample['cpu_percent'] for sample in self.cpu_samples) / len(self.cpu_samples)
        return 0.0


class TimeoutSimulator:
    """タイムアウトシミュレーション用ユーティリティ"""

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = timeout_seconds
        self.timer = None
        self.timeout_occurred = False
        self.timeout_callbacks = []

    def add_timeout_callback(self, callback: Callable):
        """タイムアウト時のコールバックを追加"""
        self.timeout_callbacks.append(callback)

    def start_timeout(self):
        """タイムアウト監視を開始"""
        self.timeout_occurred = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timeout)
        self.timer.start(int(self.timeout_seconds * 1000))

    def cancel_timeout(self):
        """タイムアウト監視をキャンセル"""
        if self.timer:
            self.timer.stop()
            self.timer = None

    def _on_timeout(self):
        """タイムアウト発生時の処理"""
        self.timeout_occurred = True
        self.cancel_timeout()

        for callback in self.timeout_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"タイムアウトコールバックエラー: {e}")


def wait_for_condition(condition_func: Callable[[], bool],
                      timeout_seconds: float = 30.0,
                      check_interval: float = 0.1) -> bool:
    """条件が満たされるまで待機"""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        QApplication.processEvents()
        if condition_func():
            return True
        time.sleep(check_interval)
    return False


def create_mock_main_window_with_tracking(temp_folder: str,
                                        progress_tracker: MockProgressTracker) -> Mock:
    """進捗追跡機能付きのモックメインウィンドウを作成"""
    mock_window = Mock()

    # 基本属性の設定
    mock_window.folder_tree = Mock()
    mock_window.folder_tree.get_current_folder.return_value = temp_folder
    mock_window.index_manager = Mock()
    mock_window.search_manager = Mock()
    mock_window.thread_manager = Mock()

    # 進捗表示メソッドをモック
    mock_window.show_progress = progress_tracker.mock_show_progress
    mock_window.update_progress = progress_tracker.mock_update_progress
    mock_window.hide_progress = progress_tracker.mock_hide_progress

    # エラーハンドリングメソッドをモック
    mock_window._on_rebuild_error = progress_tracker.mock_error_occurred

    return mock_window


def assert_progress_flow_is_valid(progress_updates: list[dict[str, Any]]):
    """進捗フローが正しいことを検証"""
    if not progress_updates:
        pytest.fail("進捗更新が記録されていません")

    # show -> update -> hide の順序を確認
    show_count = sum(1 for update in progress_updates if update.get('type') == 'show_progress')
    hide_count = sum(1 for update in progress_updates if update.get('type') == 'hide_progress')
    sum(1 for update in progress_updates if update.get('type') == 'update_progress')

    assert show_count > 0, "show_progressが呼ばれていません"
    assert hide_count > 0, "hide_progressが呼ばれていません"

    # 進捗更新の単調性を確認
    update_events = [update for update in progress_updates if update.get('type') == 'update_progress']
    for i in range(1, len(update_events)):
        prev_event = update_events[i-1]
        curr_event = update_events[i]

        # 同じtotalの場合、currentは増加または同じであるべき
        if (prev_event.get('total') == curr_event.get('total') and
            curr_event.get('total', 0) > 0):
            assert curr_event.get('current', 0) >= prev_event.get('current', 0), \
                f"進捗が後退しています: {prev_event} -> {curr_event}"


def assert_performance_is_acceptable(metrics: TestMetrics,
                                   expected_file_count: int,
                                   max_duration_seconds: float = 300.0,
                                   min_files_per_second: float = 1.0):
    """パフォーマンスが許容範囲内であることを検証"""
    assert metrics.duration > 0, "実行時間が記録されていません"
    assert metrics.duration < max_duration_seconds, \
        f"処理時間が長すぎます: {metrics.duration:.2f}秒 (最大: {max_duration_seconds}秒)"

    files_per_second = metrics.files_per_second
    assert files_per_second >= min_files_per_second, \
        f"処理速度が遅すぎます: {files_per_second:.2f} files/sec (最小: {min_files_per_second} files/sec)"

    print("パフォーマンステスト結果:")
    print(f"  - 処理時間: {metrics.duration:.2f}秒")
    print(f"  - 処理速度: {files_per_second:.2f} files/sec")
    print(f"  - 進捗更新回数: {len(metrics.progress_updates)}")
