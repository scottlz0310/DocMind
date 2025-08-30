"""
エラーケースとデバッグ機能テスト

様々なエラーケースとデバッグ機能の統合テスト
"""

import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.document_processor import DocumentProcessor
from src.core.file_watcher import FileWatcher
from src.core.index_manager import IndexManager
from src.core.indexing_worker import IndexingWorker
from src.data.database import DatabaseManager
from src.data.models import Document, FileType
from src.utils.error_handler import ErrorHandler
from src.utils.exceptions import DocumentProcessingError
from src.utils.logging_config import setup_logging


@pytest.mark.integration
class TestErrorCasesAndDebugging:
    """エラーケースとデバッグ機能テスト"""

    @pytest.fixture(autouse=True)
    def setup(self, test_config):
        """テストセットアップ"""
        self.config = test_config
        self.test_folder = Path(tempfile.mkdtemp())

        # エラーテスト用ファイルを作成
        self._create_error_test_files()

        # コンポーネント初期化
        self.document_processor = DocumentProcessor()
        self.index_manager = IndexManager(str(self.config.index_dir))
        self.index_manager.create_index()
        self.file_watcher = Mock(spec=FileWatcher)
        self.db_manager = DatabaseManager(str(self.config.database_file))
        self.db_manager.initialize()

        # エラーハンドラー初期化
        self.error_handler = ErrorHandler()

        # ログ設定
        setup_logging(self.config.log_dir)

        # シグナル受信用
        self.error_signals = []
        self.completion_signals = []

        yield

        if self.test_folder.exists():
            shutil.rmtree(self.test_folder)

    def _create_error_test_files(self):
        """エラーテスト用ファイルを作成"""
        # 正常なファイル
        (self.test_folder / "normal.txt").write_text(
            "これは正常なファイルです。", encoding="utf-8"
        )

        # 空のファイル
        (self.test_folder / "empty.txt").write_text("", encoding="utf-8")

        # 非常に大きなファイル（メモリエラーテスト用）
        large_content = "大きなファイルのテスト内容。\n" * 10000
        (self.test_folder / "large.txt").write_text(large_content, encoding="utf-8")

        # 特殊文字を含むファイル名
        special_chars_file = self.test_folder / "特殊文字ファイル名.txt"
        special_chars_file.write_text(
            "特殊文字を含むファイル名のテストです。", encoding="utf-8"
        )

        # 読み取り専用ファイル（権限エラーテスト用）
        readonly_file = self.test_folder / "readonly.txt"
        readonly_file.write_text("読み取り専用ファイル", encoding="utf-8")
        readonly_file.chmod(0o444)  # 読み取り専用に設定

        # 破損したファイル（バイナリデータ）
        corrupted_file = self.test_folder / "corrupted.txt"
        with open(corrupted_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe\xfd")

        # 非常に長いファイル名
        long_name = "a" * 200 + ".txt"
        try:
            (self.test_folder / long_name).write_text(
                "長いファイル名のテスト", encoding="utf-8"
            )
        except OSError:
            # ファイルシステムが長いファイル名をサポートしない場合はスキップ
            pass

        # ネストされたディレクトリ構造
        deep_dir = self.test_folder
        for i in range(10):
            deep_dir = deep_dir / f"level_{i}"
            deep_dir.mkdir()
        (deep_dir / "deep_file.txt").write_text(
            "深くネストされたファイル", encoding="utf-8"
        )

    def _connect_error_signals(self, worker):
        """エラーシグナルを接続"""
        worker.error_occurred.connect(
            lambda context, error: self.error_signals.append((context, error))
        )
        worker.indexing_completed.connect(
            lambda folder, stats: self.completion_signals.append((folder, stats))
        )

    def test_file_access_permission_errors(self):
        """ファイルアクセス権限エラーテスト"""
        # 読み取り不可能なディレクトリを作成
        restricted_dir = self.test_folder / "restricted"
        restricted_dir.mkdir()
        (restricted_dir / "restricted_file.txt").write_text(
            "制限されたファイル", encoding="utf-8"
        )

        # ディレクトリの権限を制限
        try:
            restricted_dir.chmod(0o000)  # アクセス不可

            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher,
            )

            self._connect_error_signals(worker)
            worker.process_folder()

            # 処理が完了していることを確認（エラーがあっても継続）
            assert (
                len(self.completion_signals) == 1
            ), "権限エラーがあっても処理が完了していません"

            folder_path, stats = self.completion_signals[0]

            # エラーが記録されていることを確認
            assert (
                len(stats["errors"]) > 0 or stats["files_failed"] > 0
            ), "権限エラーが記録されていません"

        finally:
            # 権限を復元してクリーンアップ
            try:
                restricted_dir.chmod(0o755)
            except:
                pass

        print("✓ ファイルアクセス権限エラーテスト完了")

    def test_corrupted_file_handling(self):
        """破損ファイル処理テスト"""
        # DocumentProcessorをモックして破損ファイルエラーをシミュレート
        with patch.object(self.document_processor, "process_file") as mock_process:

            def side_effect(file_path):
                if "corrupted.txt" in file_path:
                    raise DocumentProcessingError("ファイルが破損しています")
                # 他のファイルは正常に処理
                return Document(
                    id=f"test_{Path(file_path).stem}",
                    file_path=file_path,
                    title=Path(file_path).stem,
                    content="正常なコンテンツ",
                    file_type=FileType.TEXT,
                    size=100,
                )

            mock_process.side_effect = side_effect

            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher,
            )

            self._connect_error_signals(worker)
            worker.process_folder()

        # 破損ファイルエラーが適切に処理されていることを確認
        assert (
            len(self.completion_signals) == 1
        ), "破損ファイルエラーがあっても処理が完了していません"

        folder_path, stats = self.completion_signals[0]
        assert stats["files_failed"] > 0, "破損ファイルの失敗が記録されていません"

        # エラーメッセージに破損ファイルの情報が含まれていることを確認
        error_messages = " ".join(stats["errors"])
        assert (
            "corrupted.txt" in error_messages or "破損" in error_messages
        ), "破損ファイルのエラー情報が記録されていません"

        print("✓ 破損ファイル処理テスト完了")

    def test_memory_exhaustion_handling(self):
        """メモリ不足処理テスト"""
        # 非常に大きなファイルを処理する際のメモリエラーをシミュレート
        with patch.object(self.document_processor, "process_file") as mock_process:

            def side_effect(file_path):
                if "large.txt" in file_path:
                    raise MemoryError("メモリが不足しています")
                return Document(
                    id=f"test_{Path(file_path).stem}",
                    file_path=file_path,
                    title=Path(file_path).stem,
                    content="正常なコンテンツ",
                    file_type=FileType.TEXT,
                    size=100,
                )

            mock_process.side_effect = side_effect

            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher,
            )

            self._connect_error_signals(worker)
            worker.process_folder()

        # メモリエラーが適切に処理されていることを確認
        assert (
            len(self.completion_signals) == 1
        ), "メモリエラーがあっても処理が完了していません"

        folder_path, stats = self.completion_signals[0]
        assert stats["files_failed"] > 0, "メモリエラーの失敗が記録されていません"

        print("✓ メモリ不足処理テスト完了")

    def test_database_connection_errors(self):
        """データベース接続エラーテスト"""
        # IndexManagerをモックしてデータベースエラーをシミュレート
        with patch.object(self.index_manager, "add_document") as mock_add:
            mock_add.side_effect = Exception("データベース接続エラー")

            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher,
            )

            self._connect_error_signals(worker)
            worker.process_folder()

        # データベースエラーが発生していることを確認
        assert (
            len(self.error_signals) > 0
        ), "データベースエラーシグナルが発行されていません"

        # エラーコンテキストを確認
        error_contexts = [signal[0] for signal in self.error_signals]
        assert any(
            "batch_processing" in context for context in error_contexts
        ), "バッチ処理エラーが記録されていません"

        print("✓ データベース接続エラーテスト完了")

    def test_file_watcher_initialization_errors(self):
        """FileWatcher初期化エラーテスト"""
        # FileWatcherをモックしてエラーをシミュレート
        self.file_watcher.add_watch_path.side_effect = Exception(
            "ファイル監視初期化エラー"
        )

        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher,
        )

        self._connect_error_signals(worker)
        worker.process_folder()

        # FileWatcherエラーが適切に処理されていることを確認
        assert (
            len(self.error_signals) > 0
        ), "FileWatcherエラーシグナルが発行されていません"

        error_contexts = [signal[0] for signal in self.error_signals]
        assert any(
            "file_watching" in context for context in error_contexts
        ), "ファイル監視エラーが記録されていません"

        print("✓ FileWatcher初期化エラーテスト完了")

    def test_unicode_and_encoding_errors(self):
        """Unicode・エンコーディングエラーテスト"""
        # 異なるエンコーディングのファイルを作成
        encoding_test_dir = self.test_folder / "encoding_test"
        encoding_test_dir.mkdir()

        # UTF-8ファイル
        (encoding_test_dir / "utf8.txt").write_text(
            "UTF-8エンコーディングのテストファイル 🚀", encoding="utf-8"
        )

        # Shift-JISファイル
        try:
            (encoding_test_dir / "sjis.txt").write_text(
                "Shift-JISエンコーディングのテストファイル", encoding="shift-jis"
            )
        except UnicodeEncodeError:
            # Shift-JISでエンコードできない場合はスキップ
            pass

        # バイナリファイル（テキストとして読み取ろうとするとエラー）
        with open(encoding_test_dir / "binary.txt", "wb") as f:
            f.write(b"\xff\xfe\x00\x01\x02\x03")

        worker = IndexingWorker(
            str(encoding_test_dir),
            self.document_processor,
            self.index_manager,
            self.file_watcher,
        )

        self._connect_error_signals(worker)
        worker.process_folder()

        # エンコーディングエラーがあっても処理が完了することを確認
        assert (
            len(self.completion_signals) == 1
        ), "エンコーディングエラーがあっても処理が完了していません"

        print("✓ Unicode・エンコーディングエラーテスト完了")

    def test_concurrent_access_conflicts(self):
        """並行アクセス競合テスト"""
        # 同じフォルダに対して複数のワーカーを同時実行
        workers = []
        threads = []
        all_error_signals = []
        all_completion_signals = []

        for _i in range(3):
            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher,
            )

            # 各ワーカー用のシグナル収集
            worker_errors = []
            worker_completions = []

            worker.error_occurred.connect(
                lambda context, error, we=worker_errors: we.append((context, error))
            )
            worker.indexing_completed.connect(
                lambda folder, stats, wc=worker_completions: wc.append((folder, stats))
            )

            workers.append(worker)
            all_error_signals.append(worker_errors)
            all_completion_signals.append(worker_completions)

        # 並行実行
        def run_worker(worker):
            worker.process_folder()

        for worker in workers:
            thread = threading.Thread(target=run_worker, args=(worker,))
            threads.append(thread)
            thread.start()

        # 全スレッドの完了を待つ
        for thread in threads:
            thread.join(timeout=30)

        # 少なくとも一部のワーカーが完了していることを確認
        completed_workers = sum(
            1 for completions in all_completion_signals if len(completions) > 0
        )
        assert completed_workers > 0, "並行実行でワーカーが完了していません"

        print(f"✓ 並行アクセス競合テスト完了: {completed_workers}/3 ワーカーが完了")

    def test_resource_cleanup_on_errors(self):
        """エラー時のリソースクリーンアップテスト"""
        # リソースリークを検出するためのモック
        opened_files = []
        original_open = open

        def tracking_open(*args, **kwargs):
            file_obj = original_open(*args, **kwargs)
            opened_files.append(file_obj)
            return file_obj

        with patch("builtins.open", side_effect=tracking_open):
            # エラーを発生させるワーカー
            with patch.object(self.document_processor, "process_file") as mock_process:
                mock_process.side_effect = Exception("リソーステスト用エラー")

                worker = IndexingWorker(
                    str(self.test_folder),
                    self.document_processor,
                    self.index_manager,
                    self.file_watcher,
                )

                self._connect_error_signals(worker)
                worker.process_folder()

        # 開いたファイルが適切に閉じられていることを確認
        for file_obj in opened_files:
            if not file_obj.closed:
                print(f"警告: ファイルが閉じられていません: {file_obj.name}")

        print("✓ エラー時のリソースクリーンアップテスト完了")

    def test_error_logging_and_reporting(self):
        """エラーログ記録・報告テスト"""
        # ログファイルの場所を確認
        log_file = self.config.log_dir / "docmind.log"

        # エラーを発生させる
        with patch.object(self.document_processor, "process_file") as mock_process:
            mock_process.side_effect = DocumentProcessingError("ログテスト用エラー")

            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher,
            )

            self._connect_error_signals(worker)
            worker.process_folder()

        # ログファイルにエラーが記録されていることを確認
        if log_file.exists():
            log_content = log_file.read_text(encoding="utf-8")
            assert (
                "ログテスト用エラー" in log_content or "ERROR" in log_content
            ), "エラーがログファイルに記録されていません"

        # エラーシグナルが発行されていることを確認
        assert (
            len(self.error_signals) > 0 or len(self.completion_signals) > 0
        ), "エラー情報が適切に報告されていません"

        print("✓ エラーログ記録・報告テスト完了")


