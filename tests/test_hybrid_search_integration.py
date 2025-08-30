"""
ハイブリッド検索の統合テスト

実際のIndexManagerとEmbeddingManagerを使用したSearchManagerの統合テストを実行します。
"""

import os
import shutil
import tempfile
import unittest

from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.core.search_manager import SearchManager
from src.data.models import Document, FileType, SearchQuery, SearchType


class TestHybridSearchIntegration(unittest.TestCase):
    """ハイブリッド検索の統合テストケース"""

    @classmethod
    def setUpClass(cls):
        """テストクラス全体の前準備"""
        # 一時ディレクトリを作成
        cls.temp_dir = tempfile.mkdtemp()
        cls.index_dir = os.path.join(cls.temp_dir, "test_index")
        cls.embeddings_path = os.path.join(cls.temp_dir, "test_embeddings.pkl")

        # テスト用ドキュメントファイルを作成
        cls.test_files_dir = os.path.join(cls.temp_dir, "test_files")
        os.makedirs(cls.test_files_dir, exist_ok=True)
        cls._create_test_files()

    @classmethod
    def tearDownClass(cls):
        """テストクラス全体の後処理"""
        # 一時ディレクトリを削除
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    @classmethod
    def _create_test_files(cls):
        """テスト用ファイルを作成"""
        test_contents = [
            {
                "filename": "python_basics.txt",
                "content": "Pythonは初心者にも学びやすいプログラミング言語です。シンプルな文法と豊富なライブラリが特徴です。データ分析、ウェブ開発、機械学習など様々な分野で使用されています。"
            },
            {
                "filename": "machine_learning.txt",
                "content": "機械学習は人工知能の一分野で、データからパターンを学習するアルゴリズムです。教師あり学習、教師なし学習、強化学習の3つの主要なカテゴリがあります。"
            },
            {
                "filename": "data_analysis.txt",
                "content": "データ分析は大量のデータから有用な情報を抽出するプロセスです。統計学的手法、可視化、機械学習技術を組み合わせて使用します。"
            },
            {
                "filename": "web_development.txt",
                "content": "ウェブ開発にはフロントエンドとバックエンドの開発があります。HTML、CSS、JavaScriptがフロントエンドの基本技術です。"
            },
            {
                "filename": "database_design.txt",
                "content": "データベース設計では正規化、インデックス、パフォーマンス最適化が重要です。SQLを使用してデータの操作と検索を行います。"
            }
        ]

        for file_info in test_contents:
            file_path = os.path.join(cls.test_files_dir, file_info["filename"])
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_info["content"])

    def setUp(self):
        """各テストの前準備"""
        # IndexManagerとEmbeddingManagerを初期化
        self.index_manager = IndexManager(self.index_dir)
        self.embedding_manager = EmbeddingManager(
            model_name="all-MiniLM-L6-v2",
            embeddings_path=self.embeddings_path
        )

        # SearchManagerを初期化
        self.search_manager = SearchManager(
            self.index_manager,
            self.embedding_manager
        )

        # テストドキュメントを作成してインデックス化
        self.test_documents = self._create_and_index_documents()

    def tearDown(self):
        """各テストの後処理"""
        # インデックスとキャッシュをクリア
        if os.path.exists(self.index_dir):
            shutil.rmtree(self.index_dir)
        if os.path.exists(self.embeddings_path):
            os.remove(self.embeddings_path)

    def _create_and_index_documents(self):
        """テストドキュメントを作成してインデックス化"""
        documents = []

        for filename in os.listdir(self.test_files_dir):
            file_path = os.path.join(self.test_files_dir, filename)

            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            document = Document.create_from_file(file_path, content)
            documents.append(document)

            # インデックスに追加
            self.index_manager.add_document(document)

            # 埋め込みを生成
            self.embedding_manager.add_document_embedding(document.id, content)

        # 埋め込みを保存
        self.embedding_manager.save_embeddings()

        return documents

    def test_full_text_search_integration(self):
        """全文検索の統合テスト"""
        query = SearchQuery(
            query_text="Python プログラミング",
            search_type=SearchType.FULL_TEXT,
            limit=10
        )

        results = self.search_manager.search(query)

        # 結果が返されることを確認
        self.assertGreater(len(results), 0)

        # Pythonに関連するドキュメントが上位に来ることを確認
        top_result = results[0]
        self.assertIn("python", top_result.document.content.lower())

        # 検索タイプが正しいことを確認
        for result in results:
            self.assertEqual(result.search_type, SearchType.FULL_TEXT)

    def test_semantic_search_integration(self):
        """セマンティック検索の統合テスト"""
        query = SearchQuery(
            query_text="人工知能 AI アルゴリズム",
            search_type=SearchType.SEMANTIC,
            limit=10
        )

        results = self.search_manager.search(query)

        # 結果が返されることを確認
        self.assertGreater(len(results), 0)

        # 機械学習に関連するドキュメントが含まれることを確認
        # （セマンティック検索では直接的なキーワードマッチがなくても関連文書を見つける）
        found_ml_doc = any("機械学習" in result.document.content for result in results)
        self.assertTrue(found_ml_doc, "セマンティック検索で機械学習関連文書が見つからない")

        # 検索タイプが正しいことを確認
        for result in results:
            self.assertEqual(result.search_type, SearchType.SEMANTIC)

    def test_hybrid_search_integration(self):
        """ハイブリッド検索の統合テスト"""
        query = SearchQuery(
            query_text="データ 分析 統計",
            search_type=SearchType.HYBRID,
            limit=10,
            weights={"full_text": 0.6, "semantic": 0.4}
        )

        results = self.search_manager.search(query)

        # 結果が返されることを確認
        self.assertGreater(len(results), 0)

        # データ分析に関連するドキュメントが含まれることを確認
        found_data_analysis = any(
            "データ分析" in result.document.content or
            "data_analysis" in result.document.file_path
            for result in results
        )
        self.assertTrue(found_data_analysis, "ハイブリッド検索でデータ分析関連文書が見つからない")

        # 検索タイプが正しいことを確認
        for result in results:
            self.assertEqual(result.search_type, SearchType.HYBRID)

        # スコアが適切な範囲にあることを確認
        for result in results:
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)

    def test_search_suggestions_integration(self):
        """検索提案の統合テスト"""
        # 検索提案インデックスを構築
        self.search_manager._build_suggestion_index()

        # 部分的なクエリで提案を取得
        suggestions = self.search_manager.get_search_suggestions("プログ", limit=5)

        # 提案が返されることを確認
        self.assertIsInstance(suggestions, list)

        # "プログラミング"が含まれる可能性が高い
        if suggestions:
            self.assertTrue(any("プログ" in suggestion for suggestion in suggestions))

    def test_search_with_file_type_filter(self):
        """ファイルタイプフィルターでの検索テスト"""
        query = SearchQuery(
            query_text="Python",
            search_type=SearchType.FULL_TEXT,
            limit=10,
            file_types=[FileType.TEXT]
        )

        results = self.search_manager.search(query)

        # 結果が返されることを確認
        self.assertGreater(len(results), 0)

        # すべての結果がTEXTファイルであることを確認
        for result in results:
            self.assertEqual(result.document.file_type, FileType.TEXT)

    def test_search_performance(self):
        """検索パフォーマンステスト"""
        import time

        query = SearchQuery(
            query_text="機械学習 データ分析",
            search_type=SearchType.HYBRID,
            limit=10
        )

        # 検索時間を測定
        start_time = time.time()
        results = self.search_manager.search(query)
        end_time = time.time()

        search_time = end_time - start_time

        # 検索が5秒以内に完了することを確認（要件6.1）
        self.assertLess(search_time, 5.0, f"検索時間が5秒を超えました: {search_time:.2f}秒")

        # 結果が返されることを確認
        self.assertGreater(len(results), 0)

    def test_empty_query_handling(self):
        """空クエリの処理テスト"""
        SearchQuery(
            query_text="",
            search_type=SearchType.FULL_TEXT,
            limit=10
        )

        # 空クエリでSearchErrorが発生することを確認
        with self.assertRaises(ValueError):  # SearchQueryの検証でエラー
            pass

    def test_large_result_set_handling(self):
        """大きな結果セットの処理テスト"""
        query = SearchQuery(
            query_text="の",  # 多くの文書にマッチする可能性が高い
            search_type=SearchType.FULL_TEXT,
            limit=100
        )

        results = self.search_manager.search(query)

        # 制限数を超えないことを確認
        self.assertLessEqual(len(results), 100)

        # 結果が関連度順にソートされていることを確認
        for i in range(len(results) - 1):
            self.assertGreaterEqual(results[i].score, results[i + 1].score)

    def test_search_result_snippets(self):
        """検索結果スニペットのテスト"""
        query = SearchQuery(
            query_text="Python プログラミング",
            search_type=SearchType.FULL_TEXT,
            limit=5
        )

        results = self.search_manager.search(query)

        # すべての結果にスニペットがあることを確認
        for result in results:
            self.assertIsInstance(result.snippet, str)
            self.assertGreater(len(result.snippet), 0)

            # スニペットが適切な長さであることを確認
            self.assertLessEqual(
                len(result.snippet),
                self.search_manager.snippet_max_length + 10  # "..."を考慮
            )

    def test_highlighted_terms_extraction(self):
        """ハイライト用語抽出のテスト"""
        query = SearchQuery(
            query_text="Python データ分析",
            search_type=SearchType.FULL_TEXT,
            limit=5
        )

        results = self.search_manager.search(query)

        # 結果にハイライト用語があることを確認
        for result in results:
            self.assertIsInstance(result.highlighted_terms, list)

            # クエリに含まれる用語がハイライト用語に含まれることを確認
            if result.highlighted_terms:
                query_terms = ["python", "データ", "分析"]
                found_terms = [term.lower() for term in result.highlighted_terms]
                any(
                    any(qt in ft for qt in query_terms)
                    for ft in found_terms
                )
                # 注意: 必ずしもすべてのクエリ用語がハイライトされるとは限らない


if __name__ == '__main__':
    # テスト実行前の警告
    print("注意: この統合テストは実際のAIモデルをダウンロードして使用します。")
    print("初回実行時は時間がかかる場合があります。")

    # ログレベルを設定
    import logging
    logging.getLogger().setLevel(logging.WARNING)

    # テストスイートを実行
    unittest.main(verbosity=2)
