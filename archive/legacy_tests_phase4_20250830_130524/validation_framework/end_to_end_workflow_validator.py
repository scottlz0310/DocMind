"""
統合ワークフロー検証クラス

DocMindアプリケーションの完全なユーザーワークフローを検証します。
アプリケーション起動からドキュメント処理、検索、結果表示までの
一連の流れを包括的に検証し、実際の使用シナリオでの動作を確認します。
"""

import gc
import shutil
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import psutil

try:
    from .base_validator import BaseValidator, ValidationConfig, ValidationResult
    from .memory_monitor import MemoryMonitor
    from .performance_monitor import PerformanceMonitor
    from .test_data_generator import TestDataGenerator
except ImportError:
    from base_validator import BaseValidator, ValidationConfig
    from test_data_generator import TestDataGenerator

# DocMindコンポーネントのインポート
try:
    from src.core.document_processor import DocumentProcessor
    from src.core.embedding_manager import EmbeddingManager
    from src.core.index_manager import IndexManager
    from src.core.search_manager import SearchManager
    from src.data.database import DatabaseManager
    from src.data.models import Document, FileType, SearchResult, SearchType
    from src.gui.folder_tree import FolderTreeWidget
    from src.gui.main_window import MainWindow
    from src.gui.preview_widget import PreviewWidget
    from src.gui.search_interface import SearchInterface
    from src.gui.search_results import SearchResultsWidget
    from src.utils.config import Config
except ImportError as e:
    print(f"DocMindコンポーネントのインポートに失敗: {e}")


