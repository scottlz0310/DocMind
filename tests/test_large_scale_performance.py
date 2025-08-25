# -*- coding: utf-8 -*-
"""
大規模パフォーマンステスト

大量ファイルでのインデックス処理パフォーマンステスト
"""

import pytest
import tempfile
import shutil
import os
import time
import threading
import random
import string
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
import psutil
import gc

from src.core.indexing_worker import IndexingWorker
from src.core.document_processor import DocumentProcessor
from src.core.index_manager import IndexManager
from src.core.file_watcher import FileWatcher
from src.data.models import Document, FileType


@pytest.mark.slow
@pytest.mark.performance
class TestLargeScalePerformance:
    """大規模パフォーマンステスト"""

    @pytest.fixture(autouse=True)
    def setup(self, test_config):
        """大規模テスト用セットアップ"""
        self.config = test_config
        self.test_folder = Path(tempfile.mkdtemp())
        
        # パフォーマンス測定用の変数
        self.performance_metrics = {
            'start_time': 0,
            'end_time': 0,
            'memory_usage': [],
            'cpu_usage': [],
            'file_processing_times': [],
            'batch_processing_times': []
        }
        
        # コンポーネント初期化
        self.document_processor = DocumentProcessor()
        self.index_manager = IndexManager(str(self.config.index_dir))
        self.index_manager.create_index()
        self.file_watcher = Mock(spec=FileWatcher)
        
        yield
        
        if self.test_folder.exists():
            shutil.rmtree(self.test_folder)

    def _generate_random_content(self, size_category='medium'):
        """ランダムなコンテンツを生成"""
        if size_category == 'small':
            lines = random.randint(5, 20)
        elif size_category == 'medium':
            lines = random.randint(50, 200)
        elif size_category == 'large':
            lines = random.randint(500, 1000)
        else:
            lines = random.randint(10, 50)
        
        content_lines = []
        for _ in range(lines):
            # ランダムな日本語風テキストを生成
            words = [
                "これは", "テスト", "ドキュメント", "です", "内容", "検索", "キーワード",
                "システム", "処理", "データ", "ファイル", "情報", "管理", "機能",
                "プログラム", "アプリケーション", "インデックス", "データベース"
            ]
            line_words = random.sample(words, random.randint(3, 8))
            content_lines.append(" ".join(line_words) + "。")
        
        return "\n".join(content_lines)

    def _create_large_dataset(self, file_counts):
        """大規模データセットを作成"""
        print(f"大規模データセットを作成中...")
        
        total_files = sum(file_counts.values())
        created_files = 0
        
        for file_type, count in file_counts.items():
            type_dir = self.test_folder / file_type
            type_dir.mkdir()
            
            for i in range(count):
                if file_type == 'small':
                    content = self._generate_random_content('small')
                    file_path = type_dir / f"small_{i:04d}.txt"
                elif file_type == 'medium':
                    content = self._generate_random_content('medium')
                    file_path = type_dir / f"medium_{i:04d}.txt"
                elif file_type == 'large':
                    content = self._generate_random_content('large')
                    file_path = type_dir / f"large_{i:04d}.txt"
                elif file_type == 'markdown':
                    content = f"# ドキュメント {i}\n\n" + self._generate_random_content('medium')
                    file_path = type_dir / f"doc_{i:04d}.md"
                else:
                    content = self._generate_random_content('medium')
                    file_path = type_dir / f"file_{i:04d}.txt"
                
                file_path.write_text(content, encoding='utf-8')
                created_files += 1
                
                # 進捗表示
                if created_files % 100 == 0:
                    progress = (created_files / total_files) * 100
                    print(f"  作成進捗: {created_files}/{total_files} ({progress:.1f}%)")
        
        print(f"データセット作成完了: {created_files}ファイル")
        return created_files

    def _monitor_system_resources(self, worker, interval=1.0):
        """システムリソースを監視"""
        def monitor():
            process = psutil.Process()
            while not getattr(worker, '_monitoring_stopped', False):
                try:
                    # CPU使用率
                    cpu_percent = process.cpu_percent()
                    
                    # メモリ使用量
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    
                    self.performance_metrics['cpu_usage'].append(cpu_percent)
                    self.performance_metrics['memory_usage'].append(memory_mb)
                    
                    time.sleep(interval)
                except:
                    break
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        return monitor_thread

    def test_1000_files_performance(self, performance_timer, memory_monitor):
        """1000ファイルパフォーマンステスト"""
        # データセット作成
        file_counts = {
            'small': 600,    # 小さいファイル
            'medium': 300,   # 中サイズファイル
            'large': 80,     # 大きいファイル
            'markdown': 20   # Markdownファイル
        }
        
        total_files = self._create_large_dataset(file_counts)
        
        # パフォーマンス測定開始
        performance_timer.start()
        memory_monitor.start()
        
        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )
        
        # システムリソース監視開始
        monitor_thread = self._monitor_system_resources(worker)
        
        # 結果収集用
        completion_signals = []
        progress_signals = []
        
        worker.indexing_completed.connect(
            lambda folder, stats: completion_signals.append((folder, stats))
        )
        worker.progress_updated.connect(
            lambda msg, current, total: progress_signals.append((msg, current, total))
        )
        
        # 処理実行
        self.performance_metrics['start_time'] = time.time()
        worker.process_folder()
        self.performance_metrics['end_time'] = time.time()
        
        # 監視停止
        worker._monitoring_stopped = True
        monitor_thread.join(timeout=1)
        
        # パフォーマンス測定終了
        processing_time = performance_timer.stop()
        peak_memory = memory_monitor.get_peak_memory()
        
        # 結果検証
        assert len(completion_signals) == 1, "処理が完了していません"
        
        folder_path, stats = completion_signals[0]
        
        # パフォーマンス分析
        files_per_second = stats['files_processed'] / processing_time if processing_time > 0 else 0
        avg_memory = sum(self.performance_metrics['memory_usage']) / len(self.performance_metrics['memory_usage']) if self.performance_metrics['memory_usage'] else 0
        max_cpu = max(self.performance_metrics['cpu_usage']) if self.performance_metrics['cpu_usage'] else 0
        
        print(f"\n=== 1000ファイルパフォーマンステスト結果 ===")
        print(f"総ファイル数: {total_files}")
        print(f"処理ファイル数: {stats['files_processed']}")
        print(f"失敗ファイル数: {stats['files_failed']}")
        print(f"処理時間: {processing_time:.2f}秒")
        print(f"処理速度: {files_per_second:.1f}ファイル/秒")
        print(f"ピークメモリ: {peak_memory:.2f}MB")
        print(f"平均メモリ: {avg_memory:.2f}MB")
        print(f"最大CPU使用率: {max_cpu:.1f}%")
        
        # パフォーマンス要件の確認
        assert processing_time < 300, f"処理時間が長すぎます: {processing_time:.2f}秒 (要件: 300秒以内)"
        assert files_per_second > 2, f"処理速度が遅すぎます: {files_per_second:.1f}ファイル/秒 (要件: 2ファイル/秒以上)"
        assert peak_memory < 1000, f"メモリ使用量が多すぎます: {peak_memory:.2f}MB (要件: 1000MB以内)"
        
        print("✓ 1000ファイルパフォーマンステスト完了")

    @pytest.mark.very_slow
    def test_5000_files_stress_test(self, performance_timer, memory_monitor):
        """5000ファイルストレステスト"""
        # より大規模なデータセット
        file_counts = {
            'small': 3000,
            'medium': 1500,
            'large': 400,
            'markdown': 100
        }
        
        total_files = self._create_large_dataset(file_counts)
        
        # ストレステスト実行
        performance_timer.start()
        memory_monitor.start()
        
        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )
        
        monitor_thread = self._monitor_system_resources(worker, interval=2.0)
        
        completion_signals = []
        worker.indexing_completed.connect(
            lambda folder, stats: completion_signals.append((folder, stats))
        )
        
        # 処理実行
        worker.process_folder()
        
        # 監視停止
        worker._monitoring_stopped = True
        monitor_thread.join(timeout=2)
        
        processing_time = performance_timer.stop()
        peak_memory = memory_monitor.get_peak_memory()
        
        # 結果検証
        assert len(completion_signals) == 1, "ストレステストが完了していません"
        
        folder_path, stats = completion_signals[0]
        
        print(f"\n=== 5000ファイルストレステスト結果 ===")
        print(f"総ファイル数: {total_files}")
        print(f"処理ファイル数: {stats['files_processed']}")
        print(f"処理時間: {processing_time:.2f}秒")
        print(f"ピークメモリ: {peak_memory:.2f}MB")
        
        # ストレステスト要件（より緩い要件）
        assert processing_time < 1800, f"ストレステスト処理時間が長すぎます: {processing_time:.2f}秒"
        assert peak_memory < 2000, f"ストレステストメモリ使用量が多すぎます: {peak_memory:.2f}MB"
        
        print("✓ 5000ファイルストレステスト完了")

    def test_memory_efficiency_under_load(self, memory_monitor):
        """負荷時のメモリ効率性テスト"""
        # 中規模データセット
        file_counts = {
            'small': 200,
            'medium': 100,
            'large': 50
        }
        
        self._create_large_dataset(file_counts)
        
        memory_monitor.start()
        
        # メモリ使用量の詳細追跡
        memory_snapshots = []
        
        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )
        
        def track_memory_progress(msg, current, total):
            memory_usage = memory_monitor.get_current_memory()
            memory_snapshots.append({
                'stage': msg,
                'progress': current / total if total > 0 else 0,
                'memory_mb': memory_usage
            })
        
        worker.progress_updated.connect(track_memory_progress)
        
        # ガベージコレクション強制実行
        gc.collect()
        initial_memory = memory_monitor.get_current_memory()
        
        worker.process_folder()
        
        gc.collect()
        final_memory = memory_monitor.get_current_memory()
        peak_memory = memory_monitor.get_peak_memory()
        
        # メモリ効率性分析
        memory_increase = final_memory - initial_memory
        memory_efficiency = len(memory_snapshots) / peak_memory if peak_memory > 0 else 0
        
        print(f"\n=== メモリ効率性テスト結果 ===")
        print(f"初期メモリ: {initial_memory:.2f}MB")
        print(f"最終メモリ: {final_memory:.2f}MB")
        print(f"ピークメモリ: {peak_memory:.2f}MB")
        print(f"メモリ増加: {memory_increase:.2f}MB")
        print(f"メモリ効率性: {memory_efficiency:.3f}")
        
        # メモリリークの確認
        assert memory_increase < 200, f"メモリリークの可能性: {memory_increase:.2f}MB増加"
        assert peak_memory < 800, f"ピークメモリが高すぎます: {peak_memory:.2f}MB"
        
        print("✓ メモリ効率性テスト完了")

    def test_concurrent_processing_performance(self, performance_timer):
        """並行処理パフォーマンステスト"""
        # 複数のフォルダを作成
        folder_count = 3
        folders = []
        
        for i in range(folder_count):
            folder = self.test_folder / f"concurrent_{i}"
            folder.mkdir()
            folders.append(folder)
            
            # 各フォルダにファイルを作成
            for j in range(50):
                (folder / f"file_{j:03d}.txt").write_text(
                    f"並行処理テスト用ファイル {i}-{j}\n" + self._generate_random_content('small'),
                    encoding='utf-8'
                )
        
        # 並行処理実行
        performance_timer.start()
        
        workers = []
        threads = []
        results = []
        
        for folder in folders:
            worker = IndexingWorker(
                str(folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher
            )
            
            worker_results = []
            worker.indexing_completed.connect(
                lambda folder_path, stats, wr=worker_results: wr.append((folder_path, stats))
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
            thread.join(timeout=120)
        
        processing_time = performance_timer.stop()
        
        # 結果検証
        completed_workers = sum(1 for worker_results in results if len(worker_results) > 0)
        total_files_processed = sum(
            worker_results[0][1]['files_processed'] 
            for worker_results in results 
            if len(worker_results) > 0
        )
        
        print(f"\n=== 並行処理パフォーマンステスト結果 ===")
        print(f"並行ワーカー数: {folder_count}")
        print(f"完了ワーカー数: {completed_workers}")
        print(f"総処理ファイル数: {total_files_processed}")
        print(f"並行処理時間: {processing_time:.2f}秒")
        
        assert completed_workers >= 2, f"十分なワーカーが完了していません: {completed_workers}/{folder_count}"
        assert processing_time < 180, f"並行処理時間が長すぎます: {processing_time:.2f}秒"
        
        print("✓ 並行処理パフォーマンステスト完了")

    def test_scalability_analysis(self):
        """スケーラビリティ分析テスト"""
        # 異なるサイズのデータセットでパフォーマンスを測定
        test_sizes = [50, 100, 200, 500]
        scalability_results = []
        
        for size in test_sizes:
            print(f"\nスケーラビリティテスト: {size}ファイル")
            
            # テスト用フォルダを作成
            size_folder = self.test_folder / f"scale_{size}"
            size_folder.mkdir()
            
            # ファイルを作成
            for i in range(size):
                (size_folder / f"file_{i:03d}.txt").write_text(
                    f"スケーラビリティテスト用ファイル {i}\n" + self._generate_random_content('small'),
                    encoding='utf-8'
                )
            
            # パフォーマンス測定
            start_time = time.time()
            
            worker = IndexingWorker(
                str(size_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher
            )
            
            completion_signals = []
            worker.indexing_completed.connect(
                lambda folder, stats: completion_signals.append((folder, stats))
            )
            
            worker.process_folder()
            
            processing_time = time.time() - start_time
            
            # 結果記録
            if completion_signals:
                folder_path, stats = completion_signals[0]
                files_per_second = stats['files_processed'] / processing_time if processing_time > 0 else 0
                
                scalability_results.append({
                    'file_count': size,
                    'processing_time': processing_time,
                    'files_per_second': files_per_second,
                    'files_processed': stats['files_processed']
                })
        
        # スケーラビリティ分析
        print(f"\n=== スケーラビリティ分析結果 ===")
        for result in scalability_results:
            print(f"ファイル数: {result['file_count']:3d}, "
                  f"処理時間: {result['processing_time']:6.2f}秒, "
                  f"処理速度: {result['files_per_second']:6.1f}ファイル/秒")
        
        # 線形スケーラビリティの確認
        if len(scalability_results) >= 2:
            first_result = scalability_results[0]
            last_result = scalability_results[-1]
            
            size_ratio = last_result['file_count'] / first_result['file_count']
            time_ratio = last_result['processing_time'] / first_result['processing_time']
            
            scalability_factor = time_ratio / size_ratio
            
            print(f"スケーラビリティ係数: {scalability_factor:.2f} (1.0に近いほど線形)")
            
            # スケーラビリティ要件（処理時間がファイル数に比例的に増加）
            assert scalability_factor < 2.0, f"スケーラビリティが悪すぎます: {scalability_factor:.2f}"
        
        print("✓ スケーラビリティ分析テスト完了")


@pytest.mark.performance
class TestPerformanceRegression:
    """パフォーマンス回帰テスト"""

    @pytest.fixture(autouse=True)
    def setup(self, test_config):
        """パフォーマンス回帰テスト用セットアップ"""
        self.config = test_config
        self.test_folder = Path(tempfile.mkdtemp())
        
        # 標準的なテストデータセットを作成
        self._create_standard_dataset()
        
        self.document_processor = DocumentProcessor()
        self.index_manager = IndexManager(str(self.config.index_dir))
        self.index_manager.create_index()
        self.file_watcher = Mock(spec=FileWatcher)
        
        yield
        
        if self.test_folder.exists():
            shutil.rmtree(self.test_folder)

    def _create_standard_dataset(self):
        """標準的なテストデータセットを作成"""
        # 一定のパフォーマンステスト用データセット
        for i in range(100):
            content = f"標準テストファイル {i}\n" + "テスト内容 " * 50
            (self.test_folder / f"standard_{i:03d}.txt").write_text(content, encoding='utf-8')

    def test_baseline_performance(self, performance_timer, memory_monitor):
        """ベースラインパフォーマンステスト"""
        # ベースラインパフォーマンスを測定
        performance_timer.start()
        memory_monitor.start()
        
        worker = IndexingWorker(
            str(self.test_folder),
            self.document_processor,
            self.index_manager,
            self.file_watcher
        )
        
        completion_signals = []
        worker.indexing_completed.connect(
            lambda folder, stats: completion_signals.append((folder, stats))
        )
        
        worker.process_folder()
        
        processing_time = performance_timer.stop()
        peak_memory = memory_monitor.get_peak_memory()
        
        # ベースライン結果
        assert len(completion_signals) == 1, "ベースラインテストが完了していません"
        
        folder_path, stats = completion_signals[0]
        
        baseline_metrics = {
            'processing_time': processing_time,
            'peak_memory': peak_memory,
            'files_processed': stats['files_processed'],
            'files_per_second': stats['files_processed'] / processing_time if processing_time > 0 else 0
        }
        
        print(f"\n=== ベースラインパフォーマンス ===")
        print(f"処理時間: {baseline_metrics['processing_time']:.2f}秒")
        print(f"ピークメモリ: {baseline_metrics['peak_memory']:.2f}MB")
        print(f"処理ファイル数: {baseline_metrics['files_processed']}")
        print(f"処理速度: {baseline_metrics['files_per_second']:.1f}ファイル/秒")
        
        # ベースライン要件
        assert baseline_metrics['processing_time'] < 60, "ベースライン処理時間が長すぎます"
        assert baseline_metrics['peak_memory'] < 500, "ベースラインメモリ使用量が多すぎます"
        assert baseline_metrics['files_per_second'] > 1, "ベースライン処理速度が遅すぎます"
        
        print("✓ ベースラインパフォーマンステスト完了")

    def test_repeated_performance_consistency(self):
        """繰り返しパフォーマンス一貫性テスト"""
        # 複数回実行してパフォーマンスの一貫性を確認
        run_count = 5
        results = []
        
        for run in range(run_count):
            print(f"パフォーマンス一貫性テスト実行 {run + 1}/{run_count}")
            
            start_time = time.time()
            
            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher
            )
            
            completion_signals = []
            worker.indexing_completed.connect(
                lambda folder, stats: completion_signals.append((folder, stats))
            )
            
            worker.process_folder()
            
            processing_time = time.time() - start_time
            
            if completion_signals:
                folder_path, stats = completion_signals[0]
                results.append({
                    'run': run + 1,
                    'processing_time': processing_time,
                    'files_processed': stats['files_processed']
                })
        
        # 一貫性分析
        if results:
            processing_times = [r['processing_time'] for r in results]
            avg_time = sum(processing_times) / len(processing_times)
            min_time = min(processing_times)
            max_time = max(processing_times)
            
            # 標準偏差計算
            variance = sum((t - avg_time) ** 2 for t in processing_times) / len(processing_times)
            std_dev = variance ** 0.5
            
            # 変動係数（CV）
            cv = (std_dev / avg_time) * 100 if avg_time > 0 else 0
            
            print(f"\n=== パフォーマンス一貫性分析 ===")
            print(f"実行回数: {run_count}")
            print(f"平均処理時間: {avg_time:.2f}秒")
            print(f"最小処理時間: {min_time:.2f}秒")
            print(f"最大処理時間: {max_time:.2f}秒")
            print(f"標準偏差: {std_dev:.2f}秒")
            print(f"変動係数: {cv:.1f}%")
            
            # 一貫性要件（変動係数が20%以下）
            assert cv < 20, f"パフォーマンスの変動が大きすぎます: {cv:.1f}%"
        
        print("✓ 繰り返しパフォーマンス一貫性テスト完了")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])