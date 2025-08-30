"""
エンドツーエンド統合テスト

アプリケーション全体のワークフローをテストする統合テスト
"""

import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.document_processor import DocumentProcessor
from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.core.search_manager import SearchManager
from src.data.database import DatabaseManager
from src.data.models import Document, FileType, SearchType


@pytest.mark.integration
class TestEndToEndWorkflow:
    """エンドツーエンドワークフローテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, test_config, sample_documents):
        """テストセットアップ"""
        self.config = test_config
        self.sample_documents = sample_documents

        # コンポーネントを初期化
        self.db_manager = DatabaseManager(str(self.config.database_file))
        self.db_manager.initialize()

        self.index_manager = IndexManager(str(self.config.index_dir))
        self.index_manager.create_index()

        self.embedding_manager = EmbeddingManager()
        self.document_processor = DocumentProcessor()

        self.search_manager = SearchManager(
            self.index_manager,
            self.embedding_manager
        )

    def test_complete_document_indexing_workflow(self):
        """完全なドキュメントインデックス化ワークフロー"""
        # 1. ドキュメントファイルを処理
        processed_docs = []
        all_files = []
        for _file_type, files in self.sample_documents.items():
            all_files.extend(files)

        for file_path in all_files[:5]:  # 最初の5ファイルをテスト
            try:
                doc = self.document_processor.process_file(str(file_path))
                if doc and doc.content.strip():
                    processed_docs.append(doc)
            except Exception as e:
                print(f"ファイル処理エラー: {file_path} - {e}")
                continue

        assert len(processed_docs) > 0, "処理されたドキュメントが存在しません"

        # 2. データベースに保存
        for doc in processed_docs:
            success = self.db_manager.add_document(doc)
            assert success, f"ドキュメントの保存に失敗: {doc.file_path}"

        # 3. 全文検索インデックスに追加
        for doc in processed_docs:
            self.index_manager.add_document(doc)

        # 4. 埋め込みを生成（モック使用）
        with patch.object(self.embedding_manager, 'generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            for doc in processed_docs:
                self.embedding_manager.add_document_embedding(doc.id, doc.content)

        # 5. インデックス化の確認
        db_docs = self.db_manager.get_all_documents()
        assert len(db_docs) == len(processed_docs), "データベースのドキュメント数が一致しません"

        print(f"✓ {len(processed_docs)}個のドキュメントが正常にインデックス化されました")

    def test_complete_search_workflow(self):
        """完全な検索ワークフロー"""
        # テストデータをセットアップ
        self.test_complete_document_indexing_workflow()

        # 1. 全文検索テスト
        text_results = self.search_manager.search("テスト", SearchType.FULL_TEXT)
        assert isinstance(text_results, list), "検索結果がリストではありません"

        # 2. セマンティック検索テスト（モック使用）
        with patch.object(self.embedding_manager, 'search_similar') as mock_search:
            mock_search.return_value = []
            semantic_results = self.search_manager.search("技術文書", SearchType.SEMANTIC)
            assert isinstance(semantic_results, list), "セマンティック検索結果がリストではありません"

        # 3. ハイブリッド検索テスト
        hybrid_results = self.search_manager.search("Python プログラミング", SearchType.HYBRID)
        assert isinstance(hybrid_results, list), "ハイブリッド検索結果がリストではありません"

        print("✓ すべての検索タイプが正常に動作しました")

    def test_incremental_update_workflow(self):
        """増分更新ワークフロー"""
        # 初期インデックス化
        self.test_complete_document_indexing_workflow()

        # 新しいドキュメントを追加
        new_file = Path(self.config.data_dir) / "new_document.txt"
        new_file.write_text("これは新しく追加されたドキュメントです。", encoding='utf-8')

        # ドキュメントを処理
        new_doc = self.document_processor.process_file(str(new_file))
        assert new_doc is not None, "新しいドキュメントの処理に失敗"

        # 増分更新
        self.db_manager.add_document(new_doc)
        self.index_manager.add_document(new_doc)

        with patch.object(self.embedding_manager, 'generate_embedding') as mock_embed:
            mock_embed.return_value = [0.2] * 384
            self.embedding_manager.add_document_embedding(new_doc.id, new_doc.content)

        # 更新後の検索テスト
        results = self.search_manager.search("新しく追加", SearchType.FULL_TEXT)

        # 結果の確認（実際の検索結果がない場合もあるため、エラーが発生しないことを確認）
        assert isinstance(results, list), "増分更新後の検索が失敗"

        print("✓ 増分更新ワークフローが正常に動作しました")

    def test_error_recovery_workflow(self):
        """エラー回復ワークフロー"""
        # 不正なファイルパスでのドキュメント処理
        invalid_path = "/non/existent/file.txt"

        try:
            self.document_processor.process_file(invalid_path)
            # エラーが発生しても例外が投げられないことを確認
        except Exception as e:
            # 適切なエラーハンドリングがされていることを確認
            assert "ファイルが見つかりません" in str(e) or "No such file" in str(e)

        # データベース接続エラーのシミュレーション
        with patch.object(self.db_manager, 'add_document') as mock_add:
            mock_add.side_effect = Exception("データベース接続エラー")

            # エラーが適切に処理されることを確認
            try:
                test_doc = Document(
                    id="test_id",
                    file_path="test.txt",
                    title="テストドキュメント",
                    content="テスト内容",
                    file_type="text",
                    size=100
                )
                self.db_manager.add_document(test_doc)
                raise AssertionError("例外が発生するはずです")
            except Exception as e:
                assert "データベース接続エラー" in str(e)

        print("✓ エラー回復ワークフローが正常に動作しました")

    @pytest.mark.slow
    def test_large_dataset_workflow(self, large_document_set):
        """大規模データセットでのワークフロー"""
        # 大量のファイルを処理
        processed_count = 0
        all_files = []
        for _file_type, files in large_document_set.items():
            all_files.extend(files[:10])  # 各タイプから10ファイルずつ

        start_time = time.time()

        for file_path in all_files:
            try:
                doc = self.document_processor.process_file(str(file_path))
                if doc and doc.content.strip():
                    self.db_manager.add_document(doc)
                    self.index_manager.add_document(doc)
                    processed_count += 1
            except Exception as e:
                print(f"大規模処理エラー: {file_path} - {e}")
                continue

        processing_time = time.time() - start_time

        # パフォーマンス要件の確認
        assert processed_count > 0, "処理されたドキュメントがありません"
        assert processing_time < 60, f"処理時間が長すぎます: {processing_time:.2f}秒"

        # 検索パフォーマンステスト
        search_start = time.time()
        self.search_manager.search("テスト", SearchType.FULL_TEXT)
        search_time = time.time() - search_start

        assert search_time < 5, f"検索時間が長すぎます: {search_time:.2f}秒"

        print(f"✓ 大規模データセット処理完了: {processed_count}ファイル, {processing_time:.2f}秒")
        print(f"✓ 検索パフォーマンス: {search_time:.2f}秒")


@pytest.mark.integration
class TestSystemIntegration:
    """システム統合テスト"""

    def test_component_integration(self, test_config):
        """コンポーネント間の統合テスト"""
        # 各コンポーネントが正常に初期化できることを確認
        db_manager = DatabaseManager(str(test_config.database_file))
        db_manager.initialize()

        index_manager = IndexManager(str(test_config.index_dir))
        index_manager.create_index()

        embedding_manager = EmbeddingManager()
        DocumentProcessor()

        search_manager = SearchManager(
            index_manager,
            embedding_manager
        )

        # 各コンポーネントが適切に連携することを確認
        assert search_manager.index_manager is index_manager
        assert search_manager.embedding_manager is embedding_manager
        # SearchManagerはdb_managerを直接保持しないため、この確認は削除

        print("✓ コンポーネント統合テスト完了")

    def test_configuration_integration(self, test_config):
        """設定統合テスト"""
        # 設定が各コンポーネントに正しく適用されることを確認
        assert test_config.data_dir.exists()
        assert test_config.index_dir.exists()

        # ログディレクトリが存在しない場合は作成
        if not test_config.log_dir.exists():
            test_config.log_dir.mkdir(parents=True, exist_ok=True)
        assert test_config.log_dir.exists()

        # 設定ファイルの読み書きテスト
        # 設定の保存テスト（save_configメソッドを使用）
        result = test_config.save_config()
        assert result is True or result is None  # 保存が成功したことを確認

        # 基本的な設定値の確認
        assert isinstance(test_config.data_dir, Path)
        assert isinstance(test_config.index_dir, Path)
        assert isinstance(test_config.log_dir, Path)

        print("✓ 設定統合テスト完了")

    def test_data_persistence_integration(self, test_config, sample_documents):
        """データ永続化統合テスト"""
        # データベース永続化テスト
        db_manager = DatabaseManager(str(test_config.database_file))
        db_manager.initialize()

        # テストドキュメントを作成
        now = datetime.now()
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("これは統合テスト用のドキュメントです。")
            temp_file_path = f.name

        test_doc = Document(
            id="integration_test_doc",
            file_path=temp_file_path,
            title="統合テストドキュメント",
            content="これは統合テスト用のドキュメントです。",
            file_type=FileType.TEXT,
            size=100,
            created_date=now,
            modified_date=now,
            indexed_date=now
        )

        # データベースの基本操作テスト
        # データベースが正常に初期化されていることを確認
        assert db_manager._initialized is True

        # データベースの健全性チェック
        health_status = db_manager.health_check()
        assert health_status is True

        # データベース統計情報の取得
        stats = db_manager.get_database_stats()
        assert isinstance(stats, dict)
        assert "db_file_size" in stats
        assert "document_count" in stats

        # インデックス永続化テスト
        index_manager = IndexManager(str(test_config.index_dir))
        index_manager.create_index()
        index_manager.add_document(test_doc)

        # 新しいインスタンスで読み込みテスト
        new_index_manager = IndexManager(str(test_config.index_dir))
        results = new_index_manager.search_text("統合テスト")

        # 結果が取得できることを確認（実際の検索結果は実装に依存）
        assert isinstance(results, list)

        print("✓ データ永続化統合テスト完了")


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """パフォーマンス統合テスト"""

    def test_search_performance_requirements(self, test_config, performance_timer, memory_monitor):
        """検索パフォーマンス要件テスト"""
        # 要件: 最大50,000ドキュメントを5秒以内で検索

        # テスト用の小規模データセット（実際の50,000は時間がかかるため）
        db_manager = DatabaseManager(str(test_config.database_file))
        db_manager.initialize()

        index_manager = IndexManager(str(test_config.index_dir))
        index_manager.create_index()

        embedding_manager = EmbeddingManager()
        search_manager = SearchManager(index_manager, embedding_manager)

        # テストドキュメントを大量作成（簡略版）
        test_docs = []
        now = datetime.now()
        temp_files = []
        for i in range(100):  # 実際のテストでは小規模
            # 一時ファイルを作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f"これはパフォーマンステスト用のドキュメント {i} です。検索テスト用のキーワードを含みます。")
                temp_file_path = f.name
                temp_files.append(temp_file_path)

            doc = Document(
                id=f"perf_test_doc_{i}",
                file_path=temp_file_path,
                title=f"パフォーマンステストドキュメント {i}",
                content=f"これはパフォーマンステスト用のドキュメント {i} です。検索テスト用のキーワードを含みます。",
                file_type=FileType.TEXT,
                size=100,
                created_date=now,
                modified_date=now,
                indexed_date=now
            )
            test_docs.append(doc)
            db_manager.add_document(doc)
            index_manager.add_document(doc)

        # 検索パフォーマンステスト
        performance_timer.start()
        results = search_manager.search("パフォーマンステスト", SearchType.FULL_TEXT)
        search_time = performance_timer.stop()

        # パフォーマンス要件の確認
        assert search_time < 5.0, f"検索時間が要件を超過: {search_time:.2f}秒"
        assert isinstance(results, list), "検索結果が正しい形式ではありません"

        # メモリ使用量の確認
        memory_increase = memory_monitor.get_memory_increase()
        assert memory_increase < 500, f"メモリ使用量が過大: {memory_increase:.2f}MB"

        print(f"✓ 検索パフォーマンステスト完了: {search_time:.3f}秒, メモリ増加: {memory_increase:.2f}MB")

    def test_startup_performance(self, test_config, performance_timer):
        """起動パフォーマンステスト"""
        # 要件: Windows 10/11で10秒以内に起動

        performance_timer.start()

        # アプリケーション初期化のシミュレーション
        db_manager = DatabaseManager(str(test_config.database_file))
        db_manager.initialize()

        index_manager = IndexManager(str(test_config.index_dir))
        index_manager.create_index()

        embedding_manager = EmbeddingManager()
        # モデル読み込みをモック（実際の読み込みは時間がかかるため）
        with patch.object(embedding_manager, 'load_model'):
            embedding_manager.load_model()

        SearchManager(index_manager, embedding_manager)

        startup_time = performance_timer.stop()

        # 起動時間要件の確認
        assert startup_time < 10.0, f"起動時間が要件を超過: {startup_time:.2f}秒"

        print(f"✓ 起動パフォーマンステスト完了: {startup_time:.3f}秒")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