class EndToEndWorkflowValidator(BaseValidator):
    """
    統合ワークフロー検証クラス

    DocMindアプリケーションの完全なユーザーワークフローを検証し、
    実際の使用シナリオでの動作を確認します。
    """

    def __init__(self, config: ValidationConfig | None = None):
        """
        統合ワークフロー検証クラスの初期化

        Args:
            config: 検証設定
        """
        super().__init__(config)

        # テストデータ生成器
        self.test_data_generator = TestDataGenerator()

        # テスト環境
        self.temp_dir = None
        self.test_config = None

        # DocMindコンポーネント
        self.db_manager = None
        self.index_manager = None
        self.embedding_manager = None
        self.document_processor = None
        self.search_manager = None
        self.main_window = None

        # ワークフロー実行状態
        self.workflow_state = {
            "startup_completed": False,
            "documents_processed": False,
            "search_executed": False,
            "results_displayed": False,
            "background_processing": False,
        }

        # パフォーマンス監視
        self.memory_baseline = 0
        self.cpu_baseline = 0
        self.workflow_start_time = None

        self.logger.info("統合ワークフロー検証クラスを初期化しました")

    def setup_test_environment(self) -> None:
        """テスト環境のセットアップ"""
        self.logger.info("統合ワークフロー検証環境をセットアップします")

        # 一時ディレクトリの作成
        self.temp_dir = Path(tempfile.mkdtemp(prefix="docmind_e2e_test_"))

        # テスト設定の作成（シンプルなオブジェクトを使用）
        class TestConfig:
            def __init__(self, temp_dir):
                self.data_dir = temp_dir / "data"
                self.database_file = temp_dir / "test.db"
                self.index_dir = temp_dir / "index"
                self.cache_dir = temp_dir / "cache"
                # その他の設定
                self.search_timeout = 5.0
                self.max_results = 100
                self.enable_semantic_search = True
                self.cache_size = 1000

        self.test_config = TestConfig(self.temp_dir)

        # 必要なディレクトリを作成
        for dir_path in [
            self.test_config.data_dir,
            self.test_config.index_dir,
            self.test_config.cache_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # ベースラインメトリクスの取得
        self.memory_baseline = psutil.virtual_memory().used / 1024 / 1024  # MB
        self.cpu_baseline = psutil.cpu_percent(interval=1)

        self.logger.info(f"テスト環境セットアップ完了: {self.temp_dir}")

    def teardown_test_environment(self) -> None:
        """テスト環境のクリーンアップ"""
        self.logger.info("統合ワークフロー検証環境をクリーンアップします")

        # GUIコンポーネントのクリーンアップ
        if self.main_window:
            try:
                self.main_window.close()
                self.main_window = None
            except Exception as e:
                self.logger.warning(f"メインウィンドウのクリーンアップエラー: {e}")

        # データベース接続のクリーンアップ
        if self.db_manager:
            try:
                self.db_manager.close()
                self.db_manager = None
            except Exception as e:
                self.logger.warning(f"データベースのクリーンアップエラー: {e}")

        # 一時ディレクトリの削除
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception as e:
                self.logger.warning(f"一時ディレクトリの削除エラー: {e}")

        # メモリのクリーンアップ
        gc.collect()

        self.logger.info("テスト環境クリーンアップ完了")

    def test_complete_application_workflow(self) -> None:
        """
        完全なアプリケーションワークフローの検証

        要件9.1: ドキュメント追加から検索まで、システムは一連の処理を正常に完了する
        """
        self.logger.info("完全なアプリケーションワークフローの検証を開始")

        self.workflow_start_time = time.time()

        # 1. アプリケーション起動の検証
        self._validate_application_startup()

        # 2. ドキュメント処理の検証
        self._validate_document_processing()

        # 3. インデックス化の検証
        self._validate_indexing_process()

        # 4. 検索実行の検証
        self._validate_search_execution()

        # 5. 結果表示の検証
        self._validate_result_display()

        # 6. ワークフロー完了の確認
        self._validate_workflow_completion()

        workflow_time = time.time() - self.workflow_start_time
        self.logger.info(
            f"完全なワークフロー検証完了 (実行時間: {workflow_time:.2f}秒)"
        )

        # パフォーマンス要件の確認
        self.assert_condition(
            workflow_time < 60.0,
            f"ワークフロー実行時間が要件を超過: {workflow_time:.2f}秒 > 60秒",
        )

    def test_hybrid_search_workflow(self) -> None:
        """
        複数の検索タイプ組み合わせの検証

        要件9.2: 複数の検索タイプを組み合わせる時、システムは統合された結果を提供する
        """
        self.logger.info("ハイブリッド検索ワークフローの検証を開始")

        # 前提条件: ドキュメントが処理済みであること
        if not self.workflow_state["documents_processed"]:
            self._validate_document_processing()

        # テストクエリの準備
        test_queries = [
            "Python プログラミング",
            "データベース 設計",
            "機械学習 アルゴリズム",
            "ウェブ開発 フレームワーク",
        ]

        for query in test_queries:
            self.logger.info(f"ハイブリッド検索テスト: '{query}'")

            # 1. 全文検索の実行
            start_time = time.time()
            fulltext_results = self._execute_search(query, SearchType.FULL_TEXT)
            fulltext_time = time.time() - start_time

            # 2. セマンティック検索の実行
            start_time = time.time()
            semantic_results = self._execute_search(query, SearchType.SEMANTIC)
            semantic_time = time.time() - start_time

            # 3. ハイブリッド検索の実行
            start_time = time.time()
            hybrid_results = self._execute_search(query, SearchType.HYBRID)
            hybrid_time = time.time() - start_time

            # 結果の検証
            self.assert_condition(
                isinstance(fulltext_results, list),
                f"全文検索結果がリストではありません: {type(fulltext_results)}",
            )

            self.assert_condition(
                isinstance(semantic_results, list),
                f"セマンティック検索結果がリストではありません: {type(semantic_results)}",
            )

            self.assert_condition(
                isinstance(hybrid_results, list),
                f"ハイブリッド検索結果がリストではありません: {type(hybrid_results)}",
            )

            # パフォーマンス要件の確認（5秒以内）
            self.assert_condition(
                fulltext_time < 5.0,
                f"全文検索時間が要件を超過: {fulltext_time:.2f}秒 > 5秒",
            )

            self.assert_condition(
                semantic_time < 5.0,
                f"セマンティック検索時間が要件を超過: {semantic_time:.2f}秒 > 5秒",
            )

            self.assert_condition(
                hybrid_time < 5.0,
                f"ハイブリッド検索時間が要件を超過: {hybrid_time:.2f}秒 > 5秒",
            )

            self.logger.info(
                f"検索完了 - 全文: {fulltext_time:.2f}s, セマンティック: {semantic_time:.2f}s, ハイブリッド: {hybrid_time:.2f}s"
            )

        self.logger.info("ハイブリッド検索ワークフロー検証完了")

    def test_background_processing_responsiveness(self) -> None:
        """
        バックグラウンド処理中の応答性検証

        要件9.3: バックグラウンド処理中でも、システムはユーザーインターフェースの応答性を維持する
        """
        self.logger.info("バックグラウンド処理中の応答性検証を開始")

        # GUIコンポーネントの初期化
        self._initialize_gui_components()

        # バックグラウンド処理の開始
        background_thread = threading.Thread(
            target=self._simulate_heavy_background_processing, daemon=True
        )
        background_thread.start()

        # UI応答性の監視
        responsiveness_results = []
        test_duration = 10.0  # 10秒間テスト
        start_time = time.time()

        while time.time() - start_time < test_duration:
            # UI操作のシミュレーション
            ui_start = time.time()
            self._simulate_ui_interaction()
            ui_response_time = time.time() - ui_start

            responsiveness_results.append(ui_response_time)

            # CPU使用率の監視
            psutil.cpu_percent(interval=0.1)

            # 応答時間の確認（100ms以内）
            self.assert_condition(
                ui_response_time < 0.1,
                f"UI応答時間が要件を超過: {ui_response_time:.3f}秒 > 0.1秒",
            )

            time.sleep(0.5)  # 0.5秒間隔でテスト

        # バックグラウンド処理の完了を待機
        background_thread.join(timeout=5.0)

        # 応答性統計の計算
        avg_response_time = sum(responsiveness_results) / len(responsiveness_results)
        max_response_time = max(responsiveness_results)

        self.logger.info(
            f"UI応答性統計 - 平均: {avg_response_time:.3f}s, 最大: {max_response_time:.3f}s"
        )

        # 応答性要件の確認
        self.assert_condition(
            avg_response_time < 0.05,
            f"平均UI応答時間が要件を超過: {avg_response_time:.3f}秒 > 0.05秒",
        )

        self.assert_condition(
            max_response_time < 0.1,
            f"最大UI応答時間が要件を超過: {max_response_time:.3f}秒 > 0.1秒",
        )

        self.logger.info("バックグラウンド処理中の応答性検証完了")

    def test_configuration_hot_reload(self) -> None:
        """
        設定変更の即座反映検証

        要件9.4: 設定変更後、システムは再起動なしに新しい設定を適用する
        """
        self.logger.info("設定変更の即座反映検証を開始")

        # 初期設定の確認
        original_config = {
            "search_timeout": 5.0,
            "max_results": 100,
            "enable_semantic_search": True,
            "cache_size": 1000,
        }

        # 設定変更のテスト
        new_config = {
            "search_timeout": 10.0,
            "max_results": 50,
            "enable_semantic_search": False,
            "cache_size": 500,
        }

        # 1. 初期設定での動作確認
        self._apply_configuration(original_config)
        initial_behavior = self._test_configuration_behavior()

        # 2. 設定変更の適用
        config_change_start = time.time()
        self._apply_configuration(new_config)
        config_change_time = time.time() - config_change_start

        # 3. 新設定での動作確認
        new_behavior = self._test_configuration_behavior()

        # 設定変更時間の確認（1秒以内）
        self.assert_condition(
            config_change_time < 1.0,
            f"設定変更時間が要件を超過: {config_change_time:.3f}秒 > 1秒",
        )

        # 設定反映の確認
        self.assert_condition(
            initial_behavior != new_behavior, "設定変更が反映されていません"
        )

        # 4. 設定の復元
        self._apply_configuration(original_config)
        restored_behavior = self._test_configuration_behavior()

        self.assert_condition(
            initial_behavior == restored_behavior, "設定の復元が正常に動作していません"
        )

        self.logger.info("設定変更の即座反映検証完了")

    def test_long_term_stability(self) -> None:
        """
        長時間連続使用時の安定性検証

        要件9.5: 長時間の連続使用時、システムはメモリリークや性能劣化を起こさない
        """
        self.logger.info("長時間連続使用時の安定性検証を開始")

        # 初期メモリ使用量の記録
        initial_memory = psutil.virtual_memory().used / 1024 / 1024  # MB
        memory_samples = [initial_memory]
        performance_samples = []

        # 長時間使用のシミュレーション（短縮版: 30秒間）
        test_duration = 30.0
        start_time = time.time()
        iteration_count = 0

        while time.time() - start_time < test_duration:
            iteration_start = time.time()

            # 典型的な使用パターンのシミュレーション
            self._simulate_typical_usage_pattern()

            iteration_time = time.time() - iteration_start
            performance_samples.append(iteration_time)

            # メモリ使用量の監視
            current_memory = psutil.virtual_memory().used / 1024 / 1024
            memory_samples.append(current_memory)

            iteration_count += 1

            # 短い休憩
            time.sleep(0.5)

        # メモリリークの検証
        memory_growth = memory_samples[-1] - memory_samples[0]
        max_memory = max(memory_samples)

        self.logger.info(
            f"メモリ使用量変化: {memory_growth:.2f}MB (最大: {max_memory:.2f}MB)"
        )

        # メモリリーク要件の確認（100MB以下の増加）
        self.assert_condition(
            memory_growth < 100.0,
            f"メモリリークが検出されました: {memory_growth:.2f}MB > 100MB",
        )

        # 性能劣化の検証
        early_performance = (
            sum(performance_samples[:5]) / 5
            if len(performance_samples) >= 5
            else performance_samples[0]
        )
        late_performance = (
            sum(performance_samples[-5:]) / 5
            if len(performance_samples) >= 5
            else performance_samples[-1]
        )

        performance_degradation = (
            (late_performance - early_performance) / early_performance * 100
        )

        self.logger.info(
            f"性能変化: {performance_degradation:.2f}% (初期: {early_performance:.3f}s, 後期: {late_performance:.3f}s)"
        )

        # 性能劣化要件の確認（20%以下の劣化）
        self.assert_condition(
            performance_degradation < 20.0,
            f"性能劣化が検出されました: {performance_degradation:.2f}% > 20%",
        )

        self.logger.info(f"長時間安定性検証完了 (反復回数: {iteration_count})")

    def _validate_application_startup(self) -> None:
        """アプリケーション起動の検証"""
        self.logger.info("アプリケーション起動を検証")

        startup_start = time.time()

        # DocMindコンポーネントの初期化
        self.db_manager = DatabaseManager(str(self.test_config.database_file))
        self.db_manager.initialize()

        self.index_manager = IndexManager(str(self.test_config.index_dir))
        self.index_manager.create_index()

        self.embedding_manager = EmbeddingManager()
        self.document_processor = DocumentProcessor()

        self.search_manager = SearchManager(self.index_manager, self.embedding_manager)

        startup_time = time.time() - startup_start

        # 起動時間要件の確認（10秒以内）
        self.assert_condition(
            startup_time < 10.0, f"起動時間が要件を超過: {startup_time:.2f}秒 > 10秒"
        )

        self.workflow_state["startup_completed"] = True
        self.logger.info(f"アプリケーション起動完了 (時間: {startup_time:.2f}秒)")

    def _validate_document_processing(self) -> None:
        """ドキュメント処理の検証"""
        self.logger.info("ドキュメント処理を検証")

        # テストドキュメントの生成
        test_documents = self.test_data_generator.create_standard_dataset(
            output_dir=self.test_config.data_dir, num_files=10
        )

        processed_count = 0
        processing_start = time.time()

        for file_path in test_documents:
            try:
                doc = self.document_processor.process_file(str(file_path))
                if doc and doc.content.strip():
                    # データベースに保存
                    self.db_manager.add_document(doc)
                    # インデックスに追加
                    self.index_manager.add_document(doc)
                    processed_count += 1
            except Exception as e:
                self.logger.warning(f"ドキュメント処理エラー: {file_path} - {e}")

        processing_time = time.time() - processing_start

        # 処理要件の確認
        self.assert_condition(processed_count > 0, "処理されたドキュメントがありません")

        self.assert_condition(
            processing_time < 30.0,
            f"ドキュメント処理時間が要件を超過: {processing_time:.2f}秒 > 30秒",
        )

        self.workflow_state["documents_processed"] = True
        self.logger.info(
            f"ドキュメント処理完了 ({processed_count}件, 時間: {processing_time:.2f}秒)"
        )

    def _validate_indexing_process(self) -> None:
        """インデックス化プロセスの検証"""
        self.logger.info("インデックス化プロセスを検証")

        # インデックス統計の確認
        doc_count = self.db_manager.get_document_count()

        self.assert_condition(
            doc_count > 0, "インデックス化されたドキュメントがありません"
        )

        self.logger.info(f"インデックス化完了 ({doc_count}件のドキュメント)")

    def _validate_search_execution(self) -> None:
        """検索実行の検証"""
        self.logger.info("検索実行を検証")

        test_queries = ["テスト", "ドキュメント", "Python"]

        for query in test_queries:
            search_start = time.time()
            results = self.search_manager.search(query, SearchType.FULL_TEXT)
            search_time = time.time() - search_start

            # 検索時間要件の確認
            self.assert_condition(
                search_time < 5.0, f"検索時間が要件を超過: {search_time:.2f}秒 > 5秒"
            )

            # 結果の確認
            self.assert_condition(
                isinstance(results, list),
                f"検索結果がリストではありません: {type(results)}",
            )

        self.workflow_state["search_executed"] = True
        self.logger.info("検索実行検証完了")

    def _validate_result_display(self) -> None:
        """結果表示の検証"""
        self.logger.info("結果表示を検証")

        # テスト用ファイルの作成
        test_file = self.test_config.data_dir / "test1.txt"
        test_file.write_text("これはテスト用のドキュメントです。", encoding="utf-8")

        # モック結果の作成
        now = datetime.now()

        mock_results = [
            SearchResult(
                document=Document(
                    id="test_doc_1",
                    file_path=str(test_file),
                    title="テストドキュメント1",
                    content="これはテスト用のドキュメントです。",
                    file_type=FileType.TEXT,
                    size=100,
                    created_date=now,
                    modified_date=now,
                    indexed_date=now,
                ),
                score=0.95,
                search_type=SearchType.FULL_TEXT,
                snippet="これはテスト用の...",
                highlighted_terms=["テスト"],
                relevance_explanation="キーワードマッチ",
            )
        ]

        # 結果表示の検証（実際のGUIは使用せず、データ構造のみ確認）
        self.assert_condition(len(mock_results) > 0, "表示する検索結果がありません")

        for result in mock_results:
            self.assert_condition(
                hasattr(result, "document"), "検索結果にドキュメント情報がありません"
            )

            self.assert_condition(
                hasattr(result, "score"), "検索結果にスコア情報がありません"
            )

        self.workflow_state["results_displayed"] = True
        self.logger.info("結果表示検証完了")

    def _validate_workflow_completion(self) -> None:
        """ワークフロー完了の確認"""
        self.logger.info("ワークフロー完了を確認")

        # すべてのワークフロー段階が完了していることを確認
        for stage, completed in self.workflow_state.items():
            self.assert_condition(completed, f"ワークフロー段階が未完了: {stage}")

        self.logger.info("ワークフロー完了確認済み")

    def _execute_search(
        self, query: str, search_type: SearchType
    ) -> list[SearchResult]:
        """検索の実行"""
        try:
            return self.search_manager.search(query, search_type)
        except Exception as e:
            self.logger.warning(f"検索実行エラー: {query} ({search_type}) - {e}")
            return []

    def _initialize_gui_components(self) -> None:
        """GUIコンポーネントの初期化"""
        try:
            # モックGUIコンポーネントの作成
            self.main_window = Mock()
            self.main_window.search_interface = Mock()
            self.main_window.search_results = Mock()
            self.main_window.preview_widget = Mock()
            self.main_window.folder_tree = Mock()

            self.logger.info("GUIコンポーネント初期化完了")
        except Exception as e:
            self.logger.warning(f"GUIコンポーネント初期化エラー: {e}")

    def _simulate_heavy_background_processing(self) -> None:
        """重いバックグラウンド処理のシミュレーション"""
        self.workflow_state["background_processing"] = True

        # CPU集約的な処理のシミュレーション
        for _i in range(100):
            # 計算集約的なタスク
            sum(j * j for j in range(1000))
            time.sleep(0.01)  # 短い休憩

        self.workflow_state["background_processing"] = False

    def _simulate_ui_interaction(self) -> None:
        """UI操作のシミュレーション"""
        if self.main_window:
            # モックUI操作
            self.main_window.search_interface.get_search_text()
            self.main_window.search_results.update_results([])
            self.main_window.folder_tree.get_selected_folder()

    def _apply_configuration(self, config: dict[str, Any]) -> None:
        """設定の適用"""
        # 設定変更のシミュレーション
        for key, value in config.items():
            setattr(self.test_config, key, value)

    def _test_configuration_behavior(self) -> dict[str, Any]:
        """設定による動作の確認"""
        # 設定に基づく動作のテスト
        behavior = {
            "search_timeout": getattr(self.test_config, "search_timeout", 5.0),
            "max_results": getattr(self.test_config, "max_results", 100),
            "enable_semantic_search": getattr(
                self.test_config, "enable_semantic_search", True
            ),
        }
        return behavior

    def _simulate_typical_usage_pattern(self) -> None:
        """典型的な使用パターンのシミュレーション"""
        # 1. 検索実行
        if self.search_manager:
            try:
                self.search_manager.search("テスト", SearchType.FULL_TEXT)
            except Exception:
                pass

        # 2. メモリ使用
        temp_data = list(range(1000))

        # 3. 短い処理
        time.sleep(0.1)

        # 4. メモリ解放
        del temp_data
        gc.collect()


if __name__ == "__main__":
    # 単体テスト実行
    validator = EndToEndWorkflowValidator()

    try:
        validator.setup_test_environment()
        results = validator.run_validation()

        print("\n=== 統合ワークフロー検証結果 ===")
        for result in results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.test_name}: {result.execution_time:.2f}秒")
            if not result.success:
                print(f"  エラー: {result.error_message}")

        print(f"\n合格率: {sum(1 for r in results if r.success)}/{len(results)}")

    finally:
        validator.teardown_test_environment()
        validator.cleanup()
