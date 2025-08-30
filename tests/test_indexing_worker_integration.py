"""
IndexingWorker統合テスト

実際のインデックス処理ワーカーのエンドツーエンドテストを実装
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
from src.core.indexing_worker import (
    IndexingWorker,
)
from src.data.models import Document, FileType
from src.utils.exceptions import DocumentProcessingError


@pytest.mark.integration
class TestIndexingWorkerIntegration:
    """IndexingWorker統合テスト"""

    @pytest.fixture(autouse=True)
    def setup(self, test_config):
        """テストセットアップ"""
        self.config = test_config

        # テスト用の一時ディレクトリを作成
        self.test_folder = Path(tempfile.mkdtemp())

        # テスト用ファイルを作成
        self._create_test_files()

        # コンポーネントを初期化
        self.document_processor = DocumentProcessor()
        self.index_manager = IndexManager(str(self.config.index_dir))
        self.index_manager.create_index()
        self.file_watcher = Mock(spec=FileWatcher)

        # シグナル受信用のモック
        self.progress_signals = []
        self.file_processed_signals = []
        self.completion_signals = []
        self.error_signals = []

        yield

        # クリーンアップ
        if self.test_folder.exists():
            shutil.rmtree(self.test_folder)

    def _create_test_files(self):
        """テスト用ファイルを作成"""
        # テキストファイル
        (self.test_folder / "test1.txt").write_text(
            "これは最初のテストドキュメントです。\n"
            "検索テスト用のキーワードを含んでいます。",
            encoding='utf-8'
        )

        (self.test_folder / "test2.txt").write_text(
            "これは2番目のテストドキュメントです。\n"
            "別の検索キーワードも含んでいます。",
            encoding='utf-8'
        )

        # Markdownファイル
        (self.test_folder / "readme.md").write_text(
            "# テストドキュメント\n\n"
            "これはMarkdown形式のテストファイルです。\n"
            "- リスト項目1\n"
            "- リスト項目2\n",
            encoding='utf-8'
        )

        # サブディレクトリとファイル
        sub_dir = self.test_folder / "subdir"
        sub_dir.mkdir()
        (sub_dir / "nested.txt").write_text(
            "これはサブディレクトリ内のファイルです。\n"
            "ネストされたファイルのテストです。",
            encoding='utf-8'
        )

        # サポートされていないファイル
        (self.test_folder / "unsupported.xyz").write_text(
            "これはサポートされていない形式のファイルです。",
            encoding='utf-8'
        )

        # 空のファイル
        (self.test_folder / "empty.txt").write_text("", encoding='utf-8')

    def _connect_signals(self, worker):
        """ワーカーのシグナルを接続"""
        worker.progress_updated.connect(
            lambda msg, current, total: self.progress_signals.append((msg, current, total))
        )
        worker.file_processed.connect(
            lambda path, success, error: self.file_processed_signals.append((path, success, error))
        )
        worker.indexing_completed.connect(
            lambda folder, stats: self.completion_signals.append((folder, stats))
        )
        worker.error_occurred.connect(
            lambda context, error: self.error_signals.append((context, error))
        )

    def test_complete_indexing_workflow(self):
        """完全なインデックス処理ワークフローテスト"""
        # ワーカーを作成
        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )

        # シグナルを接続
        self._connect_signals(worker)

        # 処理を実行
        worker.process_folder()

        # 結果を検証
        assert len(self.completion_signals) == 1, "完了シグナルが発行されていません"

        folder_path, stats = self.completion_signals[0]
        assert folder_path == str(self.test_folder)
        assert isinstance(stats, dict)

        # 統計情報を検証
        assert stats['total_files_found'] >= 4  # txt, md, nested.txt, empty.txt
        assert stats['files_processed'] >= 3   # empty.txtは内容がないため除外される可能性
        assert stats['documents_added'] >= 3
        assert stats['processing_time'] > 0

        # 進捗シグナルが発行されていることを確認
        assert len(self.progress_signals) > 0, "進捗シグナルが発行されていません"

        # ファイル処理シグナルが発行されていることを確認
        assert len(self.file_processed_signals) > 0, "ファイル処理シグナルが発行されていません"

        # FileWatcherが開始されていることを確認
        self.file_watcher.add_watch_path.assert_called_once_with(str(self.test_folder))

        print(f"✓ 完全なインデックス処理ワークフロー完了: {stats}")

    def test_progress_reporting(self):
        """進捗報告機能テスト"""
        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )

        self._connect_signals(worker)
        worker.process_folder()

        # 進捗シグナルの内容を検証
        scanning_signals = [s for s in self.progress_signals if "スキャン" in s[0]]
        processing_signals = [s for s in self.progress_signals if "処理中" in s[0]]
        [s for s in self.progress_signals if "インデックス" in s[0]]

        assert len(scanning_signals) > 0, "スキャン進捗が報告されていません"
        assert len(processing_signals) > 0, "処理進捗が報告されていません"

        # 進捗率が適切に計算されていることを確認
        for _msg, current, total in self.progress_signals:
            if total > 0:
                assert 0 <= current <= total, f"進捗値が不正: {current}/{total}"

        print("✓ 進捗報告機能テスト完了")

    def test_error_handling_during_processing(self):
        """処理中のエラーハンドリングテスト"""
        # エラーを発生させるファイルを作成
        error_file = self.test_folder / "error_file.txt"
        error_file.write_text("エラーテスト用ファイル", encoding='utf-8')

        # DocumentProcessorをモックしてエラーを発生させる
        with patch.object(self.document_processor, 'process_file') as mock_process:
            def side_effect(file_path):
                if "error_file.txt" in file_path:
                    raise DocumentProcessingError("テスト用エラー")
                # 他のファイルは正常に処理
                return Document(
                    id=f"test_{Path(file_path).stem}",
                    file_path=file_path,
                    title=Path(file_path).stem,
                    content=Path(file_path).read_text(encoding='utf-8'),
                    file_type=FileType.TEXT,
                    size=Path(file_path).stat().st_size
                )

            mock_process.side_effect = side_effect

            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher
            )

            self._connect_signals(worker)
            worker.process_folder()

        # エラーが適切に処理されていることを確認
        assert len(self.completion_signals) == 1, "エラーがあっても処理が完了していません"

        folder_path, stats = self.completion_signals[0]
        assert stats['files_failed'] > 0, "失敗ファイル数が記録されていません"
        assert len(stats['errors']) > 0, "エラー情報が記録されていません"

        # エラーファイルの処理失敗シグナルを確認
        failed_signals = [s for s in self.file_processed_signals if not s[1]]
        assert len(failed_signals) > 0, "失敗シグナルが発行されていません"

        print("✓ エラーハンドリングテスト完了")

    def test_cancellation_functionality(self):
        """キャンセル機能テスト"""
        # 大量のファイルを作成（処理時間を延ばすため）
        large_folder = self.test_folder / "large_test"
        large_folder.mkdir()

        for i in range(20):
            (large_folder / f"file_{i:03d}.txt").write_text(
                f"これは大量ファイルテスト用のドキュメント {i} です。\n" * 10,
                encoding='utf-8'
            )

        worker = IndexingWorker(
            str(large_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )

        self._connect_signals(worker)

        # 別スレッドで処理を開始
        def run_processing():
            worker.process_folder()

        thread = threading.Thread(target=run_processing)
        thread.start()

        # 少し待ってからキャンセル
        time.sleep(0.1)
        worker.stop()

        # スレッドの完了を待つ
        thread.join(timeout=5)

        # キャンセルが適切に動作していることを確認
        assert worker.should_stop is True, "キャンセルフラグが設定されていません"

        print("✓ キャンセル機能テスト完了")

    def test_batch_processing_optimization(self):
        """バッチ処理最適化テスト"""
        # IndexManagerをモックしてバッチ処理を監視
        with patch.object(self.index_manager, 'add_document') as mock_add:
            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher
            )

            self._connect_signals(worker)
            worker.process_folder()

            # add_documentが呼ばれていることを確認
            assert mock_add.call_count > 0, "インデックスへの追加が行われていません"

        print("✓ バッチ処理最適化テスト完了")

    def test_file_watcher_integration(self):
        """FileWatcher統合テスト"""
        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )

        self._connect_signals(worker)
        worker.process_folder()

        # FileWatcherが適切に呼ばれていることを確認
        self.file_watcher.add_watch_path.assert_called_once_with(str(self.test_folder))

        print("✓ FileWatcher統合テスト完了")

    def test_statistics_accuracy(self):
        """統計情報の正確性テスト"""
        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )

        self._connect_signals(worker)
        worker.process_folder()

        # 統計情報を取得
        folder_path, stats = self.completion_signals[0]

        # 実際のファイル数と比較
        actual_supported_files = []
        for root, _, files in os.walk(self.test_folder):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in {'.txt', '.md', '.pdf', '.docx', '.doc', '.xlsx', '.xls'}:
                    actual_supported_files.append(file_path)

        assert stats['total_files_found'] == len(actual_supported_files), \
            f"発見ファイル数が不正: 期待値={len(actual_supported_files)}, 実際={stats['total_files_found']}"

        # 処理時間が記録されていることを確認
        assert stats['processing_time'] > 0, "処理時間が記録されていません"

        # エラー情報の形式を確認
        assert isinstance(stats['errors'], list), "エラー情報がリスト形式ではありません"

        print(f"✓ 統計情報の正確性テスト完了: {stats}")


@pytest.mark.integration
class TestIndexingWorkerPerformance:
    """IndexingWorkerパフォーマンステスト"""

    @pytest.fixture(autouse=True)
    def setup(self, test_config):
        """パフォーマンステスト用セットアップ"""
        self.config = test_config
        self.test_folder = Path(tempfile.mkdtemp())

        # パフォーマンステスト用の大量ファイルを作成
        self._create_performance_test_files()

        self.document_processor = DocumentProcessor()
        self.index_manager = IndexManager(str(self.config.index_dir))
        self.index_manager.create_index()
        self.file_watcher = Mock(spec=FileWatcher)

        yield

        if self.test_folder.exists():
            shutil.rmtree(self.test_folder)

    def _create_performance_test_files(self):
        """パフォーマンステスト用ファイルを作成"""
        # 様々なサイズのファイルを作成
        sizes = [
            (10, "small"),    # 小さいファイル 10個
            (5, "medium"),    # 中サイズファイル 5個
            (2, "large")      # 大きいファイル 2個
        ]

        for count, size_type in sizes:
            size_dir = self.test_folder / size_type
            size_dir.mkdir()

            for i in range(count):
                if size_type == "small":
                    content = f"小さいテストファイル {i}\n" * 5
                elif size_type == "medium":
                    content = f"中サイズテストファイル {i}\n" * 50
                else:  # large
                    content = f"大きいテストファイル {i}\n" * 500

                (size_dir / f"file_{i:03d}.txt").write_text(content, encoding='utf-8')

    @pytest.mark.slow
    def test_large_folder_processing_performance(self, performance_timer, memory_monitor):
        """大量ファイル処理パフォーマンステスト"""
        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )

        # シグナル受信用
        completion_signals = []
        worker.indexing_completed.connect(
            lambda folder, stats: completion_signals.append((folder, stats))
        )

        # パフォーマンス測定開始
        performance_timer.start()
        memory_monitor.start()

        # 処理実行
        worker.process_folder()

        # 測定終了
        processing_time = performance_timer.stop()
        memory_usage = memory_monitor.get_peak_memory()

        # 結果検証
        assert len(completion_signals) == 1, "処理が完了していません"

        folder_path, stats = completion_signals[0]

        # パフォーマンス要件の確認
        files_per_second = stats['files_processed'] / processing_time if processing_time > 0 else 0

        print("パフォーマンス結果:")
        print(f"  処理時間: {processing_time:.2f}秒")
        print(f"  処理ファイル数: {stats['files_processed']}")
        print(f"  処理速度: {files_per_second:.1f}ファイル/秒")
        print(f"  メモリ使用量: {memory_usage:.2f}MB")

        # パフォーマンス要件（調整可能）
        assert processing_time < 30, f"処理時間が長すぎます: {processing_time:.2f}秒"
        assert files_per_second > 0.5, f"処理速度が遅すぎます: {files_per_second:.1f}ファイル/秒"
        assert memory_usage < 500, f"メモリ使用量が多すぎます: {memory_usage:.2f}MB"

        print("✓ 大量ファイル処理パフォーマンステスト完了")

    def test_memory_efficiency(self, memory_monitor):
        """メモリ効率性テスト"""
        memory_monitor.start()

        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )

        # 処理前のメモリ使用量
        initial_memory = memory_monitor.get_current_memory()

        worker.process_folder()

        # 処理後のメモリ使用量
        final_memory = memory_monitor.get_current_memory()
        peak_memory = memory_monitor.get_peak_memory()

        memory_increase = final_memory - initial_memory

        print("メモリ効率性結果:")
        print(f"  初期メモリ: {initial_memory:.2f}MB")
        print(f"  最終メモリ: {final_memory:.2f}MB")
        print(f"  ピークメモリ: {peak_memory:.2f}MB")
        print(f"  メモリ増加: {memory_increase:.2f}MB")

        # メモリリークがないことを確認
        assert memory_increase < 100, f"メモリ増加が大きすぎます: {memory_increase:.2f}MB"

        print("✓ メモリ効率性テスト完了")

    def test_concurrent_processing_safety(self):
        """並行処理安全性テスト"""
        # 複数のワーカーを同時実行
        workers = []
        threads = []
        results = []

        for i in range(3):
            # 各ワーカー用のフォルダを作成
            worker_folder = self.test_folder / f"worker_{i}"
            worker_folder.mkdir()

            for j in range(5):
                (worker_folder / f"file_{j}.txt").write_text(
                    f"ワーカー{i}のファイル{j}です。",
                    encoding='utf-8'
                )

            worker = IndexingWorker(
                str(worker_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher
            )

            # 結果収集用
            worker_results = []
            worker.indexing_completed.connect(
                lambda folder, stats, wr=worker_results: wr.append((folder, stats))
            )

            workers.append(worker)
            results.append(worker_results)

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

        # 結果検証
        for i, worker_results in enumerate(results):
            assert len(worker_results) == 1, f"ワーカー{i}が完了していません"
            folder_path, stats = worker_results[0]
            assert stats['files_processed'] > 0, f"ワーカー{i}がファイルを処理していません"

        print("✓ 並行処理安全性テスト完了")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
