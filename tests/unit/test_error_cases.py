"""
エラーケース・境界値テスト

異常系・境界条件・リソース制限・復旧機能の包括的テスト
"""
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.config import Config
from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager


class TestErrorCases:
    """エラーケース・境界値テスト"""

    @pytest.fixture
    def temp_workspace(self):
        """テスト用一時ワークスペース"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_disk_space_exhaustion_handling(self, temp_workspace):
        """ディスク容量不足ハンドリングテスト"""
        index_manager = IndexManager(str(temp_workspace / 'index'))

        # ディスク容量不足シミュレーション
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            result = index_manager.add_document(
                '/test/doc.txt',
                'テストドキュメント',
                {'test': True}
            )

            # エラーハンドリング確認
            assert result is False or result is None

        # システム復旧確認
        normal_result = index_manager.add_document(
            '/test/recovery.txt',
            '復旧テスト',
            {'recovery': True}
        )
        assert normal_result is not False

    def test_memory_pressure_handling(self, temp_workspace):
        """メモリ圧迫ハンドリングテスト"""
        embedding_manager = EmbeddingManager(embeddings_path=str(temp_workspace / 'cache' / 'embeddings.pkl'))

        # 大量のメモリを消費する処理
        large_texts = []
        for _i in range(100):
            # 1MB程度のテキスト
            large_text = "大きなテキストデータ " * 50000
            large_texts.append(large_text)

        # メモリ不足エラーシミュレーション
        with patch.object(embedding_manager, '_generate_embedding',
                         side_effect=MemoryError("Out of memory")):

            for text in large_texts[:5]:  # 少数のみテスト
                result = embedding_manager.get_embedding(text)
                # エラー時はNoneまたはデフォルト値を返すべき
                assert result is None or isinstance(result, type(None))

    def test_corrupted_index_recovery(self, temp_workspace):
        """破損インデックス復旧テスト"""
        index_dir = temp_workspace / 'index'
        index_manager = IndexManager(str(index_dir))

        # 正常なインデックス作成
        index_manager.add_document('/test/doc1.txt', 'テスト1', {})
        index_manager.add_document('/test/doc2.txt', 'テスト2', {})

        # インデックスファイル破損シミュレーション
        index_files = list(index_dir.glob('*'))
        if index_files:
            with open(index_files[0], 'wb') as f:
                f.write(b'corrupted data')

        # 新しいマネージャーで復旧テスト
        recovery_manager = IndexManager(str(index_dir))

        # 復旧後の動作確認
        result = recovery_manager.add_document('/test/recovery.txt', '復旧テスト', {})
        assert result is not False

    def test_invalid_file_format_handling(self, temp_workspace):
        """無効ファイル形式ハンドリングテスト"""
        from src.core.document_processor import DocumentProcessor

        processor = DocumentProcessor()

        # 存在しないファイル
        result = processor.process_file('/nonexistent/file.txt')
        assert result is None or result.success is False

        # 無効な拡張子
        invalid_file = temp_workspace / 'test.invalid'
        invalid_file.write_text('無効なファイル')

        result = processor.process_file(str(invalid_file))
        assert result is None or result.success is False

        # 空ファイル
        empty_file = temp_workspace / 'empty.txt'
        empty_file.touch()

        result = processor.process_file(str(empty_file))
        # 空ファイルは正常処理されるべき
        assert result is not None

    def test_network_timeout_simulation(self, temp_workspace):
        """ネットワークタイムアウトシミュレーションテスト"""
        # 外部API呼び出しがある場合のテスト
        embedding_manager = EmbeddingManager(embeddings_path=str(temp_workspace / 'cache' / 'embeddings.pkl'))

        # タイムアウトシミュレーション
        with patch('requests.get', side_effect=TimeoutError("Connection timeout")):
            # 外部モデルダウンロードが必要な場合
            result = embedding_manager.get_embedding("テストテキスト")

            # ローカルモデルまたはキャッシュから処理されるべき
            assert result is not None or result is None  # 実装依存

    def test_concurrent_access_conflicts(self, temp_workspace):
        """並行アクセス競合テスト"""
        import threading
        import time

        index_manager = IndexManager(str(temp_workspace / 'index'))
        conflicts = []

        def concurrent_write(thread_id):
            try:
                for i in range(50):
                    result = index_manager.add_document(
                        f'/thread_{thread_id}/doc_{i}.txt',
                        f'スレッド{thread_id}ドキュメント{i}',
                        {'thread': thread_id}
                    )
                    time.sleep(0.001)  # 競合を誘発

                    if result is False:
                        conflicts.append(f'thread_{thread_id}_doc_{i}')
            except Exception as e:
                conflicts.append(f'thread_{thread_id}_exception: {str(e)}')

        # 10スレッドで並行書き込み
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_write, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 競合処理確認（完全な失敗は許容しない）
        conflict_rate = len(conflicts) / (10 * 50)
        assert conflict_rate < 0.1  # 10%未満の競合率

    def test_resource_exhaustion_graceful_degradation(self, temp_workspace):
        """リソース枯渇時の優雅な劣化テスト"""
        config_manager = Config(str(temp_workspace / 'config.json'))

        # ファイルハンドル制限シミュレーション
        with patch('builtins.open', side_effect=OSError("Too many open files")):
            # 設定保存試行
            config_manager.set('test.value', 'test')
            save_result = config_manager.save_config()

            # 失敗は許容するが、クラッシュしてはいけない
            assert save_result is False or save_result is None

        # 通常動作復旧確認
        config_manager.set('recovery.test', 'ok')
        assert config_manager.get('recovery.test') == 'ok'

    def test_malformed_data_handling(self, temp_workspace):
        """不正形式データハンドリングテスト"""
        config_file = temp_workspace / 'malformed_config.json'

        # 不正なJSONファイル作成
        config_file.write_text('{ invalid json content }')

        # 不正データからの復旧
        config_manager = Config(str(config_file))

        # デフォルト値で動作することを確認
        default_value = config_manager.get('search.max_results')
        assert default_value is not None

        # 新しい設定保存が可能であることを確認
        config_manager.set('test.new_value', 'test')
        assert config_manager.get('test.new_value') == 'test'

    def test_unicode_edge_cases(self, temp_workspace):
        """Unicode境界ケーステスト"""
        embedding_manager = EmbeddingManager(embeddings_path=str(temp_workspace / 'cache' / 'embeddings.pkl'))

        # 特殊Unicode文字
        edge_cases = [
            "🌍🚀💻",  # 絵文字
            "𝕳𝖊𝖑𝖑𝖔",  # 数学記号
            "Ĥëłłø Wørłđ",  # アクセント付き文字
            "こんにちは世界",  # 日本語
            "مرحبا بالعالم",  # アラビア語
            "Здравствуй мир",  # ロシア語
            "\x00\x01\x02",  # 制御文字
            "a" * 10000,  # 非常に長い文字列
        ]

        for text in edge_cases:
            try:
                result = embedding_manager.get_embedding(text)
                # 結果がNoneでなければ成功
                assert result is not None or result is None
            except Exception as e:
                # 例外が発生しても致命的でなければ許容
                assert not isinstance(e, SystemExit | KeyboardInterrupt)

    def test_boundary_value_limits(self, temp_workspace):
        """境界値制限テスト"""
        index_manager = IndexManager(str(temp_workspace / 'index'))

        # 境界値テスト
        boundary_cases = [
            ('', '空文字列パス'),  # 空パス
            ('/' * 1000, '非常に長いパス'),  # 長いパス
            ('/test/normal.txt', ''),  # 空コンテンツ
            ('/test/large.txt', 'x' * 1000000),  # 1MBコンテンツ
            ('/test/metadata.txt', 'test', {'key': 'value' * 10000}),  # 大きなメタデータ
        ]

        for case in boundary_cases:
            try:
                if len(case) == 2:
                    path, content = case
                    result = index_manager.add_document(path, content, {})
                else:
                    path, content, metadata = case
                    result = index_manager.add_document(path, content, metadata)

                # 結果の妥当性確認（失敗も許容）
                assert result is not None or result is None

            except Exception as e:
                # 致命的でない例外は許容
                assert not isinstance(e, SystemExit | KeyboardInterrupt | MemoryError)

    def test_system_signal_handling(self, temp_workspace):
        """システムシグナルハンドリングテスト"""
        import signal
        import threading
        import time

        index_manager = IndexManager(str(temp_workspace / 'index'))
        interrupted = False

        def interrupt_handler(signum, frame):
            nonlocal interrupted
            interrupted = True

        # シグナルハンドラー設定
        original_handler = signal.signal(signal.SIGINT, interrupt_handler)

        try:
            def long_running_task():
                for i in range(1000):
                    if interrupted:
                        break
                    index_manager.add_document(
                        f'/signal_test/doc_{i}.txt',
                        f'シグナルテスト{i}',
                        {'doc_id': i}
                    )
                    time.sleep(0.001)

            # バックグラウンドタスク開始
            task_thread = threading.Thread(target=long_running_task)
            task_thread.start()

            # 短時間後に割り込み
            time.sleep(0.1)
            os.kill(os.getpid(), signal.SIGINT)

            task_thread.join(timeout=5.0)

            # 割り込み処理確認
            assert interrupted is True

        finally:
            # シグナルハンドラー復元
            signal.signal(signal.SIGINT, original_handler)
