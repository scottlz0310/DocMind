#!/usr/bin/env python3
"""
検索インターフェースの統合テスト

検索インターフェースの完全なワークフローをテストし、
各コンポーネントの連携が正しく動作することを確認します。
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

# テスト対象のモジュールをインポートするためのパス設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.data.models import Document, FileType, SearchQuery, SearchResult, SearchType
from src.gui.search_interface import (
    AdvancedSearchOptions,
    SearchHistoryWidget,
    SearchInputWidget,
    SearchInterface,
    SearchProgressWidget,
    SearchTypeSelector,
    SearchWorkerThread,
)
from src.utils.exceptions import SearchError


class TestSearchInputWidget:
    """検索入力ウィジェットのテスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()

    @pytest.fixture
    def widget(self, app):
        """SearchInputWidgetのフィクスチャ"""
        return SearchInputWidget()

    def test_initialization(self, widget):
        """初期化のテスト"""
        assert widget.placeholderText() == "検索キーワードを入力してください..."
        assert widget.maxLength() == 500
        assert widget.completer is not None

    def test_search_request_signal(self, widget, qtbot):
        """検索要求シグナルのテスト"""
        with qtbot.waitSignal(widget.search_requested, timeout=1000) as blocker:
            widget.setText("テスト検索")
            QTest.keyPress(widget, Qt.Key_Return)

        assert blocker.args[0] == "テスト検索"

    def test_empty_search_prevention(self, widget, qtbot):
        """空の検索の防止テスト"""
        # 空文字列では検索シグナルが発行されないことを確認
        widget.setText("")
        with qtbot.assertNotEmitted(widget.search_requested):
            QTest.keyPress(widget, Qt.Key_Return)

        # 空白のみでも検索シグナルが発行されないことを確認
        widget.setText("   ")
        with qtbot.assertNotEmitted(widget.search_requested):
            QTest.keyPress(widget, Qt.Key_Return)

    def test_suggestions_update(self, widget):
        """検索提案の更新テスト"""
        suggestions = ["テスト1", "テスト2", "サンプル"]
        widget.update_suggestions(suggestions)

        assert widget.suggestions == suggestions
        assert widget.completer.model().stringList() == suggestions

    def test_text_trimming(self, widget):
        """テキストの自動トリミングテスト"""
        widget.setText("  テスト検索  ")
        # テキスト変更イベントを手動で発火
        widget._on_text_changed("  テスト検索  ")

        assert widget.text() == "テスト検索"


