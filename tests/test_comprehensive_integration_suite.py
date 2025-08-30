"""
包括的統合テストスイート

全ての統合テストとデバッグ機能を統合したテストスイート
"""

import json
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.document_processor import DocumentProcessor
from src.core.embedding_manager import EmbeddingManager
from src.core.file_watcher import FileWatcher
from src.core.index_manager import IndexManager
from src.core.indexing_worker import IndexingWorker
from src.core.search_manager import SearchManager
from src.data.database import DatabaseManager
from src.data.models import Document, FileType, SearchType


@pytest.mark.integration
class TestComprehensiveIntegrationSuite:
    """包括的統合テストスイート"""

    @pytest.fixture(autouse=True)
    def setup(self, test_config):
        """包括的テスト用セットアップ"""
        self.config = test_config
        self.test_folder = Path(tempfile.mkdtemp())

        # 包括的なテストデータを作成
        self._create_comprehensive_test_data()

        # 全コンポーネントを初期化
        self._initialize_all_components()

        # テスト結果記録用
        self.test_results = {
            'start_time': datetime.now(),
            'component_tests': {},
            'integration_tests': {},
            'performance_metrics': {},
            'error_cases': {},
            'end_time': None
        }

        yield

        self.test_results['end_time'] = datetime.now()
        self._generate_test_report()

        if self.test_folder.exists():
            shutil.rmtree(self.test_folder)

    def _create_comprehensive_test_data(self):
        """包括的なテストデータを作成"""
        # 様々なファイル形式とサイズのテストデータ
        test_data = {
            'text_files': {
                'simple.txt': "シンプルなテキストファイルです。",
                'japanese.txt': "日本語のテキストファイルです。検索テスト用のキーワードを含んでいます。",
                'english.txt': "This is an English text file for testing purposes.",
                'mixed.txt': "Mixed language file 日本語と英語が混在したファイルです。",
                'empty.txt': "",
                'large.txt': "大きなファイルのテスト。\n" * 1000
            },
            'markdown_files': {
                'readme.md': """# テストプロジェクト

## 概要
これはテスト用のMarkdownファイルです。

## 機能
- 検索機能
- インデックス機能
- ファイル監視機能

## 使用方法
1. ファイルを選択
2. インデックスを作成
3. 検索を実行
""",
                'documentation.md': """# ドキュメント

## API仕様
- GET /search
- POST /index
- DELETE /document

## 設定
```json
{
  "index_dir": "./index",
  "log_level": "INFO"
}
```
"""
            },
            'nested_structure': {
                'level1': {
                    'level2': {
                        'deep_file.txt': "深くネストされたファイルです。",
                        'level3': {
                            'very_deep.txt': "非常に深くネストされたファイルです。"
                        }
                    },
                    'sibling.txt': "兄弟ファイルです。"
                }
            },
            'special_cases': {
                'special_chars_ファイル名.txt': "特殊文字を含むファイル名のテストです。",
                'spaces in name.txt': "スペースを含むファイル名のテストです。",
                'numbers123.txt': "数字を含むファイル名のテストです。"
            }
        }

        # ファイル構造を作成
        self._create_file_structure(self.test_folder, test_data)

    def _create_file_structure(self, base_path, structure):
        """ファイル構造を再帰的に作成"""
        for name, content in structure.items():
            path = base_path / name

            if isinstance(content, dict):
                # ディレクトリの場合
                path.mkdir(exist_ok=True)
                self._create_file_structure(path, content)
            else:
                # ファイルの場合
                path.write_text(content, encoding='utf-8')

    def _initialize_all_components(self):
        """全コンポーネントを初期化"""
        # データベース
        self.db_manager = DatabaseManager(str(self.config.database_file))
        self.db_manager.initialize()

        # インデックス管理
        self.index_manager = IndexManager(str(self.config.index_dir))
        self.index_manager.create_index()

        # ドキュメント処理
        self.document_processor = DocumentProcessor()

        # 埋め込み管理（モック使用）
        self.embedding_manager = Mock(spec=EmbeddingManager)
        self.embedding_manager.generate_embedding.return_value = [0.1] * 384
        self.embedding_manager.search_similar.return_value = []

        # 検索管理
        self.search_manager = SearchManager(
            self.index_manager,
            self.embedding_manager
        )

        # ファイル監視（モック使用）
        self.file_watcher = Mock(spec=FileWatcher)

        # インデックスワーカー
        self.indexing_worker = None  # 必要に応じて作成

    def test_complete_application_workflow(self):
        """完全なアプリケーションワークフローテスト"""
        print("\n=== 完全なアプリケーションワークフローテスト開始 ===")

        workflow_start = time.time()

        try:
            # 1. フォルダインデックス処理
            print("1. フォルダインデックス処理テスト")
            indexing_result = self._test_folder_indexing()
            self.test_results['integration_tests']['folder_indexing'] = indexing_result

            # 2. 検索機能テスト
            print("2. 検索機能テスト")
            search_result = self._test_search_functionality()
            self.test_results['integration_tests']['search_functionality'] = search_result

            # 3. ファイル監視テスト
            print("3. ファイル監視テスト")
            file_watching_result = self._test_file_watching()
            self.test_results['integration_tests']['file_watching'] = file_watching_result

            # 4. エラーハンドリングテスト
            print("4. エラーハンドリングテスト")
            error_handling_result = self._test_error_handling()
            self.test_results['integration_tests']['error_handling'] = error_handling_result

            # 5. パフォーマンステスト
            print("5. パフォーマンステスト")
            performance_result = self._test_performance()
            self.test_results['integration_tests']['performance'] = performance_result

            workflow_time = time.time() - workflow_start

            print(f"\n=== ワークフローテスト完了: {workflow_time:.2f}秒 ===")

            # 全体的な成功判定
            all_passed = all(
                result.get('success', False)
                for result in self.test_results['integration_tests'].values()
            )

            assert all_passed, "一部のワークフローテストが失敗しました"

        except Exception as e:
            self.test_results['integration_tests']['workflow_error'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            raise

    def _test_folder_indexing(self):
        """フォルダインデックス処理テスト"""
        try:
            start_time = time.time()

            # IndexingWorkerを作成
            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher
            )

            # 結果収集
            completion_signals = []
            progress_signals = []
            error_signals = []

            worker.indexing_completed.connect(
                lambda folder, stats: completion_signals.append((folder, stats))
            )
            worker.progress_updated.connect(
                lambda msg, current, total: progress_signals.append((msg, current, total))
            )
            worker.error_occurred.connect(
                lambda context, error: error_signals.append((context, error))
            )

            # インデックス処理実行
            worker.process_folder()

            processing_time = time.time() - start_time

            # 結果検証
            success = len(completion_signals) == 1

            if success:
                folder_path, stats = completion_signals[0]

                return {
                    'success': True,
                    'processing_time': processing_time,
                    'files_processed': stats['files_processed'],
                    'files_failed': stats['files_failed'],
                    'documents_added': stats['documents_added'],
                    'progress_updates': len(progress_signals),
                    'errors': len(error_signals),
                    'stats': stats
                }
            else:
                return {
                    'success': False,
                    'error': 'インデックス処理が完了しませんでした',
                    'processing_time': processing_time
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time if 'start_time' in locals() else 0
            }

    def _test_search_functionality(self):
        """検索機能テスト"""
        try:
            # まずインデックスにデータを追加
            test_docs = []
            for i, (file_path, content) in enumerate([
                ("test1.txt", "検索テスト用のドキュメント1です。"),
                ("test2.txt", "検索テスト用のドキュメント2です。"),
                ("test3.md", "# Markdownドキュメント\n検索機能のテストです。")
            ]):
                doc = Document(
                    id=f"search_test_{i}",
                    file_path=file_path,
                    title=f"テストドキュメント{i}",
                    content=content,
                    file_type=FileType.TEXT,
                    size=len(content.encode('utf-8'))
                )
                test_docs.append(doc)
                self.index_manager.add_document(doc)

            # 検索テスト実行
            search_results = {}

            # 全文検索テスト
            text_results = self.search_manager.search("検索テスト", SearchType.FULL_TEXT)
            search_results['full_text'] = {
                'query': '検索テスト',
                'result_count': len(text_results),
                'success': isinstance(text_results, list)
            }

            # セマンティック検索テスト
            semantic_results = self.search_manager.search("ドキュメント", SearchType.SEMANTIC)
            search_results['semantic'] = {
                'query': 'ドキュメント',
                'result_count': len(semantic_results),
                'success': isinstance(semantic_results, list)
            }

            # ハイブリッド検索テスト
            hybrid_results = self.search_manager.search("Markdown", SearchType.HYBRID)
            search_results['hybrid'] = {
                'query': 'Markdown',
                'result_count': len(hybrid_results),
                'success': isinstance(hybrid_results, list)
            }

            # 全体的な成功判定
            all_search_success = all(
                result['success'] for result in search_results.values()
            )

            return {
                'success': all_search_success,
                'search_results': search_results,
                'total_documents': len(test_docs)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _test_file_watching(self):
        """ファイル監視テスト"""
        try:
            # FileWatcherの動作をテスト
            self.file_watcher.add_watch_path.return_value = True

            # ワーカーでファイル監視を開始
            worker = IndexingWorker(
                str(self.test_folder),
                self.document_processor,
                self.index_manager,
                self.file_watcher
            )

            # ファイル監視開始をシミュレート
            worker._start_file_watching()

            # FileWatcherが呼ばれたことを確認
            self.file_watcher.add_watch_path.assert_called_with(str(self.test_folder))

            return {
                'success': True,
                'watch_path_called': self.file_watcher.add_watch_path.called,
                'watch_path': str(self.test_folder)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _test_error_handling(self):
        """エラーハンドリングテスト"""
        try:
            error_cases = {}

            # 1. ファイル処理エラーのテスト
            with patch.object(self.document_processor, 'process_file') as mock_process:
                mock_process.side_effect = Exception("テスト用エラー")

                worker = IndexingWorker(
                    str(self.test_folder),
                    self.document_processor,
                    self.index_manager,
                    self.file_watcher
                )

                error_signals = []
                completion_signals = []

                worker.error_occurred.connect(
                    lambda context, error: error_signals.append((context, error))
                )
                worker.indexing_completed.connect(
                    lambda folder, stats: completion_signals.append((folder, stats))
                )

                worker.process_folder()

                error_cases['file_processing_error'] = {
                    'error_signals': len(error_signals),
                    'completed': len(completion_signals) > 0,
                    'success': len(completion_signals) > 0  # エラーがあっても完了することを確認
                }

            # 2. データベースエラーのテスト
            with patch.object(self.index_manager, 'add_document') as mock_add:
                mock_add.side_effect = Exception("データベースエラー")

                worker = IndexingWorker(
                    str(self.test_folder),
                    self.document_processor,
                    self.index_manager,
                    self.file_watcher
                )

                db_error_signals = []
                worker.error_occurred.connect(
                    lambda context, error: db_error_signals.append((context, error))
                )

                worker.process_folder()

                error_cases['database_error'] = {
                    'error_signals': len(db_error_signals),
                    'success': len(db_error_signals) > 0  # エラーが適切に検出されることを確認
                }

            # 全体的な成功判定
            overall_success = all(
                case.get('success', False) for case in error_cases.values()
            )

            return {
                'success': overall_success,
                'error_cases': error_cases
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _test_performance(self):
        """パフォーマンステスト"""
        try:
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

                files_per_second = stats['files_processed'] / processing_time if processing_time > 0 else 0

                # パフォーマンス要件の確認
                performance_ok = (
                    processing_time < 60 and  # 60秒以内
                    files_per_second > 0.5    # 0.5ファイル/秒以上
                )

                return {
                    'success': performance_ok,
                    'processing_time': processing_time,
                    'files_processed': stats['files_processed'],
                    'files_per_second': files_per_second,
                    'performance_ok': performance_ok
                }
            else:
                return {
                    'success': False,
                    'error': 'パフォーマンステストが完了しませんでした'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_test_report(self):
        """テストレポートを生成"""
        report_file = self.config.log_dir / "comprehensive_integration_test_report.json"

        # レポートデータを準備
        report_data = {
            'test_suite': 'Comprehensive Integration Test Suite',
            'execution_time': {
                'start': self.test_results['start_time'].isoformat(),
                'end': self.test_results['end_time'].isoformat() if self.test_results['end_time'] else None,
                'duration_seconds': (
                    (self.test_results['end_time'] - self.test_results['start_time']).total_seconds()
                    if self.test_results['end_time'] else None
                )
            },
            'test_results': self.test_results,
            'summary': self._generate_test_summary()
        }

        # レポートファイルに保存
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n=== テストレポートを生成しました: {report_file} ===")

        except Exception as e:
            print(f"テストレポートの生成に失敗しました: {e}")

    def _generate_test_summary(self):
        """テストサマリーを生成"""
        integration_tests = self.test_results.get('integration_tests', {})

        total_tests = len(integration_tests)
        passed_tests = sum(1 for result in integration_tests.values() if result.get('success', False))
        failed_tests = total_tests - passed_tests

        summary = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'overall_success': failed_tests == 0
        }

        # 詳細サマリー
        for test_name, result in integration_tests.items():
            summary[f'{test_name}_success'] = result.get('success', False)
            if 'processing_time' in result:
                summary[f'{test_name}_time'] = result['processing_time']

        return summary

    def test_component_isolation(self):
        """コンポーネント分離テスト"""
        """各コンポーネントが独立して動作することを確認"""

        # 1. DocumentProcessor単体テスト
        test_file = self.test_folder / "isolation_test.txt"
        test_file.write_text("分離テスト用ファイル", encoding='utf-8')

        doc = self.document_processor.process_file(str(test_file))
        assert doc is not None, "DocumentProcessorが単体で動作しません"

        # 2. IndexManager単体テスト
        self.index_manager.add_document(doc)
        results = self.index_manager.search_text("分離テスト")
        assert isinstance(results, list), "IndexManagerが単体で動作しません"

        # 3. SearchManager単体テスト
        search_results = self.search_manager.search("分離テスト", SearchType.FULL_TEXT)
        assert isinstance(search_results, list), "SearchManagerが単体で動作しません"

        print("✓ コンポーネント分離テスト完了")

    def test_data_consistency(self):
        """データ一貫性テスト"""
        """データベース、インデックス、検索結果の一貫性を確認"""

        # テストドキュメントを作成
        test_doc = Document(
            id="consistency_test",
            file_path="consistency_test.txt",
            title="一貫性テスト",
            content="データ一貫性テスト用のドキュメントです。",
            file_type=FileType.TEXT,
            size=100
        )

        # データベースに追加
        db_success = self.db_manager.add_document(test_doc)
        assert db_success, "データベースへの追加に失敗"

        # インデックスに追加
        self.index_manager.add_document(test_doc)

        # データベースから取得
        db_doc = self.db_manager.get_document(test_doc.id)
        assert db_doc is not None, "データベースからドキュメントを取得できません"
        assert db_doc.id == test_doc.id, "データベースのドキュメントIDが一致しません"

        # インデックスから検索
        search_results = self.index_manager.search_text("一貫性テスト")
        assert len(search_results) > 0, "インデックスから検索結果を取得できません"

        print("✓ データ一貫性テスト完了")

    def test_resource_management(self):
        """リソース管理テスト"""
        """メモリ、ファイルハンドル、スレッドなどのリソース管理を確認"""

        import gc
        import threading

        # 初期状態のリソース使用量を記録
        initial_thread_count = threading.active_count()

        # 複数のワーカーを作成・実行・破棄
        for _i in range(3):
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

            # ワーカーを明示的に削除
            del worker
            gc.collect()

        # 最終的なスレッド数を確認
        final_thread_count = threading.active_count()

        # スレッドリークがないことを確認
        thread_leak = final_thread_count - initial_thread_count
        assert thread_leak <= 1, f"スレッドリークが検出されました: {thread_leak}個のスレッドが残存"

        print("✓ リソース管理テスト完了")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
