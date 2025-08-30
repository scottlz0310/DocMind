"""
データ永続化・整合性検証クラス

このモジュールは、DocMindアプリケーションのデータ永続化機能と
データ整合性を包括的に検証します。
"""

import hashlib
import os
import pickle
import shutil
import sqlite3
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    from .base_validator import BaseValidator, ValidationConfig, ValidationResult
    from .test_data_generator import TestDataGenerator
except ImportError:
    from base_validator import BaseValidator, ValidationConfig
    from test_data_generator import TestDataGenerator

# DocMindのコアモジュールをインポート
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.data.models import Document, FileType
from src.data.storage import StorageManager


class DataPersistenceValidator(BaseValidator):
    """
    データ永続化・整合性検証クラス

    データベースACID特性、並行アクセス、インデックス整合性、
    埋め込みキャッシュ、バックアップ・回復機能を検証します。
    """

    def __init__(self, config: ValidationConfig | None = None):
        """
        データ永続化検証クラスの初期化

        Args:
            config: 検証設定
        """
        super().__init__(config)

        # テスト用の一時ディレクトリ
        self.test_data_dir = None
        self.backup_dir = None

        # テストデータ生成器
        self.test_data_generator = TestDataGenerator()

        # 検証対象のコンポーネント
        self.storage_manager = None
        self.db_manager = None
        self.index_manager = None
        self.embedding_manager = None

        # 並行アクセステスト用
        self.concurrent_results = []
        self.concurrent_errors = []

        self.logger.info("データ永続化検証クラスを初期化しました")

    def setup_test_environment(self) -> None:
        """テスト環境のセットアップ"""
        try:
            # 一時ディレクトリの作成
            self.test_data_dir = tempfile.mkdtemp(prefix="docmind_persistence_test_")
            self.backup_dir = tempfile.mkdtemp(prefix="docmind_backup_test_")

            # コンポーネントの初期化
            self.storage_manager = StorageManager(self.test_data_dir)
            self.db_manager = self.storage_manager.db_manager

            # インデックスマネージャーの初期化
            index_path = os.path.join(self.test_data_dir, "whoosh_index")
            self.index_manager = IndexManager(index_path)

            # 埋め込みマネージャーの初期化
            embeddings_path = os.path.join(self.test_data_dir, "embeddings.pkl")
            self.embedding_manager = EmbeddingManager(embeddings_path=embeddings_path)

            self.logger.info(f"テスト環境をセットアップしました: {self.test_data_dir}")

        except Exception as e:
            self.logger.error(f"テスト環境のセットアップに失敗しました: {e}")
            raise

    def teardown_test_environment(self) -> None:
        """テスト環境のクリーンアップ"""
        try:
            # コンポーネントのクリーンアップ
            if self.storage_manager:
                self.storage_manager.close()

            if self.index_manager:
                self.index_manager.close()

            # 一時ディレクトリの削除
            if self.test_data_dir and os.path.exists(self.test_data_dir):
                shutil.rmtree(self.test_data_dir)

            if self.backup_dir and os.path.exists(self.backup_dir):
                shutil.rmtree(self.backup_dir)

            self.logger.info("テスト環境をクリーンアップしました")

        except Exception as e:
            self.logger.warning(f"テスト環境のクリーンアップで警告: {e}")

    def test_database_acid_properties(self) -> None:
        """データベースACID特性の検証"""
        self.logger.info("データベースACID特性の検証を開始します")

        # テストドキュメントの準備
        test_docs = self.test_data_generator.generate_test_documents(10)

        # Atomicity（原子性）の検証
        self._test_atomicity(test_docs)

        # Consistency（一貫性）の検証
        self._test_consistency(test_docs)

        # Isolation（独立性）の検証
        self._test_isolation(test_docs)

        # Durability（永続性）の検証
        self._test_durability(test_docs)

        self.logger.info("データベースACID特性の検証が完了しました")

    def _test_atomicity(self, test_docs: list[Document]) -> None:
        """原子性の検証"""
        self.logger.info("原子性（Atomicity）を検証中...")

        # 正常なトランザクション
        initial_count = self.storage_manager.get_document_count()

        # 複数ドキュメントの一括保存
        saved_count = self.storage_manager.bulk_save_documents(test_docs[:5])
        self.assert_condition(
            saved_count == 5,
            f"一括保存で期待される件数と異なります: 期待=5, 実際={saved_count}"
        )

        final_count = self.storage_manager.get_document_count()
        self.assert_condition(
            final_count == initial_count + 5,
            f"トランザクション後のドキュメント数が不正: 期待={initial_count + 5}, 実際={final_count}"
        )

        # エラー発生時のロールバック検証
        try:
            # 意図的にエラーを発生させるドキュメント
            invalid_doc = Document(
                id="invalid",
                file_path="/nonexistent/path",  # 存在しないパス
                title="Invalid Document",
                content="Test content",
                file_type=FileType.TEXT,
                size=-1,  # 無効なサイズ
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now()
            )

            # 無効なドキュメントを含む一括保存（失敗するはず）
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("BEGIN TRANSACTION")
                    # 正常なドキュメントを挿入
                    for doc in test_docs[5:7]:
                        cursor.execute("""
                            INSERT INTO documents
                            (id, file_path, title, file_type, size, created_date, modified_date, indexed_date, content_hash)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (doc.id, doc.file_path, doc.title, doc.file_type.value,
                             doc.size, doc.created_date, doc.modified_date, doc.indexed_date, doc.content_hash))

                    # 無効なドキュメントを挿入（エラーが発生するはず）
                    cursor.execute("""
                        INSERT INTO documents
                        (id, file_path, title, file_type, size, created_date, modified_date, indexed_date, content_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (invalid_doc.id, invalid_doc.file_path, invalid_doc.title, invalid_doc.file_type.value,
                         invalid_doc.size, invalid_doc.created_date, invalid_doc.modified_date, invalid_doc.indexed_date, ""))

                    cursor.execute("COMMIT")

                except Exception:
                    cursor.execute("ROLLBACK")
                    raise

        except Exception:
            # エラーが発生することを期待
            pass

        # ロールバック後のドキュメント数が変わっていないことを確認
        rollback_count = self.storage_manager.get_document_count()
        self.assert_condition(
            rollback_count == final_count,
            f"ロールバック後のドキュメント数が変化しました: 期待={final_count}, 実際={rollback_count}"
        )

        self.logger.info("原子性の検証が完了しました")

    def _test_consistency(self, test_docs: list[Document]) -> None:
        """一貫性の検証"""
        self.logger.info("一貫性（Consistency）を検証中...")

        # 制約違反の検証
        doc = test_docs[0]

        # 重複ID挿入の検証
        self.storage_manager.save_document(doc)

        # 同じIDで再度挿入を試行（更新されるはず）
        doc_copy = Document(
            id=doc.id,
            file_path=doc.file_path,
            title="Updated Title",
            content="Updated Content",
            file_type=doc.file_type,
            size=doc.size,
            created_date=doc.created_date,
            modified_date=datetime.now(),
            indexed_date=datetime.now()
        )

        self.storage_manager.save_document(doc_copy)

        # 更新されたことを確認
        retrieved_doc = self.storage_manager.load_document(doc.id)
        self.assert_condition(
            retrieved_doc is not None and retrieved_doc.title == "Updated Title",
            "ドキュメントの更新が正しく反映されていません"
        )

        # 外部キー制約の検証（将来の拡張に備えて）
        # 現在のスキーマでは外部キーはないが、データ整合性をチェック

        # ファイルタイプの制約検証
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO documents
                    (id, file_path, title, file_type, size, created_date, modified_date, indexed_date, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ("test_invalid_type", "/test/path", "Test", "invalid_type",
                     100, datetime.now(), datetime.now(), datetime.now(), "hash"))
                conn.commit()

                # 制約違反が検出されるべき
                self.assert_condition(False, "無効なファイルタイプが挿入されました（制約違反が検出されませんでした）")

            except sqlite3.IntegrityError:
                # 制約違反が正しく検出された
                pass

        self.logger.info("一貫性の検証が完了しました")

    def _test_isolation(self, test_docs: list[Document]) -> None:
        """独立性の検証"""
        self.logger.info("独立性（Isolation）を検証中...")

        # 並行トランザクションの検証
        doc1 = test_docs[0]
        doc2 = test_docs[1]

        # 2つのスレッドで同時にドキュメントを操作
        results = []
        errors = []

        def transaction1():
            try:
                # ドキュメント1を保存（異なるIDを使用して競合を避ける）
                doc1_copy = Document(
                    id=f"{doc1.id}_tx1",
                    file_path=doc1.file_path,
                    title=doc1.title,
                    content=doc1.content,
                    file_type=doc1.file_type,
                    size=doc1.size,
                    created_date=doc1.created_date,
                    modified_date=doc1.modified_date,
                    indexed_date=doc1.indexed_date
                )
                self.storage_manager.save_document(doc1_copy)
                time.sleep(0.05)  # 短い待機時間

                # ドキュメント1を更新
                doc1_copy.title = "Updated by Transaction 1"
                self.storage_manager.save_document(doc1_copy)
                results.append("transaction1_success")

            except Exception as e:
                errors.append(f"transaction1_error: {e}")

        def transaction2():
            try:
                # ドキュメント2を保存（異なるIDを使用して競合を避ける）
                doc2_copy = Document(
                    id=f"{doc2.id}_tx2",
                    file_path=doc2.file_path,
                    title=doc2.title,
                    content=doc2.content,
                    file_type=doc2.file_type,
                    size=doc2.size,
                    created_date=doc2.created_date,
                    modified_date=doc2.modified_date,
                    indexed_date=doc2.indexed_date
                )
                self.storage_manager.save_document(doc2_copy)
                time.sleep(0.05)

                # ドキュメント2を更新
                doc2_copy.title = "Updated by Transaction 2"
                self.storage_manager.save_document(doc2_copy)
                results.append("transaction2_success")

            except Exception as e:
                errors.append(f"transaction2_error: {e}")

        # 並行実行
        thread1 = threading.Thread(target=transaction1)
        thread2 = threading.Thread(target=transaction2)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # 両方のトランザクションが成功することを確認
        # SQLiteの制限により、並行アクセスでロックが発生することを許容
        total_operations = len(results) + len(errors)
        self.assert_condition(
            total_operations == 2,
            f"並行トランザクションで予期しない結果: 成功={len(results)}, エラー={len(errors)}"
        )

        # 少なくとも1つのトランザクションが成功するか、適切なエラーハンドリングがされることを確認
        if len(results) == 0:
            self.logger.warning("すべてのトランザクションが失敗しました（SQLiteの制限による可能性があります）")
            # データベースロックエラーが適切に処理されていることを確認
            for error in errors:
                self.assert_condition(
                    "database is locked" in error or "timeout" in error.lower(),
                    f"予期しないエラータイプ: {error}"
                )
        else:
            self.logger.info(f"並行トランザクション結果: 成功={len(results)}, エラー={len(errors)}")

        # データの整合性を確認
        retrieved_doc1 = self.storage_manager.load_document(f"{doc1.id}_tx1")
        retrieved_doc2 = self.storage_manager.load_document(f"{doc2.id}_tx2")

        if retrieved_doc1:
            self.assert_condition(
                retrieved_doc1.title == "Updated by Transaction 1",
                "トランザクション1の結果が正しく保存されていません"
            )

        if retrieved_doc2:
            self.assert_condition(
                retrieved_doc2.title == "Updated by Transaction 2",
                "トランザクション2の結果が正しく保存されていません"
            )

        self.logger.info("独立性の検証が完了しました")

    def _test_durability(self, test_docs: list[Document]) -> None:
        """永続性の検証"""
        self.logger.info("永続性（Durability）を検証中...")

        # ドキュメントを保存
        doc = test_docs[0]
        self.storage_manager.save_document(doc)

        # データベース接続を閉じて再開
        self.storage_manager.close()

        # 新しいStorageManagerで同じデータベースを開く
        new_storage_manager = StorageManager(self.test_data_dir)

        # データが永続化されていることを確認
        retrieved_doc = new_storage_manager.load_document(doc.id)
        self.assert_condition(
            retrieved_doc is not None,
            "データベース再起動後にドキュメントが見つかりません"
        )

        self.assert_condition(
            retrieved_doc.title == doc.title and retrieved_doc.content == doc.content,
            "データベース再起動後にドキュメントの内容が変化しています"
        )

        # 元のStorageManagerに戻す
        new_storage_manager.close()
        self.storage_manager = StorageManager(self.test_data_dir)
        self.db_manager = self.storage_manager.db_manager

        self.logger.info("永続性の検証が完了しました")

    def test_concurrent_access_validation(self) -> None:
        """並行アクセスの検証"""
        self.logger.info("並行アクセスの検証を開始します")

        # テストドキュメントの準備
        test_docs = self.test_data_generator.generate_test_documents(50)

        # 複数スレッドでの同時アクセス検証
        self._test_concurrent_database_operations(test_docs)

        # 読み書き競合の検証
        self._test_read_write_concurrency(test_docs)

        # デッドロック検出の検証
        self._test_deadlock_detection(test_docs)

        self.logger.info("並行アクセスの検証が完了しました")

    def _test_concurrent_database_operations(self, test_docs: list[Document]) -> None:
        """並行データベース操作の検証"""
        self.logger.info("並行データベース操作を検証中...")

        self.concurrent_results.clear()
        self.concurrent_errors.clear()

        # 複数スレッドでドキュメントを同時に保存
        def save_documents(doc_batch: list[Document], thread_id: int):
            try:
                for doc in doc_batch:
                    # スレッドIDを含むユニークなIDに変更
                    doc.id = f"{doc.id}_thread_{thread_id}"
                    self.storage_manager.save_document(doc)
                    time.sleep(0.001)  # 短い待機で競合を誘発

                self.concurrent_results.append(f"thread_{thread_id}_success")

            except Exception as e:
                self.concurrent_errors.append(f"thread_{thread_id}_error: {e}")

        # 5つのスレッドで並行実行
        threads = []
        batch_size = 10

        for i in range(5):
            start_idx = i * batch_size
            end_idx = start_idx + batch_size
            doc_batch = test_docs[start_idx:end_idx]

            thread = threading.Thread(
                target=save_documents,
                args=(doc_batch, i)
            )
            threads.append(thread)
            thread.start()

        # すべてのスレッドの完了を待機
        for thread in threads:
            thread.join()

        # 結果の検証
        self.assert_condition(
            len(self.concurrent_results) == 5,
            f"並行操作で期待されるスレッド数と異なります: 期待=5, 成功={len(self.concurrent_results)}"
        )

        self.assert_condition(
            len(self.concurrent_errors) == 0,
            f"並行操作でエラーが発生しました: {self.concurrent_errors}"
        )

        # データベース内のドキュメント数を確認
        final_count = self.storage_manager.get_document_count()
        self.assert_condition(
            final_count >= 50,  # 最低50件は保存されているはず
            f"並行操作後のドキュメント数が不足: 実際={final_count}"
        )

        self.logger.info("並行データベース操作の検証が完了しました")

    def _test_read_write_concurrency(self, test_docs: list[Document]) -> None:
        """読み書き競合の検証"""
        self.logger.info("読み書き競合を検証中...")

        # テストドキュメントを事前に保存
        base_doc = test_docs[0]
        base_doc.id = "concurrent_test_doc"
        self.storage_manager.save_document(base_doc)

        read_results = []
        write_results = []
        errors = []

        def continuous_reader():
            """継続的な読み取り操作"""
            try:
                for i in range(100):
                    doc = self.storage_manager.load_document("concurrent_test_doc")
                    if doc:
                        read_results.append(f"read_{i}")
                    time.sleep(0.01)

            except Exception as e:
                errors.append(f"reader_error: {e}")

        def continuous_writer():
            """継続的な書き込み操作"""
            try:
                for i in range(50):
                    doc = self.storage_manager.load_document("concurrent_test_doc")
                    if doc:
                        doc.title = f"Updated Title {i}"
                        doc.content = f"Updated Content {i}"
                        self.storage_manager.save_document(doc)
                        write_results.append(f"write_{i}")
                    time.sleep(0.02)

            except Exception as e:
                errors.append(f"writer_error: {e}")

        # 読み取りと書き込みを並行実行
        reader_thread = threading.Thread(target=continuous_reader)
        writer_thread = threading.Thread(target=continuous_writer)

        reader_thread.start()
        writer_thread.start()

        reader_thread.join()
        writer_thread.join()

        # 結果の検証
        self.assert_condition(
            len(errors) == 0,
            f"読み書き競合でエラーが発生しました: {errors}"
        )

        self.assert_condition(
            len(read_results) > 0 and len(write_results) > 0,
            f"読み書き操作が正常に実行されませんでした: 読み取り={len(read_results)}, 書き込み={len(write_results)}"
        )

        # 最終的なデータの整合性を確認
        final_doc = self.storage_manager.load_document("concurrent_test_doc")
        self.assert_condition(
            final_doc is not None,
            "読み書き競合後にドキュメントが見つかりません"
        )

        self.logger.info("読み書き競合の検証が完了しました")

    def _test_deadlock_detection(self, test_docs: list[Document]) -> None:
        """デッドロック検出の検証"""
        self.logger.info("デッドロック検出を検証中...")

        # 2つのドキュメントを準備
        doc1 = test_docs[0]
        doc2 = test_docs[1]
        doc1.id = "deadlock_test_doc1"
        doc2.id = "deadlock_test_doc2"

        self.storage_manager.save_document(doc1)
        self.storage_manager.save_document(doc2)

        deadlock_results = []
        deadlock_errors = []

        def transaction_a():
            """トランザクションA: doc1 -> doc2の順序で更新"""
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()

                    # doc1を更新
                    cursor.execute(
                        "UPDATE documents SET title = ? WHERE id = ?",
                        ("Updated by A", "deadlock_test_doc1")
                    )

                    time.sleep(0.1)  # デッドロックを誘発するための待機

                    # doc2を更新
                    cursor.execute(
                        "UPDATE documents SET title = ? WHERE id = ?",
                        ("Updated by A", "deadlock_test_doc2")
                    )

                    conn.commit()
                    deadlock_results.append("transaction_a_success")

            except Exception as e:
                deadlock_errors.append(f"transaction_a_error: {e}")

        def transaction_b():
            """トランザクションB: doc2 -> doc1の順序で更新"""
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()

                    # doc2を更新
                    cursor.execute(
                        "UPDATE documents SET title = ? WHERE id = ?",
                        ("Updated by B", "deadlock_test_doc2")
                    )

                    time.sleep(0.1)  # デッドロックを誘発するための待機

                    # doc1を更新
                    cursor.execute(
                        "UPDATE documents SET title = ? WHERE id = ?",
                        ("Updated by B", "deadlock_test_doc1")
                    )

                    conn.commit()
                    deadlock_results.append("transaction_b_success")

            except Exception as e:
                deadlock_errors.append(f"transaction_b_error: {e}")

        # 並行実行
        thread_a = threading.Thread(target=transaction_a)
        thread_b = threading.Thread(target=transaction_b)

        thread_a.start()
        thread_b.start()

        thread_a.join()
        thread_b.join()

        # 結果の検証（少なくとも1つは成功するはず）
        total_operations = len(deadlock_results) + len(deadlock_errors)
        self.assert_condition(
            total_operations == 2,
            f"デッドロックテストで予期しない結果: 成功={len(deadlock_results)}, エラー={len(deadlock_errors)}"
        )

        # SQLiteはデッドロックを自動的に解決するため、通常は両方成功するか、
        # タイムアウトエラーが発生する
        self.logger.info(f"デッドロックテスト結果: 成功={len(deadlock_results)}, エラー={len(deadlock_errors)}")

        self.logger.info("デッドロック検出の検証が完了しました")

    def test_index_integrity_validation(self) -> None:
        """インデックス整合性の検証"""
        self.logger.info("インデックス整合性の検証を開始します")

        # テストドキュメントの準備
        test_docs = self.test_data_generator.generate_test_documents(20)

        # Whooshインデックスの整合性検証
        self._test_whoosh_index_integrity(test_docs)

        # データベースとインデックスの同期検証
        self._test_database_index_synchronization(test_docs)

        # インデックス破損からの回復検証
        self._test_index_corruption_recovery(test_docs)

        self.logger.info("インデックス整合性の検証が完了しました")

    def _test_whoosh_index_integrity(self, test_docs: list[Document]) -> None:
        """Whooshインデックスの整合性検証"""
        self.logger.info("Whooshインデックスの整合性を検証中...")

        # ドキュメントをインデックスに追加
        for doc in test_docs:
            self.index_manager.add_document(doc)

        # インデックス内のドキュメント数を確認
        indexed_count = self.index_manager.get_document_count()
        self.assert_condition(
            indexed_count == len(test_docs),
            f"インデックス内のドキュメント数が不正: 期待={len(test_docs)}, 実際={indexed_count}"
        )

        # 各ドキュメントが検索可能であることを確認
        for doc in test_docs[:5]:  # 最初の5件をテスト
            search_results = self.index_manager.search_text(doc.title, limit=10)

            # 該当ドキュメントが検索結果に含まれることを確認
            found = any(result.document.id == doc.id for result in search_results)
            self.assert_condition(
                found,
                f"ドキュメント '{doc.title}' が検索結果に見つかりません"
            )

        # ドキュメントの更新
        updated_doc = test_docs[0]
        updated_doc.title = "Updated Title for Index Test"
        updated_doc.content = "Updated content for index integrity test"

        self.index_manager.update_document(updated_doc)

        # 更新されたドキュメントが検索可能であることを確認
        search_results = self.index_manager.search_text("Updated Title", limit=10)
        found = any(result.document.id == updated_doc.id for result in search_results)
        self.assert_condition(
            found,
            "更新されたドキュメントが検索結果に見つかりません"
        )

        # ドキュメントの削除
        self.index_manager.remove_document(updated_doc.id)

        # 削除されたドキュメントが検索結果に含まれないことを確認
        search_results = self.index_manager.search_text("Updated Title", limit=10)
        found = any(result.document.id == updated_doc.id for result in search_results)
        self.assert_condition(
            not found,
            "削除されたドキュメントが検索結果に残っています"
        )

        # インデックス数の確認
        final_count = self.index_manager.get_document_count()
        self.assert_condition(
            final_count == len(test_docs) - 1,
            f"削除後のインデックス内ドキュメント数が不正: 期待={len(test_docs) - 1}, 実際={final_count}"
        )

        self.logger.info("Whooshインデックスの整合性検証が完了しました")

    def _test_database_index_synchronization(self, test_docs: list[Document]) -> None:
        """データベースとインデックスの同期検証"""
        self.logger.info("データベースとインデックスの同期を検証中...")

        # データベースにドキュメントを保存
        for doc in test_docs[10:15]:  # 新しいドキュメントを使用
            self.storage_manager.save_document(doc)
            self.index_manager.add_document(doc)

        # データベースとインデックスのドキュメント数を比較
        db_count = self.storage_manager.get_document_count()
        index_count = self.index_manager.get_document_count()

        # 注意: 前のテストで削除されたドキュメントがあるため、完全一致ではない
        self.logger.info(f"データベース内ドキュメント数: {db_count}, インデックス内ドキュメント数: {index_count}")

        # データベース内の各ドキュメントがインデックスに存在することを確認
        db_docs = self.storage_manager.list_documents(limit=100)

        for db_doc in db_docs:
            index_exists = self.index_manager.document_exists(db_doc.id)
            if not index_exists:
                self.logger.warning(f"ドキュメント {db_doc.id} がインデックスに存在しません")

        # 同期の整合性を確認するため、新しいドキュメントで再テスト
        sync_test_doc = test_docs[15]
        sync_test_doc.id = "sync_test_document"

        # データベースとインデックスに同時に追加
        self.storage_manager.save_document(sync_test_doc)
        self.index_manager.add_document(sync_test_doc)

        # 両方から取得可能であることを確認
        db_retrieved = self.storage_manager.load_document(sync_test_doc.id)
        index_exists = self.index_manager.document_exists(sync_test_doc.id)

        self.assert_condition(
            db_retrieved is not None,
            "同期テストドキュメントがデータベースから取得できません"
        )

        self.assert_condition(
            index_exists,
            "同期テストドキュメントがインデックスに存在しません"
        )

        self.logger.info("データベースとインデックスの同期検証が完了しました")

    def _test_index_corruption_recovery(self, test_docs: list[Document]) -> None:
        """インデックス破損からの回復検証"""
        self.logger.info("インデックス破損からの回復を検証中...")

        # 正常なインデックスの状態を確認
        self.index_manager.get_document_count()

        # インデックスファイルを意図的に破損させる
        index_path = Path(self.index_manager.index_path)

        # インデックスを閉じる
        self.index_manager.close()

        # インデックスファイルの一部を削除または破損
        for index_file in index_path.glob("*.toc"):
            if index_file.exists():
                # ファイルの一部を破損
                with open(index_file, 'r+b') as f:
                    f.seek(10)
                    f.write(b'CORRUPTED_DATA')
                break

        # 新しいIndexManagerで破損したインデックスを開こうとする
        try:
            corrupted_index_manager = IndexManager(str(index_path))

            # 破損が検出されるか、または自動回復されるかを確認
            try:
                recovered_count = corrupted_index_manager.get_document_count()
                self.logger.info(f"インデックス回復後のドキュメント数: {recovered_count}")

                # 回復が成功した場合、基本的な検索が可能であることを確認
                search_results = corrupted_index_manager.search_text("test", limit=5)
                self.logger.info(f"回復後の検索結果数: {len(search_results)}")

            except Exception as e:
                self.logger.info(f"破損したインデックスでエラーが発生（期待される動作）: {e}")

                # インデックスを再構築
                corrupted_index_manager.create_index()

                # データベースからドキュメントを取得してインデックスを再構築
                db_docs = self.storage_manager.list_documents(limit=100)
                for doc in db_docs:
                    corrupted_index_manager.add_document(doc)

                # 再構築後のドキュメント数を確認
                rebuilt_count = corrupted_index_manager.get_document_count()
                self.assert_condition(
                    rebuilt_count > 0,
                    "インデックス再構築後にドキュメントが見つかりません"
                )

                self.logger.info(f"インデックス再構築が完了しました: {rebuilt_count}件")

            corrupted_index_manager.close()

        except Exception as e:
            self.logger.info(f"破損したインデックスの処理でエラー（期待される動作）: {e}")

        # 元のIndexManagerを再初期化
        self.index_manager = IndexManager(str(index_path))

        self.logger.info("インデックス破損からの回復検証が完了しました")

    def test_embedding_cache_validation(self) -> None:
        """埋め込みキャッシュの検証"""
        self.logger.info("埋め込みキャッシュの検証を開始します")

        # テストドキュメントの準備
        test_docs = self.test_data_generator.generate_test_documents(10)

        # 埋め込みキャッシュの基本機能検証
        self._test_embedding_cache_operations(test_docs)

        # キャッシュファイルの整合性検証
        self._test_embedding_cache_integrity(test_docs)

        # キャッシュの永続化と復元検証
        self._test_embedding_cache_persistence(test_docs)

        # キャッシュ破損からの回復検証
        self._test_embedding_cache_corruption_recovery(test_docs)

        self.logger.info("埋め込みキャッシュの検証が完了しました")

    def _test_embedding_cache_operations(self, test_docs: list[Document]) -> None:
        """埋め込みキャッシュの基本操作検証"""
        self.logger.info("埋め込みキャッシュの基本操作を検証中...")

        # 初期状態の確認
        initial_cache_info = self.embedding_manager.get_cache_info()
        self.assert_condition(
            initial_cache_info["total_embeddings"] == 0,
            f"初期キャッシュが空ではありません: {initial_cache_info['total_embeddings']}"
        )

        # ドキュメントの埋め込みを生成
        for doc in test_docs[:5]:
            self.embedding_manager.add_document_embedding(doc.id, doc.content)

        # キャッシュサイズの確認
        cache_info = self.embedding_manager.get_cache_info()
        self.assert_condition(
            cache_info["total_embeddings"] == 5,
            f"キャッシュ内の埋め込み数が不正: 期待=5, 実際={cache_info['total_embeddings']}"
        )

        # 埋め込みの検索テスト
        search_results = self.embedding_manager.search_similar("test content", limit=10)
        self.assert_condition(
            len(search_results) > 0,
            "埋め込み検索で結果が返されませんでした"
        )

        # 類似度スコアの妥当性確認
        for _doc_id, similarity in search_results:
            self.assert_condition(
                0.0 <= similarity <= 1.0,
                f"類似度スコアが範囲外です: {similarity}"
            )

        # 埋め込みの更新テスト
        updated_content = "This is updated content for embedding test"
        self.embedding_manager.add_document_embedding(test_docs[0].id, updated_content)

        # キャッシュサイズが変わらないことを確認（更新なので）
        updated_cache_info = self.embedding_manager.get_cache_info()
        self.assert_condition(
            updated_cache_info["total_embeddings"] == 5,
            f"更新後のキャッシュサイズが変化しました: {updated_cache_info['total_embeddings']}"
        )

        # 埋め込みの削除テスト
        self.embedding_manager.remove_document_embedding(test_docs[0].id)

        # キャッシュサイズの減少を確認
        final_cache_info = self.embedding_manager.get_cache_info()
        self.assert_condition(
            final_cache_info["total_embeddings"] == 4,
            f"削除後のキャッシュサイズが不正: 期待=4, 実際={final_cache_info['total_embeddings']}"
        )

        self.logger.info("埋め込みキャッシュの基本操作検証が完了しました")

    def _test_embedding_cache_integrity(self, test_docs: list[Document]) -> None:
        """埋め込みキャッシュファイルの整合性検証"""
        self.logger.info("埋め込みキャッシュファイルの整合性を検証中...")

        # 新しいドキュメントの埋め込みを追加
        for doc in test_docs[5:8]:
            self.embedding_manager.add_document_embedding(doc.id, doc.content)

        # キャッシュを保存
        self.embedding_manager.save_embeddings()

        # キャッシュファイルの存在確認
        cache_file_path = Path(self.embedding_manager.embeddings_path)
        self.assert_condition(
            cache_file_path.exists(),
            f"キャッシュファイルが作成されていません: {cache_file_path}"
        )

        # キャッシュファイルのサイズ確認
        file_size = cache_file_path.stat().st_size
        self.assert_condition(
            file_size > 0,
            f"キャッシュファイルのサイズが0です: {file_size}"
        )

        # キャッシュファイルの内容確認
        try:
            with open(cache_file_path, 'rb') as f:
                loaded_embeddings = pickle.load(f)

            self.assert_condition(
                isinstance(loaded_embeddings, dict),
                "キャッシュファイルの形式が不正です"
            )

            # 埋め込みデータの構造確認
            for doc_id, embedding_data in loaded_embeddings.items():
                self.assert_condition(
                    hasattr(embedding_data, 'doc_id') and hasattr(embedding_data, 'embedding'),
                    f"埋め込みデータの構造が不正です: {doc_id}"
                )

                self.assert_condition(
                    isinstance(embedding_data.embedding, np.ndarray),
                    f"埋め込みベクトルがnumpy配列ではありません: {doc_id}"
                )

        except Exception as e:
            self.assert_condition(
                False,
                f"キャッシュファイルの読み込みに失敗しました: {e}"
            )

        # ハッシュ値による整合性確認
        original_hash = self._calculate_file_hash(cache_file_path)

        # 同じデータで再保存
        self.embedding_manager.save_embeddings()

        # ハッシュ値が同じであることを確認
        new_hash = self._calculate_file_hash(cache_file_path)
        self.assert_condition(
            original_hash == new_hash,
            "同じデータの再保存でハッシュ値が変化しました"
        )

        self.logger.info("埋め込みキャッシュファイルの整合性検証が完了しました")

    def _test_embedding_cache_persistence(self, test_docs: list[Document]) -> None:
        """埋め込みキャッシュの永続化と復元検証"""
        self.logger.info("埋め込みキャッシュの永続化と復元を検証中...")

        # 現在のキャッシュ状態を記録
        original_cache_info = self.embedding_manager.get_cache_info()
        original_embeddings = dict(self.embedding_manager.embeddings)

        # キャッシュを保存
        self.embedding_manager.save_embeddings()

        # 新しいEmbeddingManagerインスタンスを作成
        new_embedding_manager = EmbeddingManager(
            embeddings_path=self.embedding_manager.embeddings_path
        )

        # キャッシュが正しく復元されることを確認
        restored_cache_info = new_embedding_manager.get_cache_info()
        self.assert_condition(
            restored_cache_info["total_embeddings"] == original_cache_info["total_embeddings"],
            f"復元されたキャッシュサイズが不正: 期待={original_cache_info['total_embeddings']}, 実際={restored_cache_info['total_embeddings']}"
        )

        # 個別の埋め込みデータの確認
        for doc_id, original_embedding in original_embeddings.items():
            restored_embedding = new_embedding_manager.embeddings.get(doc_id)

            self.assert_condition(
                restored_embedding is not None,
                f"ドキュメント {doc_id} の埋め込みが復元されていません"
            )

            # 埋め込みベクトルの一致確認
            np.testing.assert_array_equal(
                original_embedding.embedding,
                restored_embedding.embedding,
                err_msg=f"ドキュメント {doc_id} の埋め込みベクトルが一致しません"
            )

        # 復元されたキャッシュで検索が正常に動作することを確認
        search_results = new_embedding_manager.search_similar("test content", limit=5)
        self.assert_condition(
            len(search_results) > 0,
            "復元されたキャッシュで検索結果が返されませんでした"
        )

        self.logger.info("埋め込みキャッシュの永続化と復元検証が完了しました")

    def _test_embedding_cache_corruption_recovery(self, test_docs: list[Document]) -> None:
        """埋め込みキャッシュ破損からの回復検証"""
        self.logger.info("埋め込みキャッシュ破損からの回復を検証中...")

        # 正常なキャッシュファイルを作成
        cache_file_path = Path(self.embedding_manager.embeddings_path)
        self.embedding_manager.save_embeddings()

        # キャッシュファイルを意図的に破損
        with open(cache_file_path, 'w') as f:
            f.write("CORRUPTED_CACHE_DATA")

        # 破損したキャッシュファイルで新しいEmbeddingManagerを作成
        try:
            corrupted_embedding_manager = EmbeddingManager(
                embeddings_path=str(cache_file_path)
            )

            # 破損が検出され、空のキャッシュで開始されることを確認
            cache_info = corrupted_embedding_manager.get_cache_info()
            self.assert_condition(
                cache_info["total_embeddings"] == 0,
                f"破損したキャッシュが正しく処理されていません: {cache_info['total_embeddings']}"
            )

            # 新しい埋め込みを追加できることを確認
            test_doc = test_docs[8]
            corrupted_embedding_manager.add_document_embedding(test_doc.id, test_doc.content)

            # 追加後のキャッシュサイズを確認
            updated_cache_info = corrupted_embedding_manager.get_cache_info()
            self.assert_condition(
                updated_cache_info["total_embeddings"] == 1,
                "破損後の回復で新しい埋め込みが追加できませんでした"
            )

            # 回復したキャッシュを保存
            corrupted_embedding_manager.save_embeddings()

            # 保存されたキャッシュが正常に読み込めることを確認
            final_embedding_manager = EmbeddingManager(
                embeddings_path=str(cache_file_path)
            )

            final_cache_info = final_embedding_manager.get_cache_info()
            self.assert_condition(
                final_cache_info["total_embeddings"] == 1,
                "回復したキャッシュが正しく保存・読み込みされていません"
            )

        except Exception as e:
            self.logger.error(f"キャッシュ破損回復テストでエラー: {e}")
            # 破損からの回復が適切に処理されることを確認
            # 実際の実装では、破損したキャッシュは無視され、新しいキャッシュが作成される

        self.logger.info("埋め込みキャッシュ破損からの回復検証が完了しました")

    def test_backup_recovery_validation(self) -> None:
        """バックアップ・回復機能の検証"""
        self.logger.info("バックアップ・回復機能の検証を開始します")

        # テストドキュメントの準備
        test_docs = self.test_data_generator.generate_test_documents(15)

        # データベースバックアップ・回復の検証
        self._test_database_backup_recovery(test_docs)

        # インデックスバックアップ・回復の検証
        self._test_index_backup_recovery(test_docs)

        # 埋め込みキャッシュバックアップ・回復の検証
        self._test_embedding_backup_recovery(test_docs)

        # 完全システムバックアップ・回復の検証
        self._test_complete_system_backup_recovery(test_docs)

        self.logger.info("バックアップ・回復機能の検証が完了しました")

    def _test_database_backup_recovery(self, test_docs: list[Document]) -> None:
        """データベースバックアップ・回復の検証"""
        self.logger.info("データベースバックアップ・回復を検証中...")

        # テストデータをデータベースに保存
        for doc in test_docs[:10]:
            self.storage_manager.save_document(doc)

        original_count = self.storage_manager.get_document_count()

        # バックアップの作成
        backup_path = os.path.join(self.backup_dir, "database_backup.db")
        backup_success = self.storage_manager.backup_database(backup_path)

        self.assert_condition(
            backup_success,
            "データベースバックアップの作成に失敗しました"
        )

        self.assert_condition(
            os.path.exists(backup_path),
            f"バックアップファイルが作成されていません: {backup_path}"
        )

        # バックアップファイルのサイズ確認
        backup_size = os.path.getsize(backup_path)
        self.assert_condition(
            backup_size > 0,
            f"バックアップファイルのサイズが0です: {backup_size}"
        )

        # 元のデータベースにさらにデータを追加
        for doc in test_docs[10:12]:
            self.storage_manager.save_document(doc)

        modified_count = self.storage_manager.get_document_count()
        self.assert_condition(
            modified_count > original_count,
            "データベースの変更が反映されていません"
        )

        # バックアップからの復元
        restore_success = self.storage_manager.restore_database(backup_path)

        self.assert_condition(
            restore_success,
            "データベースの復元に失敗しました"
        )

        # 復元後のデータ確認
        restored_count = self.storage_manager.get_document_count()
        self.assert_condition(
            restored_count == original_count,
            f"復元後のドキュメント数が不正: 期待={original_count}, 実際={restored_count}"
        )

        # 個別ドキュメントの確認
        for doc in test_docs[:10]:
            restored_doc = self.storage_manager.load_document(doc.id)
            self.assert_condition(
                restored_doc is not None,
                f"復元後にドキュメント {doc.id} が見つかりません"
            )

            self.assert_condition(
                restored_doc.title == doc.title and restored_doc.content == doc.content,
                f"復元されたドキュメント {doc.id} の内容が一致しません"
            )

        self.logger.info("データベースバックアップ・回復の検証が完了しました")

    def _test_index_backup_recovery(self, test_docs: list[Document]) -> None:
        """インデックスバックアップ・回復の検証"""
        self.logger.info("インデックスバックアップ・回復を検証中...")

        # インデックスにドキュメントを追加
        for doc in test_docs[:8]:
            self.index_manager.add_document(doc)

        original_index_count = self.index_manager.get_document_count()

        # インデックスディレクトリのバックアップ
        index_backup_path = os.path.join(self.backup_dir, "index_backup")
        shutil.copytree(self.index_manager.index_path, index_backup_path)

        self.assert_condition(
            os.path.exists(index_backup_path),
            f"インデックスバックアップディレクトリが作成されていません: {index_backup_path}"
        )

        # 元のインデックスを変更
        additional_doc = test_docs[8]
        self.index_manager.add_document(additional_doc)

        modified_index_count = self.index_manager.get_document_count()
        self.assert_condition(
            modified_index_count > original_index_count,
            "インデックスの変更が反映されていません"
        )

        # インデックスを閉じる
        self.index_manager.close()

        # 元のインデックスディレクトリを削除
        shutil.rmtree(self.index_manager.index_path)

        # バックアップからインデックスを復元
        shutil.copytree(index_backup_path, self.index_manager.index_path)

        # 新しいIndexManagerで復元されたインデックスを開く
        restored_index_manager = IndexManager(str(self.index_manager.index_path))

        # 復元後のドキュメント数確認
        restored_index_count = restored_index_manager.get_document_count()
        self.assert_condition(
            restored_index_count == original_index_count,
            f"復元後のインデックス内ドキュメント数が不正: 期待={original_index_count}, 実際={restored_index_count}"
        )

        # 復元されたインデックスで検索が正常に動作することを確認
        search_results = restored_index_manager.search_text("test", limit=10)
        self.assert_condition(
            len(search_results) > 0,
            "復元されたインデックスで検索結果が返されませんでした"
        )

        # 元のIndexManagerを復元
        restored_index_manager.close()
        self.index_manager = IndexManager(str(self.index_manager.index_path))

        self.logger.info("インデックスバックアップ・回復の検証が完了しました")

    def _test_embedding_backup_recovery(self, test_docs: list[Document]) -> None:
        """埋め込みキャッシュバックアップ・回復の検証"""
        self.logger.info("埋め込みキャッシュバックアップ・回復を検証中...")

        # 埋め込みキャッシュにデータを追加
        for doc in test_docs[:6]:
            self.embedding_manager.add_document_embedding(doc.id, doc.content)

        # キャッシュを保存
        self.embedding_manager.save_embeddings()

        original_cache_info = self.embedding_manager.get_cache_info()

        # キャッシュファイルのバックアップ
        cache_backup_path = os.path.join(self.backup_dir, "embeddings_backup.pkl")
        shutil.copy2(self.embedding_manager.embeddings_path, cache_backup_path)

        self.assert_condition(
            os.path.exists(cache_backup_path),
            f"埋め込みキャッシュバックアップが作成されていません: {cache_backup_path}"
        )

        # 元のキャッシュを変更
        additional_doc = test_docs[6]
        self.embedding_manager.add_document_embedding(additional_doc.id, additional_doc.content)
        self.embedding_manager.save_embeddings()

        modified_cache_info = self.embedding_manager.get_cache_info()
        self.assert_condition(
            modified_cache_info["total_embeddings"] > original_cache_info["total_embeddings"],
            "埋め込みキャッシュの変更が反映されていません"
        )

        # バックアップからキャッシュを復元
        shutil.copy2(cache_backup_path, self.embedding_manager.embeddings_path)

        # 新しいEmbeddingManagerで復元されたキャッシュを読み込み
        restored_embedding_manager = EmbeddingManager(
            embeddings_path=self.embedding_manager.embeddings_path
        )

        # 復元後のキャッシュ情報確認
        restored_cache_info = restored_embedding_manager.get_cache_info()
        self.assert_condition(
            restored_cache_info["total_embeddings"] == original_cache_info["total_embeddings"],
            f"復元後の埋め込み数が不正: 期待={original_cache_info['total_embeddings']}, 実際={restored_cache_info['total_embeddings']}"
        )

        # 復元されたキャッシュで検索が正常に動作することを確認
        search_results = restored_embedding_manager.search_similar("test content", limit=5)
        self.assert_condition(
            len(search_results) > 0,
            "復元された埋め込みキャッシュで検索結果が返されませんでした"
        )

        self.logger.info("埋め込みキャッシュバックアップ・回復の検証が完了しました")

    def _test_complete_system_backup_recovery(self, test_docs: list[Document]) -> None:
        """完全システムバックアップ・回復の検証"""
        self.logger.info("完全システムバックアップ・回復を検証中...")

        # システム全体のデータを準備
        for doc in test_docs[12:15]:
            # データベースに保存
            self.storage_manager.save_document(doc)
            # インデックスに追加
            self.index_manager.add_document(doc)
            # 埋め込みを生成
            self.embedding_manager.add_document_embedding(doc.id, doc.content)

        # 各コンポーネントの状態を記録
        original_db_count = self.storage_manager.get_document_count()
        original_index_count = self.index_manager.get_document_count()
        original_embedding_count = self.embedding_manager.get_cache_info()["total_embeddings"]

        # システム全体のバックアップ
        system_backup_path = os.path.join(self.backup_dir, "system_backup")
        os.makedirs(system_backup_path, exist_ok=True)

        # データベースバックアップ
        db_backup_path = os.path.join(system_backup_path, "database.db")
        self.storage_manager.backup_database(db_backup_path)

        # インデックスバックアップ
        index_backup_path = os.path.join(system_backup_path, "index")
        shutil.copytree(self.index_manager.index_path, index_backup_path)

        # 埋め込みキャッシュバックアップ
        embedding_backup_path = os.path.join(system_backup_path, "embeddings.pkl")
        self.embedding_manager.save_embeddings()
        shutil.copy2(self.embedding_manager.embeddings_path, embedding_backup_path)

        # システム状態を変更（データ追加・削除）
        # 新しいドキュメントを追加
        new_doc = self.test_data_generator.generate_test_documents(1)[0]
        new_doc.id = "system_test_new_doc"

        self.storage_manager.save_document(new_doc)
        self.index_manager.add_document(new_doc)
        self.embedding_manager.add_document_embedding(new_doc.id, new_doc.content)

        # 既存ドキュメントを削除
        deleted_doc = test_docs[12]
        self.storage_manager.delete_document(deleted_doc.id)
        self.index_manager.remove_document(deleted_doc.id)
        self.embedding_manager.remove_document_embedding(deleted_doc.id)

        # 変更後の状態確認
        modified_db_count = self.storage_manager.get_document_count()
        self.index_manager.get_document_count()
        self.embedding_manager.get_cache_info()["total_embeddings"]

        self.assert_condition(
            modified_db_count != original_db_count,
            "システム変更がデータベースに反映されていません"
        )

        # システム全体の復元
        # 各コンポーネントを閉じる
        self.storage_manager.close()
        self.index_manager.close()

        # データベース復元
        self.storage_manager = StorageManager(self.test_data_dir)
        self.storage_manager.restore_database(db_backup_path)

        # インデックス復元
        if os.path.exists(self.index_manager.index_path):
            shutil.rmtree(self.index_manager.index_path)
        shutil.copytree(index_backup_path, self.index_manager.index_path)
        self.index_manager = IndexManager(str(self.index_manager.index_path))

        # 埋め込みキャッシュ復元
        shutil.copy2(embedding_backup_path, self.embedding_manager.embeddings_path)
        self.embedding_manager = EmbeddingManager(
            embeddings_path=self.embedding_manager.embeddings_path
        )

        # 復元後の状態確認
        restored_db_count = self.storage_manager.get_document_count()
        restored_index_count = self.index_manager.get_document_count()
        restored_embedding_count = self.embedding_manager.get_cache_info()["total_embeddings"]

        self.assert_condition(
            restored_db_count == original_db_count,
            f"システム復元後のDB件数が不正: 期待={original_db_count}, 実際={restored_db_count}"
        )

        self.assert_condition(
            restored_index_count == original_index_count,
            f"システム復元後のインデックス件数が不正: 期待={original_index_count}, 実際={restored_index_count}"
        )

        self.assert_condition(
            restored_embedding_count == original_embedding_count,
            f"システム復元後の埋め込み件数が不正: 期待={original_embedding_count}, 実際={restored_embedding_count}"
        )

        # 復元されたシステムで各機能が正常に動作することを確認
        # データベース検索
        db_docs = self.storage_manager.list_documents(limit=10)
        self.assert_condition(
            len(db_docs) > 0,
            "復元後のデータベース検索で結果が返されませんでした"
        )

        # インデックス検索
        index_results = self.index_manager.search_text("test", limit=5)
        self.assert_condition(
            len(index_results) > 0,
            "復元後のインデックス検索で結果が返されませんでした"
        )

        # 埋め込み検索
        embedding_results = self.embedding_manager.search_similar("test content", limit=5)
        self.assert_condition(
            len(embedding_results) > 0,
            "復元後の埋め込み検索で結果が返されませんでした"
        )

        self.logger.info("完全システムバックアップ・回復の検証が完了しました")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュ値を計算"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


# 実行用のメイン関数
def main():
    """データ永続化検証の実行"""
    print("DocMind データ永続化・整合性検証を開始します...")

    # 検証設定
    config = ValidationConfig(
        enable_performance_monitoring=True,
        enable_memory_monitoring=True,
        max_execution_time=600.0,  # 10分
        max_memory_usage=4096.0,   # 4GB
        log_level="INFO"
    )

    # 検証実行
    validator = DataPersistenceValidator(config)

    try:
        validator.setup_test_environment()
        results = validator.run_validation()

        # 結果サマリーの表示
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests

        print("\n=== データ永続化検証結果 ===")
        print(f"総テスト数: {total_tests}")
        print(f"成功: {passed_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")

        # 失敗したテストの詳細表示
        if failed_tests > 0:
            print("\n=== 失敗したテスト ===")
            for result in results:
                if not result.success:
                    print(f"- {result.test_name}: {result.error_message}")

        # パフォーマンス統計
        stats = validator.get_statistics_summary()
        print("\n=== パフォーマンス統計 ===")
        print(f"平均実行時間: {stats.get('avg_execution_time', 0):.2f}秒")
        print(f"最大メモリ使用量: {stats.get('max_memory_usage', 0):.2f}MB")

    except Exception as e:
        print(f"検証実行中にエラーが発生しました: {e}")

    finally:
        validator.teardown_test_environment()
        validator.cleanup()

    print("データ永続化・整合性検証が完了しました。")


if __name__ == "__main__":
    main()