class TestSearchTypeSelector:
    """検索タイプ選択ウィジェットのテスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()

    @pytest.fixture
    def widget(self, app):
        """SearchTypeSelectorのフィクスチャ"""
        return SearchTypeSelector()

    def test_initialization(self, widget):
        """初期化のテスト"""
        assert widget.get_search_type() == SearchType.HYBRID
        assert widget.hybrid_radio.isChecked()

    def test_search_type_change(self, widget, qtbot):
        """検索タイプ変更のテスト"""
        with qtbot.waitSignal(widget.search_type_changed, timeout=1000) as blocker:
            widget.full_text_radio.setChecked(True)
            widget._on_search_type_changed(widget.full_text_radio)

        assert blocker.args[0] == SearchType.FULL_TEXT
        assert widget.get_search_type() == SearchType.FULL_TEXT

    def test_set_search_type(self, widget):
        """検索タイプ設定のテスト"""
        widget.set_search_type(SearchType.SEMANTIC)

        assert widget.get_search_type() == SearchType.SEMANTIC
        assert widget.semantic_radio.isChecked()


class TestAdvancedSearchOptions:
    """高度な検索オプションウィジェットのテスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()

    @pytest.fixture
    def widget(self, app):
        """AdvancedSearchOptionsのフィクスチャ"""
        return AdvancedSearchOptions()

    def test_initialization(self, widget):
        """初期化のテスト"""
        assert not widget.isChecked()  # 初期状態では折りたたまれている
        assert widget.result_limit.value() == 100
        assert widget.full_text_weight.value() == 60
        assert widget.semantic_weight.value() == 40

    def test_file_type_selection(self, widget):
        """ファイルタイプ選択のテスト"""
        options = widget.get_search_options()

        # デフォルトでは全てのファイルタイプが選択されている
        expected_types = [ft for ft in FileType if ft != FileType.UNKNOWN]
        assert set(options["file_types"]) == set(expected_types)

    def test_date_filter(self, widget):
        """日付フィルターのテスト"""
        # 日付フィルターを有効化
        widget.date_filter_enabled.setChecked(True)
        widget._on_date_filter_toggled(True)

        assert widget.date_from.isEnabled()
        assert widget.date_to.isEnabled()

        options = widget.get_search_options()
        assert options["date_from"] is not None
        assert options["date_to"] is not None

    def test_weight_synchronization(self, widget):
        """重みの同期テスト"""
        # 全文検索の重みを変更
        widget.full_text_weight.setValue(70)
        widget._on_full_text_weight_changed(70)

        assert widget.semantic_weight.value() == 30
        assert widget.semantic_weight_label.text() == "30%"

        # セマンティック検索の重みを変更
        widget.semantic_weight.setValue(80)
        widget._on_semantic_weight_changed(80)

        assert widget.full_text_weight.value() == 20
        assert widget.full_text_weight_label.text() == "20%"

    def test_options_changed_signal(self, widget, qtbot):
        """オプション変更シグナルのテスト"""
        with qtbot.waitSignal(widget.options_changed, timeout=1000):
            widget.result_limit.setValue(200)
            widget._emit_options_changed()


class TestSearchProgressWidget:
    """検索進捗ウィジェットのテスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()

    @pytest.fixture
    def widget(self, app):
        """SearchProgressWidgetのフィクスチャ"""
        return SearchProgressWidget()

    def test_initialization(self, widget):
        """初期化のテスト"""
        assert not widget.isVisible()  # 初期状態では非表示
        assert widget.progress_bar.maximum() == 0  # 不定進捗

    def test_search_start(self, widget):
        """検索開始のテスト"""
        widget.start_search("テスト検索中...")

        assert widget.isVisible()
        assert widget.status_label.text() == "テスト検索中..."
        assert widget.start_time is not None
        assert widget.timer.isActive()

    def test_progress_update(self, widget):
        """進捗更新のテスト"""
        widget.start_search()
        widget.update_progress("処理中...", 50)

        assert widget.status_label.text() == "処理中..."
        assert widget.progress_bar.value() == 50
        assert widget.progress_bar.maximum() == 100

    def test_search_finish(self, widget, qtbot):
        """検索完了のテスト"""
        widget.start_search()
        widget.finish_search("完了しました")

        assert widget.status_label.text() == "完了しました"
        assert not widget.timer.isActive()

        # 2秒後に非表示になることを確認
        def check_visibility():
            assert not widget.isVisible()

        QTimer.singleShot(2100, check_visibility)

    def test_cancel_signal(self, widget, qtbot):
        """キャンセルシグナルのテスト"""
        widget.start_search()

        with qtbot.waitSignal(widget.cancel_requested, timeout=1000):
            widget.cancel_button.click()

        assert widget.status_label.text() == "キャンセル中..."
        assert not widget.cancel_button.isEnabled()


class TestSearchHistoryWidget:
    """検索履歴ウィジェットのテスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()

    @pytest.fixture
    def widget(self, app):
        """SearchHistoryWidgetのフィクスチャ"""
        return SearchHistoryWidget()

    @pytest.fixture
    def sample_recent_searches(self):
        """サンプルの最近の検索データ"""
        return [
            {
                "query": "テスト検索1",
                "timestamp": datetime.now() - timedelta(minutes=5),
                "result_count": 10,
            },
            {
                "query": "テスト検索2",
                "timestamp": datetime.now() - timedelta(hours=1),
                "result_count": 5,
            },
        ]

    @pytest.fixture
    def sample_popular_searches(self):
        """サンプルの人気検索データ"""
        return [
            {"query": "人気検索1", "search_count": 15, "avg_results": 8.5},
            {"query": "人気検索2", "search_count": 10, "avg_results": 12.0},
        ]

    def test_initialization(self, widget):
        """初期化のテスト"""
        assert widget.tab_widget.count() == 2
        assert widget.tab_widget.tabText(0) == "最近の検索"
        assert widget.tab_widget.tabText(1) == "人気の検索"

    def test_recent_searches_update(self, widget, sample_recent_searches):
        """最近の検索更新のテスト"""
        widget.update_recent_searches(sample_recent_searches)

        assert widget.recent_list.count() == 2

        # 最初のアイテムの内容を確認
        first_item = widget.recent_list.item(0)
        assert "テスト検索1" in first_item.text()
        assert "(10件)" in first_item.text()
        assert first_item.data(Qt.UserRole) == "テスト検索1"

    def test_popular_searches_update(self, widget, sample_popular_searches):
        """人気検索更新のテスト"""
        widget.update_popular_searches(sample_popular_searches)

        assert widget.popular_list.count() == 2

        # 最初のアイテムの内容を確認
        first_item = widget.popular_list.item(0)
        assert "人気検索1" in first_item.text()
        assert "(15回" in first_item.text()
        assert first_item.data(Qt.UserRole) == "人気検索1"

    def test_history_selection(self, widget, sample_recent_searches, qtbot):
        """履歴選択のテスト"""
        widget.update_recent_searches(sample_recent_searches)

        with qtbot.waitSignal(widget.history_selected, timeout=1000) as blocker:
            first_item = widget.recent_list.item(0)
            widget._on_recent_item_selected(first_item)

        assert blocker.args[0] == "テスト検索1"