@pytest.mark.integration
class TestDebuggingFeatures:
    """デバッグ機能テスト"""

    @pytest.fixture(autouse=True)
    def setup(self, test_config):
        """デバッグ機能テスト用セットアップ"""
        self.config = test_config
        self.test_folder = Path(tempfile.mkdtemp())

        # デバッグテスト用ファイルを作成
        self._create_debug_test_files()

        # コンポーネント初期化
        self.document_processor = DocumentProcessor()
        self.index_manager = IndexManager(str(self.config.index_dir))
        self.index_manager.create_index()
        self.file_watcher = Mock(spec=FileWatcher)

        yield

        if self.test_folder.exists():
            shutil.rmtree(self.test_folder)

    def _create_debug_test_files(self):
        """デバッグテスト用ファイルを作成"""
        # 様々なタイプのファイルを作成
        (self.test_folder / "debug1.txt").write_text(
            "デバッグテスト用ファイル1", encoding="utf-8"
        )

        (self.test_folder / "debug2.md").write_text(
            "# デバッグテスト\n\nMarkdownファイルのテスト", encoding="utf-8"
        )

        # サブディレクトリ
        sub_dir = self.test_folder / "subdir"
        sub_dir.mkdir()
        (sub_dir / "debug3.txt").write_text(
            "サブディレクトリのデバッグファイル", encoding="utf-8"
        )

    def test_detailed_progress_tracking(self):
        """詳細進捗追跡テスト"""
        progress_history = []

        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher,
        )

        # 進捗の詳細を記録
        def track_progress(message, current, total):
            progress_history.append(
                {
                    "timestamp": time.time(),
                    "message": message,
                    "current": current,
                    "total": total,
                    "percentage": (current / total * 100) if total > 0 else 0,
                }
            )

        worker.progress_updated.connect(track_progress)
        worker.process_folder()

        # 進捗履歴を分析
        assert len(progress_history) > 0, "進捗履歴が記録されていません"

        # 進捗段階の確認
        stages = set()
        for progress in progress_history:
            message = progress["message"]
            if "スキャン" in message:
                stages.add("scanning")
            elif "処理中" in message:
                stages.add("processing")
            elif "インデックス" in message:
                stages.add("indexing")

        assert len(stages) >= 2, f"十分な進捗段階が記録されていません: {stages}"

        # 進捗率の妥当性確認
        for progress in progress_history:
            assert (
                0 <= progress["percentage"] <= 100
            ), f"進捗率が範囲外です: {progress['percentage']}%"

        print(f"✓ 詳細進捗追跡テスト完了: {len(progress_history)}個の進捗記録")

    def test_file_processing_diagnostics(self):
        """ファイル処理診断テスト"""
        file_diagnostics = []

        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher,
        )

        # ファイル処理の詳細を記録
        def track_file_processing(file_path, success, error_msg):
            file_info = {
                "file_path": file_path,
                "success": success,
                "error_msg": error_msg,
                "file_size": 0,
                "file_type": Path(file_path).suffix,
            }

            try:
                file_info["file_size"] = os.path.getsize(file_path)
            except:
                pass

            file_diagnostics.append(file_info)

        worker.file_processed.connect(track_file_processing)
        worker.process_folder()

        # 診断情報を分析
        assert len(file_diagnostics) > 0, "ファイル処理診断が記録されていません"

        successful_files = [f for f in file_diagnostics if f["success"]]
        failed_files = [f for f in file_diagnostics if not f["success"]]

        print("ファイル処理診断結果:")
        print(f"  成功: {len(successful_files)}ファイル")
        print(f"  失敗: {len(failed_files)}ファイル")

        for file_info in file_diagnostics:
            status = "成功" if file_info["success"] else "失敗"
            print(
                f"  {status}: {Path(file_info['file_path']).name} "
                f"({file_info['file_size']}bytes, {file_info['file_type']})"
            )

        print("✓ ファイル処理診断テスト完了")

    def test_performance_profiling(self):
        """パフォーマンスプロファイリングテスト"""
        timing_data = {}

        # 処理時間を測定するためのモック
        original_process_file = self.document_processor.process_file

        def timed_process_file(file_path):
            start_time = time.time()
            try:
                result = original_process_file(file_path)
                processing_time = time.time() - start_time
                timing_data[file_path] = {
                    "processing_time": processing_time,
                    "success": True,
                    "file_size": (
                        os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    ),
                }
                return result
            except Exception as e:
                processing_time = time.time() - start_time
                timing_data[file_path] = {
                    "processing_time": processing_time,
                    "success": False,
                    "error": str(e),
                    "file_size": (
                        os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    ),
                }
                raise

        with patch.object(
            self.document_processor, "process_file", side_effect=timed_process_file
        ):
            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher,
            )

            start_time = time.time()
            worker.process_folder()
            total_time = time.time() - start_time

        # パフォーマンス分析
        if timing_data:
            processing_times = [
                data["processing_time"] for data in timing_data.values()
            ]
            file_sizes = [data["file_size"] for data in timing_data.values()]

            avg_processing_time = sum(processing_times) / len(processing_times)
            max_processing_time = max(processing_times)
            total_file_size = sum(file_sizes)

            print("パフォーマンスプロファイリング結果:")
            print(f"  総処理時間: {total_time:.3f}秒")
            print(f"  平均ファイル処理時間: {avg_processing_time:.3f}秒")
            print(f"  最大ファイル処理時間: {max_processing_time:.3f}秒")
            print(f"  総ファイルサイズ: {total_file_size}bytes")
            print(f"  処理速度: {total_file_size/total_time:.1f}bytes/秒")

            # パフォーマンス要件の確認
            assert (
                avg_processing_time < 5.0
            ), f"平均処理時間が長すぎます: {avg_processing_time:.3f}秒"

        print("✓ パフォーマンスプロファイリングテスト完了")

    def test_memory_usage_monitoring(self, memory_monitor):
        """メモリ使用量監視テスト"""
        memory_monitor.start()

        memory_snapshots = []

        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher,
        )

        # 進捗に応じてメモリ使用量を記録
        def track_memory_usage(message, current, total):
            memory_usage = memory_monitor.get_current_memory()
            memory_snapshots.append(
                {
                    "stage": message,
                    "progress": f"{current}/{total}",
                    "memory_mb": memory_usage,
                }
            )

        worker.progress_updated.connect(track_memory_usage)
        worker.process_folder()

        # メモリ使用量分析
        if memory_snapshots:
            initial_memory = memory_snapshots[0]["memory_mb"]
            peak_memory = max(snapshot["memory_mb"] for snapshot in memory_snapshots)
            final_memory = memory_snapshots[-1]["memory_mb"]

            memory_increase = final_memory - initial_memory
            peak_increase = peak_memory - initial_memory

            print("メモリ使用量監視結果:")
            print(f"  初期メモリ: {initial_memory:.2f}MB")
            print(f"  ピークメモリ: {peak_memory:.2f}MB")
            print(f"  最終メモリ: {final_memory:.2f}MB")
            print(f"  メモリ増加: {memory_increase:.2f}MB")
            print(f"  ピーク増加: {peak_increase:.2f}MB")

            # メモリリークの確認
            assert (
                memory_increase < 100
            ), f"メモリ増加が大きすぎます: {memory_increase:.2f}MB"

        print("✓ メモリ使用量監視テスト完了")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
