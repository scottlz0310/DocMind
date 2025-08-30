"""
統合ワークフロー検証クラスのテスト

EndToEndWorkflowValidatorクラスの動作を検証するテストケース
"""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.data.models import Document, SearchResult, SearchType
from tests.validation_framework.base_validator import ValidationConfig
from tests.validation_framework.end_to_end_workflow_validator import (
    EndToEndWorkflowValidator,
)


class TestEndToEndWorkflowValidator:
    """統合ワークフロー検証クラスのテスト"""

    @pytest.fixture
    def validator_config(self):
        """テスト用の検証設定"""
        config = ValidationConfig()
        config.enable_performance_monitoring = True
        config.enable_memory_monitoring = True
        config.enable_error_injection = False
        config.max_execution_time = 60.0
        config.max_memory_usage = 1024.0
        config.log_level = "INFO"
        return config

    @pytest.fixture
    def validator(self, validator_config):
        """テスト用のバリデーターインスタンス"""
        validator = EndToEndWorkflowValidator(validator_config)
        yield validator
        # クリーンアップ
        try:
            validator.teardown_test_environment()
            validator.cleanup()
        except Exception:
            pass

    def test_validator_initialization(self, validator_config):
        """バリデーターの初期化テスト"""
        validator = EndToEndWorkflowValidator(validator_config)

        # 基本属性の確認
        assert validator.config == validator_config
        assert validator.test_data_generator is not None
        assert validator.temp_dir is None  # セットアップ前
        assert validator.test_config is None  # セットアップ前

        # ワークフロー状態の初期化確認
        expected_states = [
            'startup_completed',
            'documents_processed',
            'search_executed',
            'results_displayed',
            'background_processing'
        ]

        for state in expected_states:
            assert state in validator.workflow_state
            assert validator.workflow_state[state] is False

        validator.cleanup()

    def test_setup_test_environment(self, validator):
        """テスト環境セットアップのテスト"""
        # セットアップ前の状態確認
        assert validator.temp_dir is None
        assert validator.test_config is None

        # セットアップ実行
        validator.setup_test_environment()

        # セットアップ後の状態確認
        assert validator.temp_dir is not None
        assert validator.temp_dir.exists()
        assert validator.test_config is not None

        # 必要なディレクトリの存在確認
        assert validator.test_config.data_dir.exists()
        assert validator.test_config.index_dir.exists()
        assert validator.test_config.cache_dir.exists()

        # ベースラインメトリクスの確認
        assert validator.memory_baseline > 0
        assert validator.cpu_baseline >= 0

    def test_teardown_test_environment(self, validator):
        """テスト環境クリーンアップのテスト"""
        # セットアップ
        validator.setup_test_environment()
        temp_dir = validator.temp_dir

        # クリーンアップ実行
        validator.teardown_test_environment()

        # クリーンアップ後の状態確認
        assert not temp_dir.exists()

    @patch('tests.validation_framework.end_to_end_workflow_validator.DatabaseManager')
    @patch('tests.validation_framework.end_to_end_workflow_validator.IndexManager')
    @patch('tests.validation_framework.end_to_end_workflow_validator.EmbeddingManager')
    @patch('tests.validation_framework.end_to_end_workflow_validator.DocumentProcessor')
    @patch('tests.validation_framework.end_to_end_workflow_validator.SearchManager')
    def test_validate_application_startup(self, mock_search_manager, mock_doc_processor,
                                        mock_embedding_manager, mock_index_manager,
                                        mock_db_manager, validator):
        """アプリケーション起動検証のテスト"""
        # セットアップ
        validator.setup_test_environment()

        # モックの設定
        mock_db_instance = Mock()
        mock_db_manager.return_value = mock_db_instance

        mock_index_instance = Mock()
        mock_index_manager.return_value = mock_index_instance

        mock_embedding_instance = Mock()
        mock_embedding_manager.return_value = mock_embedding_instance

        mock_doc_instance = Mock()
        mock_doc_processor.return_value = mock_doc_instance

        mock_search_instance = Mock()
        mock_search_manager.return_value = mock_search_instance

        # 起動検証の実行
        validator._validate_application_startup()

        # 状態の確認
        assert validator.workflow_state['startup_completed'] is True
        assert validator.db_manager is not None
        assert validator.index_manager is not None
        assert validator.embedding_manager is not None
        assert validator.document_processor is not None
        assert validator.search_manager is not None

        # モックメソッドの呼び出し確認
        mock_db_instance.initialize.assert_called_once()
        mock_index_instance.create_index.assert_called_once()

    def test_validate_document_processing(self, validator):
        """ドキュメント処理検証のテスト"""
        # セットアップ
        validator.setup_test_environment()

        # モックコンポーネントの設定
        validator.db_manager = Mock()
        validator.index_manager = Mock()
        validator.document_processor = Mock()

        # テストドキュメントの作成
        test_files = []
        for i in range(3):
            test_file = validator.test_config.data_dir / f"test_{i}.txt"
            test_file.write_text(f"テストドキュメント {i} の内容", encoding='utf-8')
            test_files.append(test_file)

        # ドキュメント処理のモック設定
        def mock_process_file(file_path):
            return Document(
                id=f"doc_{Path(file_path).stem}",
                file_path=file_path,
                title=f"テストドキュメント {Path(file_path).stem}",
                content=f"テスト内容 {Path(file_path).stem}",
                file_type="text",
                size=100
            )

        validator.document_processor.process_file.side_effect = mock_process_file
        validator.db_manager.add_document.return_value = True

        # テストデータ生成器のモック
        with patch.object(validator.test_data_generator, 'create_standard_dataset') as mock_create:
            mock_create.return_value = test_files

            # ドキュメント処理検証の実行
            validator._validate_document_processing()

        # 状態の確認
        assert validator.workflow_state['documents_processed'] is True

        # 処理回数の確認
        assert validator.document_processor.process_file.call_count == len(test_files)
        assert validator.db_manager.add_document.call_count == len(test_files)
        assert validator.index_manager.add_document.call_count == len(test_files)

    def test_validate_search_execution(self, validator):
        """検索実行検証のテスト"""
        # セットアップ
        validator.setup_test_environment()

        # モック検索マネージャーの設定
        validator.search_manager = Mock()
        validator.search_manager.search.return_value = [
            SearchResult(
                document=Document(
                    id="test_doc",
                    file_path="test.txt",
                    title="テストドキュメント",
                    content="テスト内容",
                    file_type="text",
                    size=100
                ),
                score=0.95,
                search_type=SearchType.FULL_TEXT,
                snippet="テスト内容...",
                highlighted_terms=["テスト"],
                relevance_explanation="キーワードマッチ"
            )
        ]

        # 検索実行検証
        validator._validate_search_execution()

        # 状態の確認
        assert validator.workflow_state['search_executed'] is True

        # 検索実行の確認
        assert validator.search_manager.search.call_count >= 3  # テストクエリ数

    def test_validate_result_display(self, validator):
        """結果表示検証のテスト"""
        # セットアップ
        validator.setup_test_environment()

        # 結果表示検証の実行
        validator._validate_result_display()

        # 状態の確認
        assert validator.workflow_state['results_displayed'] is True

    def test_complete_application_workflow(self, validator):
        """完全なアプリケーションワークフローのテスト"""
        # 各段階のモック化
        with patch.object(validator, '_validate_application_startup') as mock_startup, \
             patch.object(validator, '_validate_document_processing') as mock_doc_proc, \
             patch.object(validator, '_validate_indexing_process') as mock_indexing, \
             patch.object(validator, '_validate_search_execution') as mock_search, \
             patch.object(validator, '_validate_result_display') as mock_display, \
             patch.object(validator, '_validate_workflow_completion') as mock_completion:

            # ワークフロー状態の設定
            def set_startup_completed():
                validator.workflow_state['startup_completed'] = True

            def set_documents_processed():
                validator.workflow_state['documents_processed'] = True

            def set_search_executed():
                validator.workflow_state['search_executed'] = True

            def set_results_displayed():
                validator.workflow_state['results_displayed'] = True

            mock_startup.side_effect = set_startup_completed
            mock_doc_proc.side_effect = set_documents_processed
            mock_search.side_effect = set_search_executed
            mock_display.side_effect = set_results_displayed

            # 完全ワークフローの実行
            validator.test_complete_application_workflow()

            # 各段階の実行確認
            mock_startup.assert_called_once()
            mock_doc_proc.assert_called_once()
            mock_indexing.assert_called_once()
            mock_search.assert_called_once()
            mock_display.assert_called_once()
            mock_completion.assert_called_once()

    def test_hybrid_search_workflow(self, validator):
        """ハイブリッド検索ワークフローのテスト"""
        # セットアップ
        validator.setup_test_environment()
        validator.workflow_state['documents_processed'] = True

        # モック検索マネージャーの設定
        validator.search_manager = Mock()

        def mock_search(query, search_type):
            return [
                SearchResult(
                    document=Document(
                        id=f"doc_{search_type.value}",
                        file_path="test.txt",
                        title=f"テストドキュメント {search_type.value}",
                        content=f"テスト内容 {query}",
                        file_type="text",
                        size=100
                    ),
                    score=0.95,
                    search_type=search_type,
                    snippet=f"テスト内容 {query}...",
                    highlighted_terms=[query.split()[0]],
                    relevance_explanation="テストマッチ"
                )
            ]

        validator.search_manager.search.side_effect = mock_search

        # ハイブリッド検索ワークフローの実行
        validator.test_hybrid_search_workflow()

        # 検索実行回数の確認（各クエリで3回の検索タイプ）
        expected_calls = 4 * 3  # 4クエリ × 3検索タイプ
        assert validator.search_manager.search.call_count == expected_calls

    def test_background_processing_responsiveness(self, validator):
        """バックグラウンド処理中の応答性テスト"""
        # セットアップ
        validator.setup_test_environment()

        # GUIコンポーネントの初期化
        validator._initialize_gui_components()

        # 応答性検証の実行（短縮版）
        with patch.object(validator, '_simulate_heavy_background_processing') as mock_bg_proc, \
             patch.object(validator, '_simulate_ui_interaction') as mock_ui_interact:

            # バックグラウンド処理を即座に完了させる
            def quick_bg_process():
                validator.workflow_state['background_processing'] = True
                time.sleep(0.1)  # 短い処理時間
                validator.workflow_state['background_processing'] = False

            mock_bg_proc.side_effect = quick_bg_process

            # UI操作を高速化
            mock_ui_interact.return_value = None

            # 応答性検証の実行
            validator.test_background_processing_responsiveness()

            # バックグラウンド処理とUI操作の実行確認
            mock_bg_proc.assert_called_once()
            assert mock_ui_interact.call_count > 0

    def test_configuration_hot_reload(self, validator):
        """設定変更の即座反映テスト"""
        # セットアップ
        validator.setup_test_environment()

        # 設定変更テストの実行
        validator.test_configuration_hot_reload()

        # テスト完了の確認（例外が発生しないことを確認）
        assert True

    def test_long_term_stability(self, validator):
        """長時間連続使用時の安定性テスト"""
        # セットアップ
        validator.setup_test_environment()

        # 典型的使用パターンのモック化
        with patch.object(validator, '_simulate_typical_usage_pattern') as mock_usage:
            mock_usage.return_value = None

            # 安定性検証の実行
            validator.test_long_term_stability()

            # 使用パターンシミュレーションの実行確認
            assert mock_usage.call_count > 0

    def test_run_validation_integration(self, validator):
        """統合検証実行のテスト"""
        # テスト環境のセットアップ
        validator.setup_test_environment()

        # 主要メソッドのモック化
        with patch.object(validator, 'test_complete_application_workflow') as mock_workflow, \
             patch.object(validator, 'test_hybrid_search_workflow') as mock_hybrid, \
             patch.object(validator, 'test_background_processing_responsiveness') as mock_bg, \
             patch.object(validator, 'test_configuration_hot_reload') as mock_config, \
             patch.object(validator, 'test_long_term_stability') as mock_stability:

            # 検証実行
            results = validator.run_validation()

            # 結果の確認
            assert isinstance(results, list)
            assert len(results) == 5  # 5つのテストメソッド

            # 各テストメソッドの実行確認
            mock_workflow.assert_called_once()
            mock_hybrid.assert_called_once()
            mock_bg.assert_called_once()
            mock_config.assert_called_once()
            mock_stability.assert_called_once()

            # 結果の詳細確認
            for result in results:
                assert hasattr(result, 'test_name')
                assert hasattr(result, 'success')
                assert hasattr(result, 'execution_time')
                assert hasattr(result, 'memory_usage')

    def test_performance_requirements_validation(self, validator):
        """パフォーマンス要件検証のテスト"""
        # セットアップ
        validator.setup_test_environment()

        # モック結果の作成
        from datetime import datetime

        from tests.validation_framework.base_validator import ValidationResult

        # 成功ケース
        good_result = ValidationResult(
            test_name="test_performance",
            success=True,
            execution_time=2.0,  # 5秒以内
            memory_usage=500.0,  # 1GB以内
            timestamp=datetime.now()
        )
        validator.validation_results = [good_result]

        # パフォーマンス要件の検証
        is_valid = validator.validate_performance_requirements(5.0, 1000.0)
        assert is_valid is True

        # 失敗ケース
        bad_result = ValidationResult(
            test_name="test_performance_bad",
            success=True,
            execution_time=10.0,  # 5秒超過
            memory_usage=2000.0,  # 1GB超過
            timestamp=datetime.now()
        )
        validator.validation_results = [bad_result]

        # パフォーマンス要件の検証
        is_valid = validator.validate_performance_requirements(5.0, 1000.0)
        assert is_valid is False

    def test_error_handling_during_validation(self, validator):
        """検証中のエラーハンドリングテスト"""
        # セットアップ
        validator.setup_test_environment()

        # エラーを発生させるテストメソッドの追加
        def failing_test():
            raise Exception("テスト用エラー")

        validator.test_failing_method = failing_test

        # エラーが発生するテストの実行
        results = validator.run_validation(['test_failing_method'])

        # 結果の確認
        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error_message == "テスト用エラー"
        assert 'traceback' in result.details

    def test_memory_monitoring_integration(self, validator_config):
        """メモリ監視統合のテスト"""
        # メモリ監視有効化
        validator_config.enable_memory_monitoring = True
        validator = EndToEndWorkflowValidator(validator_config)

        try:
            validator.setup_test_environment()

            # メモリ使用量を増加させるテスト
            def memory_intensive_test():
                # 大きなデータ構造を作成
                large_data = list(range(100000))
                return len(large_data)

            validator.test_memory_test = memory_intensive_test

            # テスト実行
            results = validator.run_validation(['test_memory_test'])

            # メモリ使用量が記録されていることを確認
            assert len(results) == 1
            result = results[0]
            assert result.memory_usage > 0

        finally:
            validator.teardown_test_environment()
            validator.cleanup()


if __name__ == "__main__":
    # 単体テスト実行
    pytest.main([__file__, "-v"])
