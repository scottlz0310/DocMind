# -*- coding: utf-8 -*-
"""
SearchManagerのユニットテスト

ハイブリッド検索機能、結果マージ、スニペット生成、検索提案機能をテストします。
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os
from datetime import datetime
from typing import List

from src.core.search_manager import SearchManager, SearchWeights
from src.core.index_manager import IndexManager
from src.core.embedding_manager import EmbeddingManager
from src.data.models import Document, SearchResult, SearchType, SearchQuery, FileType
from src.utils.exceptions import SearchError


class TestSearchManager(unittest.TestCase):
    """SearchManagerクラスのテストケース"""
    
    def setUp(self):
        """テスト前の準備"""
        # 劣化管理マネージャーを初期化し、検索機能を有効化
        from src.utils.graceful_degradation import get_global_degradation_manager
        degradation_manager = get_global_degradation_manager()
        degradation_manager.mark_component_healthy("search_manager")
        
        # モックオブジェクトを作成
        self.mock_index_manager = Mock(spec=IndexManager)
        self.mock_embedding_manager = Mock(spec=EmbeddingManager)
        
        # SearchManagerインスタンスを作成
        self.search_manager = SearchManager(
            self.mock_index_manager,
            self.mock_embedding_manager
        )
        
        # テスト用のドキュメントを作成
        self.test_documents = self._create_test_documents()
        
        # テスト用の検索結果を作成
        self.test_full_text_results = self._create_test_full_text_results()
        self.test_semantic_results = self._create_test_semantic_results()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # 一時ファイルを削除
        if hasattr(self, 'temp_files'):
            import os
            for temp_file in self.temp_files:
                try:
                    os.unlink(temp_file)
                except FileNotFoundError:
                    pass
    
    def _create_test_documents(self) -> List[Document]:
        """テスト用のドキュメントを作成"""
        # テスト用の一時ファイルを作成
        import tempfile
        import os
        
        temp_files = []
        documents = []
        
        test_data = [
            {
                "id": "doc1",
                "title": "Python プログラミング入門",
                "content": "Pythonは初心者にも学びやすいプログラミング言語です。データ分析や機械学習にも使われます。",
                "size": 1000
            },
            {
                "id": "doc2", 
                "title": "機械学習の基礎",
                "content": "機械学習は人工知能の一分野で、データからパターンを学習します。教師あり学習と教師なし学習があります。",
                "size": 1200
            },
            {
                "id": "doc3",
                "title": "データ分析手法", 
                "content": "データ分析では統計学的手法を用いてデータの傾向を把握します。可視化も重要な要素です。",
                "size": 800
            }
        ]
        
        for data in test_data:
            # 一時ファイルを作成
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            temp_file.write(data["content"])
            temp_file.close()
            temp_files.append(temp_file.name)
            
            # Documentオブジェクトを作成
            document = Document(
                id=data["id"],
                file_path=temp_file.name,
                title=data["title"],
                content=data["content"],
                file_type=FileType.TEXT,
                size=data["size"],
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now()
            )
            documents.append(document)
        
        # テスト終了時にファイルを削除するためにリストを保存
        self.temp_files = temp_files
        
        return documents
    
    def _create_test_full_text_results(self) -> List[SearchResult]:
        """テスト用の全文検索結果を作成"""
        return [
            SearchResult(
                document=self.test_documents[0],
                score=0.8,
                search_type=SearchType.FULL_TEXT,
                snippet="Pythonは初心者にも学びやすいプログラミング言語です。",
                highlighted_terms=["Python", "プログラミング"],
                relevance_explanation="全文検索スコア: 0.80",
                rank=1
            ),
            SearchResult(
                document=self.test_documents[2],
                score=0.6,
                search_type=SearchType.FULL_TEXT,
                snippet="データ分析では統計学的手法を用いてデータの傾向を把握します。",
                highlighted_terms=["データ", "分析"],
                relevance_explanation="全文検索スコア: 0.60",
                rank=2
            )
        ]
    
    def _create_test_semantic_results(self) -> List[SearchResult]:
        """テスト用のセマンティック検索結果を作成"""
        return [
            SearchResult(
                document=self.test_documents[1],
                score=0.7,
                search_type=SearchType.SEMANTIC,
                snippet="機械学習は人工知能の一分野で、データからパターンを学習します。",
                highlighted_terms=["機械学習", "人工知能"],
                relevance_explanation="セマンティック類似度: 0.70",
                rank=1
            ),
            SearchResult(
                document=self.test_documents[0],
                score=0.5,
                search_type=SearchType.SEMANTIC,
                snippet="Pythonは初心者にも学びやすいプログラミング言語です。",
                highlighted_terms=["Python", "プログラミング"],
                relevance_explanation="セマンティック類似度: 0.50",
                rank=2
            )
        ]


class TestSearchWeights(unittest.TestCase):
    """SearchWeightsクラスのテストケース"""
    
    def test_default_weights(self):
        """デフォルト重みのテスト"""
        weights = SearchWeights()
        self.assertEqual(weights.full_text, 0.6)
        self.assertEqual(weights.semantic, 0.4)
    
    def test_custom_weights(self):
        """カスタム重みのテスト"""
        weights = SearchWeights(full_text=0.7, semantic=0.3)
        self.assertEqual(weights.full_text, 0.7)
        self.assertEqual(weights.semantic, 0.3)
    
    def test_weight_normalization(self):
        """重みの正規化テスト"""
        weights = SearchWeights(full_text=0.8, semantic=0.6)
        # 合計が1.4なので、正規化後は 0.8/1.4 ≈ 0.571, 0.6/1.4 ≈ 0.429
        self.assertAlmostEqual(weights.full_text, 0.571, places=2)
        self.assertAlmostEqual(weights.semantic, 0.429, places=2)


class TestSearchManagerMethods(TestSearchManager):
    """SearchManagerの個別メソッドのテストケース"""
    
    def test_full_text_search(self):
        """全文検索のテスト"""
        # モックの設定
        self.mock_index_manager.search_text.return_value = self.test_full_text_results
        
        # 検索クエリを作成
        query = SearchQuery(
            query_text="Python プログラミング",
            search_type=SearchType.FULL_TEXT,
            limit=10
        )
        
        # 全文検索を実行
        results = self.search_manager._full_text_search(query)
        
        # 結果を検証
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].document.title, "Python プログラミング入門")
        self.assertEqual(results[0].search_type, SearchType.FULL_TEXT)
        
        # IndexManagerが正しく呼ばれたことを確認
        self.mock_index_manager.search_text.assert_called_once()
    
    def test_semantic_search(self):
        """セマンティック検索のテスト"""
        # モックの設定
        self.mock_embedding_manager.search_similar.return_value = [
            ("doc1", 0.7),
            ("doc2", 0.5)
        ]
        
        # _get_document_by_idメソッドをモック
        with patch.object(self.search_manager, '_get_document_by_id') as mock_get_doc:
            mock_get_doc.side_effect = lambda doc_id: {
                "doc1": self.test_documents[0],
                "doc2": self.test_documents[1]
            }.get(doc_id)
            
            # 検索クエリを作成
            query = SearchQuery(
                query_text="機械学習 AI",
                search_type=SearchType.SEMANTIC,
                limit=10
            )
            
            # セマンティック検索を実行
            results = self.search_manager._semantic_search(query)
            
            # 結果を検証
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].score, 0.7)
            self.assertEqual(results[0].search_type, SearchType.SEMANTIC)
    
    def test_hybrid_search(self):
        """ハイブリッド検索のテスト"""
        # モックの設定
        with patch.object(self.search_manager, '_full_text_search') as mock_ft_search, \
             patch.object(self.search_manager, '_semantic_search') as mock_sem_search:
            
            mock_ft_search.return_value = self.test_full_text_results
            mock_sem_search.return_value = self.test_semantic_results
            
            # 検索クエリを作成
            query = SearchQuery(
                query_text="Python 機械学習",
                search_type=SearchType.HYBRID,
                limit=10,
                weights={"full_text": 0.6, "semantic": 0.4}
            )
            
            # ハイブリッド検索を実行
            results = self.search_manager._hybrid_search(query)
            
            # 結果を検証
            self.assertGreater(len(results), 0)
            self.assertTrue(all(r.search_type == SearchType.HYBRID for r in results))
            
            # 両方の検索メソッドが呼ばれたことを確認
            mock_ft_search.assert_called_once()
            mock_sem_search.assert_called_once()
    
    def test_merge_search_results(self):
        """検索結果マージのテスト"""
        weights = SearchWeights(full_text=0.6, semantic=0.4)
        
        # 結果をマージ
        merged_results = self.search_manager._merge_search_results(
            self.test_full_text_results,
            self.test_semantic_results,
            weights
        )
        
        # 結果を検証
        self.assertGreater(len(merged_results), 0)
        
        # スコアが正しく計算されているか確認
        for result in merged_results:
            self.assertEqual(result.search_type, SearchType.HYBRID)
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)
    
    def test_generate_enhanced_snippet(self):
        """強化スニペット生成のテスト"""
        content = "Pythonは初心者にも学びやすいプログラミング言語です。データ分析や機械学習にも使われます。オープンソースで無料で使用できます。"
        query_text = "Python プログラミング"
        
        snippet = self.search_manager._generate_snippet(content, query_text)
        
        # スニペットが生成されることを確認
        self.assertIsInstance(snippet, str)
        self.assertGreater(len(snippet), 0)
        self.assertLessEqual(len(snippet), self.search_manager.snippet_max_length + 10)  # "..."を考慮
    
    def test_extract_query_terms(self):
        """クエリ用語抽出のテスト"""
        query_text = "Python プログラミング machine learning"
        
        terms = self.search_manager._extract_query_terms(query_text)
        
        # 用語が正しく抽出されることを確認
        self.assertIn("python", terms)
        self.assertIn("プログラミング", terms)
        self.assertIn("machine", terms)
        self.assertIn("learning", terms)
    
    def test_search_suggestions(self):
        """検索提案のテスト"""
        # インデックス用語を設定
        self.search_manager._indexed_terms = {
            "python", "プログラミング", "機械学習", "データ分析", "programming"
        }
        
        # 検索提案を取得
        suggestions = self.search_manager.get_search_suggestions("prog", limit=5)
        
        # 提案が返されることを確認
        self.assertIsInstance(suggestions, list)
        # "prog"で始まる用語があれば含まれるはず
        if any(term.startswith("prog") for term in self.search_manager._indexed_terms):
            self.assertGreater(len(suggestions), 0)
    
    def test_remove_duplicate_results(self):
        """重複結果除去のテスト"""
        # 重複する結果を作成
        duplicate_results = [
            self.test_full_text_results[0],  # doc1
            self.test_semantic_results[1],   # doc1 (重複)
            self.test_full_text_results[1],  # doc3
        ]
        
        unique_results = self.search_manager._remove_duplicate_results(duplicate_results)
        
        # 重複が除去されることを確認
        self.assertEqual(len(unique_results), 2)
        doc_ids = [r.document.id for r in unique_results]
        self.assertEqual(len(set(doc_ids)), len(doc_ids))  # すべて異なるID
    
    def test_search_with_invalid_type(self):
        """無効な検索タイプでのエラーテスト"""
        # SearchQueryの検証でValueErrorが発生することを確認
        with self.assertRaises(ValueError):
            SearchQuery(
                query_text="test",
                search_type="invalid_type"  # 無効なタイプ
            )
    
    def test_empty_query_handling(self):
        """空のクエリの処理テスト"""
        # 空のクエリでの検索提案
        suggestions = self.search_manager.get_search_suggestions("", limit=5)
        self.assertEqual(len(suggestions), 0)
        
        # 短すぎるクエリでの検索提案
        suggestions = self.search_manager.get_search_suggestions("a", limit=5)
        self.assertEqual(len(suggestions), 0)


class TestSearchManagerIntegration(TestSearchManager):
    """SearchManagerの統合テストケース"""
    
    def test_full_search_workflow(self):
        """完全な検索ワークフローのテスト"""
        # モックの設定
        self.mock_index_manager.search_text.return_value = self.test_full_text_results
        
        # 検索クエリを作成
        query = SearchQuery(
            query_text="Python プログラミング",
            search_type=SearchType.FULL_TEXT,
            limit=10
        )
        
        # 検索を実行
        results = self.search_manager.search(query)
        
        # 結果を検証
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        
        # 結果の順序が正しいことを確認（スコア順）
        for i in range(len(results) - 1):
            self.assertGreaterEqual(results[i].score, results[i + 1].score)
    
    def test_search_stats(self):
        """検索統計情報のテスト"""
        # モックの設定
        self.mock_index_manager.get_document_count.return_value = 100
        self.mock_embedding_manager.embeddings = {"doc1": None, "doc2": None}
        
        # 統計情報を取得
        stats = self.search_manager.get_search_stats()
        
        # 統計情報が正しく返されることを確認
        self.assertIsInstance(stats, dict)
        self.assertIn("indexed_documents", stats)
        self.assertIn("cached_embeddings", stats)
        self.assertIn("default_weights", stats)
        self.assertEqual(stats["indexed_documents"], 100)
        self.assertEqual(stats["cached_embeddings"], 2)
    
    def test_update_search_settings(self):
        """検索設定更新のテスト"""
        # 設定を更新
        self.search_manager.update_search_settings(
            full_text_weight=0.7,
            semantic_weight=0.3,
            min_semantic_similarity=0.2,
            snippet_max_length=150
        )
        
        # 設定が更新されることを確認
        self.assertAlmostEqual(self.search_manager.default_weights.full_text, 0.7, places=2)
        self.assertAlmostEqual(self.search_manager.default_weights.semantic, 0.3, places=2)
        self.assertEqual(self.search_manager.min_semantic_similarity, 0.2)
        self.assertEqual(self.search_manager.snippet_max_length, 150)


if __name__ == '__main__':
    # ログレベルを設定してテスト実行時のノイズを減らす
    import logging
    logging.getLogger().setLevel(logging.WARNING)
    
    # テストスイートを実行
    unittest.main(verbosity=2)