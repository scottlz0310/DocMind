#!/usr/bin/env python3
"""
検索結果表示ウィジェットのユニットテスト

SearchResultsWidgetとSearchResultItemWidgetの機能をテストします。
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock

# テスト対象のモジュールをインポートするためにパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# PySide6のテスト用設定
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.data.models import Document, FileType, SearchResult, SearchType
from src.gui.search_results import (
    SearchResultItemWidget,
    SearchResultsWidget,
    SortOrder,
)


class TestSearchResultItemWidget(unittest.TestCase):
    """SearchResultItemWidgetのテストクラス"""

    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """各テストの前処理"""
        # テスト用のファイルを作成
        self.test_file_path = "tests/fixtures/sample_text.txt"

        # テスト用のドキュメントを作成
        self.test_document = Document(
            id="test_doc_1",
            file_path=self.test_file_path,
            title="テストドキュメント",
            content="これはテスト用のドキュメントコンテンツです。検索テストのために作成されました。",
            file_type=FileType.TEXT,
            size=1024,
            created_date=datetime(2024, 1, 1, 10, 0, 0),
            modified_date=datetime(2024, 1, 15, 14, 30, 0),
            indexed_date=datetime(2024, 1, 16, 9, 0, 0)
        )

        # テスト用の検索結果を作成
        self.test_search_result = SearchResult(
            document=self.test_document,
            score=0.85,
            search_type=SearchType.HYBRID,
            snippet="これはテスト用のドキュメント...",
            highlighted_terms=["テスト", "ドキュメント"],
            relevance_explanation="キーワードマッチによる高い関連度",
            rank=1
        )

    def test_item_widget_initialization(self):
        """アイテムウィジェットの初期化テスト"""
        widget = SearchResultItemWidget(self.test_search_result)

        # 基本プロパティの確認
        self.assertIsNotNone(widget)
        self.assertEqual(widget.search_result, self.test_search_result)
        self.assertFalse(widget.is_selected)
        self.assertFalse(widget.is_hovered)

        # UIコンポーネントの確認
        self.assertIsNotNone(widget.title_label)
        self.assertIsNotNone(widget.score_label)
        self.assertIsNotNone(widget.snippet_label)
        self.assertIsNotNone(widget.file_info_label)
        self.assertIsNotNone(widget.search_type_label)

        # 表示内容の確認
        self.assertEqual(widget.title_label.text(), "テストドキュメント")
        self.assertEqual(widget.score_label.text(), "85.0%")
        self.assertEqual(widget.search_type_label.text(), "ハイブリッド検索")

    def test_snippet_formatting(self):
        """スニペットフォーマットのテスト"""
        widget = SearchResultItemWidget(self.test_search_result)

        # 短いスニペットの場合
        formatted_snippet = widget._format_snippet()
        self.assertEqual(formatted_snippet, "これはテスト用のドキュメント...")

        # 長いスニペットの場合
        long_result = SearchResult(
            document=self.test_document,
            score=0.75,
            search_type=SearchType.FULL_TEXT,
            snippet="これは非常に長いスニペットテキストです。" * 10,  # 長いテキスト
            highlighted_terms=["テスト"],
            rank=2
        )
        long_widget = SearchResultItemWidget(long_result)
        long_snippet = long_widget._format_snippet()
        self.assertTrue(len(long_snippet) <= 150)
        self.assertTrue(long_snippet.endswith("..."))

    def test_file_info_formatting(self):
        """ファイル情報フォーマットのテスト"""
        widget = SearchResultItemWidget(self.test_search_result)

        file_info = widget._format_file_info()
        self.assertIn("テキスト", file_info)
        self.assertIn("1.0 KB", file_info)
        self.assertIn("sample_text.txt", file_info)

    def test_file_type_display_names(self):
        """ファイルタイプ表示名のテスト"""
        widget = SearchResultItemWidget(self.test_search_result)

        test_cases = [
            (FileType.PDF, "PDF"),
            (FileType.WORD, "Word"),
            (FileType.EXCEL, "Excel"),
            (FileType.MARKDOWN, "Markdown"),
            (FileType.TEXT, "テキスト"),
            (FileType.UNKNOWN, "不明")
        ]

        for file_type, expected_name in test_cases:
            display_name = widget._get_file_type_display_name(file_type)
            self.assertEqual(display_name, expected_name)

    def test_file_size_formatting(self):
        """ファイルサイズフォーマットのテスト"""
        widget = SearchResultItemWidget(self.test_search_result)

        test_cases = [
            (512, "512 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB")
        ]

        for size, expected_format in test_cases:
            formatted_size = widget._format_file_size(size)
            self.assertEqual(formatted_size, expected_format)

    def test_score_color_mapping(self):
        """スコア色マッピングのテスト"""
        widget = SearchResultItemWidget(self.test_search_result)

        test_cases = [
            (0.9, "#4caf50"),  # 緑（高スコア）
            (0.7, "#ff9800"),  # オレンジ（中スコア）
            (0.4, "#f44336")   # 赤（低スコア）
        ]

        for score, expected_color in test_cases:
            color = widget._get_score_color(score)
            self.assertEqual(color, expected_color)

    def test_search_type_color_mapping(self):
        """検索タイプ色マッピングのテスト"""
        widget = SearchResultItemWidget(self.test_search_result)

        test_cases = [
            (SearchType.FULL_TEXT, "#2196f3"),
            (SearchType.SEMANTIC, "#9c27b0"),
            (SearchType.HYBRID, "#ff5722")
        ]

        for search_type, expected_color in test_cases:
            color = widget._get_search_type_color(search_type)
            self.assertEqual(color, expected_color)

    def test_selection_state(self):
        """選択状態のテスト"""
        widget = SearchResultItemWidget(self.test_search_result)

        # 初期状態は非選択
        self.assertFalse(widget.is_selected)

        # 選択状態に変更
        widget.set_selected(True)
        self.assertTrue(widget.is_selected)

        # 非選択状態に戻す
        widget.set_selected(False)
        self.assertFalse(widget.is_selected)

    def test_mouse_interactions(self):
        """マウスインタラクションのテスト"""
        widget = SearchResultItemWidget(self.test_search_result)

        # シグナルのモック
        click_signal_mock = Mock()
        preview_signal_mock = Mock()
        widget.item_clicked.connect(click_signal_mock)
        widget.preview_requested.connect(preview_signal_mock)

        # マウスクリックのシミュレーション
        QTest.mouseClick(widget, Qt.LeftButton)
        click_signal_mock.assert_called_once_with(self.test_search_result)

        # マウスダブルクリックのシミュレーション
        QTest.mouseDClick(widget, Qt.LeftButton)
        preview_signal_mock.assert_called_once_with(self.test_search_result)


class TestSearchResultsWidget(unittest.TestCase):
    """SearchResultsWidgetのテストクラス"""

    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """各テストの前処理"""
        self.widget = SearchResultsWidget()

        # テスト用の検索結果を作成
        self.test_results = []
        for i in range(25):  # ページネーションテスト用に25件作成
            # 既存のテストファイルを使用
            test_file = "tests/fixtures/sample_text.txt" if i % 2 == 0 else "tests/fixtures/sample_markdown.md"
            file_type = FileType.TEXT if i % 2 == 0 else FileType.MARKDOWN

            doc = Document(
                id=f"test_doc_{i}",
                file_path=test_file,
                title=f"テストドキュメント {i}",
                content=f"これはテスト用のドキュメント{i}のコンテンツです。",
                file_type=file_type,
                size=1024 * (i + 1),
                created_date=datetime(2024, 1, i + 1, 10, 0, 0),
                modified_date=datetime(2024, 1, i + 1, 14, 30, 0),
                indexed_date=datetime(2024, 1, i + 1, 9, 0, 0)
            )

            result = SearchResult(
                document=doc,
                score=0.9 - (i * 0.02),  # スコアを徐々に下げる
                search_type=SearchType.HYBRID,
                snippet=f"テストスニペット {i}",
                highlighted_terms=["テスト"],
                rank=i + 1
            )
            self.test_results.append(result)

    def test_widget_initialization(self):
        """ウィジェットの初期化テスト"""
        self.assertIsNotNone(self.widget)
        self.assertEqual(len(self.widget.all_results), 0)
        self.assertEqual(len(self.widget.filtered_results), 0)
        self.assertEqual(len(self.widget.current_results), 0)
        self.assertIsNone(self.widget.selected_result)

        # ページネーション設定の確認
        self.assertEqual(self.widget.results_per_page, 20)
        self.assertEqual(self.widget.current_page, 1)
        self.assertEqual(self.widget.total_pages, 1)

        # ソート設定の確認
        self.assertEqual(self.widget.current_sort_order, SortOrder.RELEVANCE_DESC)

    def test_display_results(self):
        """結果表示のテスト"""
        # 結果を表示
        self.widget.display_results(self.test_results)

        # データの確認
        self.assertEqual(len(self.widget.all_results), 25)
        self.assertEqual(len(self.widget.filtered_results), 25)

        # ページネーションの確認
        self.assertEqual(self.widget.total_pages, 2)  # 25件 ÷ 20件/ページ = 2ページ
        self.assertEqual(len(self.widget.current_results), 20)  # 最初のページは20件

        # 結果アイテムの確認
        self.assertEqual(len(self.widget.result_items), 20)

    def test_pagination(self):
        """ページネーションのテスト"""
        self.widget.display_results(self.test_results)

        # 最初のページ
        self.assertEqual(self.widget.current_page, 1)
        self.assertEqual(len(self.widget.current_results), 20)

        # 2ページ目に移動
        self.widget.go_to_page(2)
        self.assertEqual(self.widget.current_page, 2)
        self.assertEqual(len(self.widget.current_results), 5)  # 残り5件

        # 無効なページ番号のテスト
        self.widget.go_to_page(0)  # 無効
        self.assertEqual(self.widget.current_page, 2)  # 変更されない

        self.widget.go_to_page(10)  # 無効
        self.assertEqual(self.widget.current_page, 2)  # 変更されない

    def test_sorting(self):
        """ソート機能のテスト"""
        self.widget.display_results(self.test_results)

        # 関連度降順（デフォルト）
        first_result = self.widget.current_results[0]
        self.assertEqual(first_result.score, 0.9)  # 最高スコア

        # 関連度昇順に変更
        self.widget.sort_combo.setCurrentIndex(1)  # RELEVANCE_ASC
        self.widget._on_sort_changed(1)

        first_result = self.widget.current_results[0]
        self.assertEqual(first_result.score, 0.42)  # 最低スコア

        # タイトル昇順に変更
        self.widget.sort_combo.setCurrentIndex(2)  # TITLE_ASC
        self.widget._on_sort_changed(2)

        first_result = self.widget.current_results[0]
        self.assertTrue(first_result.document.title.startswith("テストドキュメント 0"))

    def test_results_per_page_change(self):
        """1ページあたりの結果数変更のテスト"""
        self.widget.display_results(self.test_results)

        # 初期状態（20件/ページ）
        self.assertEqual(self.widget.results_per_page, 20)
        self.assertEqual(self.widget.total_pages, 2)

        # 10件/ページに変更
        self.widget.per_page_combo.setCurrentText("10")
        self.widget._on_per_page_changed("10")

        self.assertEqual(self.widget.results_per_page, 10)
        self.assertEqual(self.widget.total_pages, 3)  # 25件 ÷ 10件/ページ = 3ページ
        self.assertEqual(len(self.widget.current_results), 10)

    def test_clear_results(self):
        """結果クリアのテスト"""
        self.widget.display_results(self.test_results)

        # データが存在することを確認
        self.assertGreater(len(self.widget.all_results), 0)
        self.assertGreater(len(self.widget.result_items), 0)

        # クリア実行
        self.widget.clear_results()

        # データがクリアされたことを確認
        self.assertEqual(len(self.widget.all_results), 0)
        self.assertEqual(len(self.widget.filtered_results), 0)
        self.assertEqual(len(self.widget.current_results), 0)
        self.assertEqual(len(self.widget.result_items), 0)
        self.assertIsNone(self.widget.selected_result)

        # ページネーションがリセットされたことを確認
        self.assertEqual(self.widget.current_page, 1)
        self.assertEqual(self.widget.total_pages, 1)

    def test_result_selection(self):
        """結果選択のテスト"""
        self.widget.display_results(self.test_results)

        # シグナルのモック
        selection_signal_mock = Mock()
        self.widget.result_selected.connect(selection_signal_mock)

        # 最初の結果を選択
        first_result = self.widget.current_results[0]
        self.widget._on_result_selected(first_result)

        # 選択状態の確認
        self.assertEqual(self.widget.selected_result, first_result)
        selection_signal_mock.assert_called_once_with(first_result)

        # 選択されたアイテムウィジェットの状態確認
        first_item_widget = self.widget.result_items[0]
        self.assertTrue(first_item_widget.is_selected)

    def test_preview_request(self):
        """プレビュー要求のテスト"""
        self.widget.display_results(self.test_results)

        # シグナルのモック
        preview_signal_mock = Mock()
        self.widget.preview_requested.connect(preview_signal_mock)

        # プレビュー要求
        first_result = self.widget.current_results[0]
        self.widget._on_preview_requested(first_result)

        preview_signal_mock.assert_called_once_with(first_result)

    def test_empty_state(self):
        """空の状態のテスト"""
        # 空の結果を表示
        self.widget.display_results([])

        # データが空であることを確認
        self.assertEqual(len(self.widget.all_results), 0)
        self.assertEqual(len(self.widget.current_results), 0)
        self.assertEqual(len(self.widget.result_items), 0)

        # ページネーションの確認
        self.assertEqual(self.widget.total_pages, 1)
        self.assertEqual(self.widget.current_page, 1)

    def test_refresh_display(self):
        """表示更新のテスト"""
        self.widget.display_results(self.test_results)

        # 現在の状態を記録
        original_page = self.widget.current_page
        original_sort = self.widget.current_sort_order

        # 表示を更新
        self.widget.refresh_display()

        # 状態が保持されていることを確認
        self.assertEqual(self.widget.current_page, original_page)
        self.assertEqual(self.widget.current_sort_order, original_sort)
        self.assertEqual(len(self.widget.current_results), 20)

    def test_get_methods(self):
        """取得メソッドのテスト"""
        self.widget.display_results(self.test_results)

        # 結果選択
        first_result = self.widget.current_results[0]
        self.widget._on_result_selected(first_result)

        # 取得メソッドのテスト
        self.assertEqual(self.widget.get_selected_result(), first_result)
        self.assertEqual(len(self.widget.get_all_results()), 25)
        self.assertEqual(len(self.widget.get_filtered_results()), 25)

    def test_set_results_per_page(self):
        """1ページあたりの結果数設定のテスト"""
        self.widget.display_results(self.test_results)

        # 結果数を変更
        self.widget.set_results_per_page(15)

        self.assertEqual(self.widget.results_per_page, 15)
        self.assertEqual(self.widget.per_page_combo.currentText(), "15")
        self.assertEqual(self.widget.total_pages, 2)  # 25件 ÷ 15件/ページ = 2ページ
        self.assertEqual(self.widget.current_page, 1)  # 最初のページに戻る


class TestSearchResultsIntegration(unittest.TestCase):
    """検索結果ウィジェットの統合テスト"""

    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """各テストの前処理"""
        self.widget = SearchResultsWidget()

        # 多様なテストデータを作成
        self.mixed_results = []
        search_types = [SearchType.FULL_TEXT, SearchType.SEMANTIC, SearchType.HYBRID]

        for i in range(50):
            # 既存のテストファイルを使用
            test_files = ["tests/fixtures/sample_text.txt", "tests/fixtures/sample_markdown.md"]
            test_file = test_files[i % len(test_files)]
            current_file_type = FileType.TEXT if i % 2 == 0 else FileType.MARKDOWN

            doc = Document(
                id=f"mixed_doc_{i}",
                file_path=test_file,
                title=f"ドキュメント {chr(65 + (i % 26))}{i}",  # A0, B1, C2, ...
                content=f"混合テストドキュメント{i}のコンテンツ",
                file_type=current_file_type,
                size=1024 * (i + 1),
                created_date=datetime(2024, 1, (i % 28) + 1, 10, 0, 0),
                modified_date=datetime(2024, 1, (i % 28) + 1, 14, 30, 0),
                indexed_date=datetime(2024, 1, (i % 28) + 1, 9, 0, 0)
            )

            result = SearchResult(
                document=doc,
                score=0.1 + (i % 90) / 100.0,  # 0.1から0.99のスコア
                search_type=search_types[i % len(search_types)],
                snippet=f"混合スニペット {i}",
                highlighted_terms=["混合", "テスト"],
                rank=i + 1
            )
            self.mixed_results.append(result)

    def test_large_dataset_performance(self):
        """大規模データセットのパフォーマンステスト"""
        import time

        start_time = time.time()
        self.widget.display_results(self.mixed_results)
        end_time = time.time()

        # 表示処理が1秒以内に完了することを確認
        self.assertLess(end_time - start_time, 1.0)

        # データが正しく処理されていることを確認
        self.assertEqual(len(self.widget.all_results), 50)
        self.assertEqual(self.widget.total_pages, 3)  # 50件 ÷ 20件/ページ = 3ページ

    def test_mixed_file_types_display(self):
        """混合ファイルタイプの表示テスト"""
        self.widget.display_results(self.mixed_results)

        # 各ファイルタイプが正しく表示されることを確認
        displayed_types = set()
        for item in self.widget.result_items:
            file_info = item.file_info_label.text()
            if "PDF" in file_info:
                displayed_types.add("PDF")
            elif "Word" in file_info:
                displayed_types.add("Word")
            elif "Excel" in file_info:
                displayed_types.add("Excel")
            elif "Markdown" in file_info:
                displayed_types.add("Markdown")
            elif "テキスト" in file_info:
                displayed_types.add("テキスト")

        # 複数のファイルタイプが表示されていることを確認
        self.assertGreater(len(displayed_types), 1)

    def test_mixed_search_types_display(self):
        """混合検索タイプの表示テスト"""
        self.widget.display_results(self.mixed_results)

        # 各検索タイプが正しく表示されることを確認
        displayed_search_types = set()
        for item in self.widget.result_items:
            search_type_text = item.search_type_label.text()
            displayed_search_types.add(search_type_text)

        # 複数の検索タイプが表示されていることを確認
        self.assertGreater(len(displayed_search_types), 1)

        # 期待される検索タイプが含まれていることを確認
        expected_types = {"全文検索", "セマンティック検索", "ハイブリッド検索"}
        self.assertTrue(displayed_search_types.issubset(expected_types))

    def test_comprehensive_sorting(self):
        """包括的ソートテスト"""
        self.widget.display_results(self.mixed_results)

        # 各ソート順をテスト
        sort_tests = [
            (0, SortOrder.RELEVANCE_DESC, lambda r: -r.score),
            (1, SortOrder.RELEVANCE_ASC, lambda r: r.score),
            (2, SortOrder.TITLE_ASC, lambda r: r.document.title.lower()),
            (3, SortOrder.TITLE_DESC, lambda r: r.document.title.lower()),
            (4, SortOrder.DATE_DESC, lambda r: -r.document.modified_date.timestamp()),
            (5, SortOrder.DATE_ASC, lambda r: r.document.modified_date.timestamp()),
            (6, SortOrder.SIZE_DESC, lambda r: -r.document.size),
            (7, SortOrder.SIZE_ASC, lambda r: r.document.size)
        ]

        for index, expected_order, sort_key in sort_tests:
            self.widget.sort_combo.setCurrentIndex(index)
            self.widget._on_sort_changed(index)

            # ソート順が正しく適用されていることを確認
            self.assertEqual(self.widget.current_sort_order, expected_order)

            # 実際のソート結果を確認（最初の数件）
            if len(self.widget.current_results) >= 2:
                first_result = self.widget.current_results[0]
                second_result = self.widget.current_results[1]

                first_key = sort_key(first_result)
                second_key = sort_key(second_result)

                # 降順ソートの場合
                if expected_order in [SortOrder.RELEVANCE_DESC, SortOrder.TITLE_DESC,
                                    SortOrder.DATE_DESC, SortOrder.SIZE_DESC]:
                    if expected_order == SortOrder.TITLE_DESC:
                        self.assertGreaterEqual(first_key, second_key)
                    else:
                        self.assertLessEqual(first_key, second_key)  # 負の値なので
                # 昇順ソートの場合
                else:
                    self.assertLessEqual(first_key, second_key)


if __name__ == '__main__':
    # テストスイートの実行
    unittest.main(verbosity=2)