class TestSearchInterface:
    """統合検索インターフェースのテスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()

    @pytest.fixture
    def widget(self, app):
        """SearchInterfaceのフィクスチャ"""
        return SearchInterface()

    def test_initialization(self, widget):
        """初期化のテスト"""
        assert widget.search_input is not None
        assert widget.search_type_selector is not None
        assert widget.advanced_options is not None
        assert widget.progress_widget is not None
        assert widget.history_widget is not None
        assert not widget.is_searching

    def test_search_execution(self, widget, qtbot):
        """検索実行のテスト"""
        widget.search_input.setText("テスト検索")

        with qtbot.waitSignal(widget.search_requested, timeout=1000) as blocker:
            widget._execute_search()

        search_query = blocker.args[0]
        assert search_query.query_text == "テスト検索"
        assert search_query.search_type == SearchType.HYBRID  # デフォルト
        assert widget.is_searching
        assert not widget.search_button.isEnabled()

    def test_empty_search_prevention(self, widget, qtbot):
        """空検索の防止テスト"""
        widget.search_input.setText("")

        with qtbot.assertNotEmitted(widget.search_requested):
            widget._execute_search()

        assert not widget.is_searching

    def test_search_completion(self, widget):
        """検索完了のテスト"""
        # 検索状態を設定
        widget.is_searching = True
        widget.search_button.setEnabled(False)
        widget.search_button.setText("検索中...")

        # 検索完了を通知
        results = []
        execution_time = 1.5
        widget.on_search_completed(results, execution_time)

        assert not widget.is_searching
        assert widget.search_button.isEnabled()
        assert widget.search_button.text() == "検索"

    def test_search_error_handling(self, widget):
        """検索エラー処理のテスト"""
        # 検索状態を設定
        widget.is_searching = True
        widget.search_button.setEnabled(False)

        # エラーを通知
        error_message = "テストエラー"
        widget.on_search_error(error_message)

        assert not widget.is_searching
        assert widget.search_button.isEnabled()

    def test_search_cancellation(self, widget, qtbot):
        """検索キャンセルのテスト"""
        # 検索状態を設定
        widget.is_searching = True

        with qtbot.waitSignal(widget.search_cancelled, timeout=1000):
            widget._cancel_search()

        assert not widget.is_searching
        assert widget.search_button.isEnabled()

    def test_search_query_building(self, widget):
        """検索クエリ構築のテスト"""
        # 検索条件を設定
        widget.search_input.setText("テスト検索")
        widget.search_type_selector.set_search_type(SearchType.SEMANTIC)
        widget.advanced_options.result_limit.setValue(50)

        query = widget._build_search_query("テスト検索")

        assert query.query_text == "テスト検索"
        assert query.search_type == SearchType.SEMANTIC
        assert query.limit == 50

    def test_search_suggestions_update(self, widget):
        """検索提案更新のテスト"""
        suggestions = ["提案1", "提案2", "提案3"]
        widget.update_search_suggestions(suggestions)

        assert widget.search_input.suggestions == suggestions

    def test_search_history_update(self, widget):
        """検索履歴更新のテスト"""
        recent_searches = [
            {"query": "最近の検索", "timestamp": datetime.now(), "result_count": 5}
        ]
        popular_searches = [
            {"query": "人気の検索", "search_count": 10, "avg_results": 7.5}
        ]

        widget.update_search_history(recent_searches, popular_searches)

        assert widget.history_widget.recent_searches == recent_searches
        assert widget.history_widget.popular_searches == popular_searches


class TestSearchWorkerThread:
    """検索ワーカースレッドのテスト"""

    @pytest.fixture
    def mock_search_manager(self):
        """モックの検索マネージャー"""
        manager = Mock()
        manager.search.return_value = []
        return manager

    @pytest.fixture
    def sample_query(self):
        """サンプル検索クエリ"""
        return SearchQuery(query_text="テスト検索", search_type=SearchType.HYBRID)

    def test_successful_search(self, mock_search_manager, sample_query, qtbot):
        """成功する検索のテスト"""
        worker = SearchWorkerThread(mock_search_manager, sample_query)

        with qtbot.waitSignal(worker.search_completed, timeout=5000) as blocker:
            worker.start()
            worker.wait()

        results, execution_time = blocker.args
        assert isinstance(results, list)
        assert isinstance(execution_time, float)
        assert execution_time > 0

    def test_search_error(self, mock_search_manager, sample_query, qtbot):
        """検索エラーのテスト"""
        mock_search_manager.search.side_effect = SearchError("テストエラー")
        worker = SearchWorkerThread(mock_search_manager, sample_query)

        with qtbot.waitSignal(worker.search_error, timeout=5000) as blocker:
            worker.start()
            worker.wait()

        error_message = blocker.args[0]
        assert "テストエラー" in error_message

    def test_search_cancellation(self, mock_search_manager, sample_query):
        """検索キャンセルのテスト"""
        worker = SearchWorkerThread(mock_search_manager, sample_query)
        worker.cancel()

        assert worker.is_cancelled


class TestSearchInterfaceIntegration:
    """検索インターフェース統合テスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()

    @pytest.fixture
    def search_interface(self, app):
        """SearchInterfaceのフィクスチャ"""
        return SearchInterface()

    @pytest.fixture
    def mock_search_manager(self):
        """モックの検索マネージャー"""
        manager = Mock()

        # サンプル検索結果を作成
        sample_document = Document(
            id="test_doc_1",
            file_path="/test/document.txt",
            title="テストドキュメント",
            content="これはテストドキュメントです。",
            file_type=FileType.TEXT,
            size=100,
            created_date=datetime.now(),
            modified_date=datetime.now(),
            indexed_date=datetime.now(),
        )

        sample_result = SearchResult(
            document=sample_document,
            score=0.85,
            search_type=SearchType.HYBRID,
            snippet="これはテストドキュメント...",
            highlighted_terms=["テスト"],
            relevance_explanation="ハイブリッド検索結果",
        )

        manager.search.return_value = [sample_result]
        return manager

    def test_complete_search_workflow(
        self, search_interface, mock_search_manager, qtbot
    ):
        """完全な検索ワークフローのテスト"""
        # 1. 検索テキストを入力
        search_interface.set_search_text("テスト検索")
        assert search_interface.get_search_text() == "テスト検索"

        # 2. 検索タイプを変更
        search_interface.search_type_selector.set_search_type(SearchType.FULL_TEXT)
        assert (
            search_interface.search_type_selector.get_search_type()
            == SearchType.FULL_TEXT
        )

        # 3. 高度なオプションを設定
        search_interface.advanced_options.setChecked(True)
        search_interface.advanced_options.result_limit.setValue(50)

        # 4. 検索を実行
        with qtbot.waitSignal(
            search_interface.search_requested, timeout=1000
        ) as blocker:
            search_interface._execute_search()

        search_query = blocker.args[0]
        assert search_query.query_text == "テスト検索"
        assert search_query.search_type == SearchType.FULL_TEXT
        assert search_query.limit == 50

        # 5. 検索完了を通知
        results = mock_search_manager.search.return_value
        search_interface.on_search_completed(results, 1.2)

        assert not search_interface.is_searching
        assert search_interface.search_button.isEnabled()

    def test_search_history_integration(self, search_interface, qtbot):
        """検索履歴統合のテスト"""
        # 履歴データを更新
        recent_searches = [
            {"query": "履歴検索1", "timestamp": datetime.now(), "result_count": 3}
        ]
        popular_searches = [
            {"query": "人気検索1", "search_count": 5, "avg_results": 4.0}
        ]

        search_interface.update_search_history(recent_searches, popular_searches)

        # 履歴から検索を選択
        with qtbot.waitSignal(search_interface.search_requested, timeout=1000):
            search_interface._on_history_selected("履歴検索1")
            search_interface._execute_search()

        assert search_interface.get_search_text() == "履歴検索1"

    def test_search_suggestions_integration(self, search_interface):
        """検索提案統合のテスト"""
        # 提案を更新
        suggestions = ["提案検索1", "提案検索2"]
        search_interface.update_search_suggestions(suggestions)

        # 提案が検索入力に反映されることを確認
        assert search_interface.search_input.suggestions == suggestions

        # 提案選択のテスト
        search_interface._on_suggestion_selected("提案検索1")
        assert search_interface.get_search_text() == "提案検索1"

    def test_advanced_options_integration(self, search_interface):
        """高度なオプション統合のテスト"""
        # オプションを展開
        search_interface.advanced_options.setChecked(True)

        # ファイルタイプフィルターを設定
        for (
            file_type,
            checkbox,
        ) in search_interface.advanced_options.file_type_checkboxes.items():
            if file_type == FileType.PDF:
                checkbox.setChecked(True)
            else:
                checkbox.setChecked(False)

        # 日付フィルターを有効化
        search_interface.advanced_options.date_filter_enabled.setChecked(True)

        # 検索クエリを構築
        query = search_interface._build_search_query("テスト")

        assert FileType.PDF in query.file_types
        assert len(query.file_types) == 1
        assert query.date_from is not None
        assert query.date_to is not None

    def test_error_handling_integration(self, search_interface, qtbot):
        """エラーハンドリング統合のテスト"""
        # 検索状態を設定
        search_interface.is_searching = True

        # エラーを発生させる
        error_message = "統合テストエラー"
        search_interface.on_search_error(error_message)

        # 状態がリセットされることを確認
        assert not search_interface.is_searching
        assert search_interface.search_button.isEnabled()
        assert search_interface.search_button.text() == "検索"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
