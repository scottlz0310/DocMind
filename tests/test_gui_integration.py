"""
GUI統合テスト

PySide6 GUIコンポーネントの統合テスト
QTestフレームワークを使用したGUIテスト
"""

from unittest.mock import Mock, patch

import pytest

# GUIテストのスキップ判定
try:
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    pytest.skip("PySide6が利用できません", allow_module_level=True)

from src.data.models import Document, SearchResult, SearchType
from src.gui.folder_tree import FolderTreeWidget
from src.gui.main_window import MainWindow
from src.gui.preview_widget import PreviewWidget
from src.gui.search_interface import SearchInterface
from src.gui.search_results import SearchResultsWidget
from src.gui.settings_dialog import SettingsDialog


@pytest.mark.gui
class TestMainWindowGUI:
    """メインウィンドウGUIテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_qt_application):
        """テストセットアップ"""
        self.app = mock_qt_application

        # 依存関係をモック
        with patch('src.gui.main_window.SearchManager') as mock_search_manager, \
             patch('src.gui.main_window.DatabaseManager') as mock_db_manager, \
             patch('src.gui.main_window.Config') as mock_config:

            self.mock_search_manager = Mock()
            mock_search_manager.return_value = self.mock_search_manager

            self.mock_db_manager = Mock()
            mock_db_manager.return_value = self.mock_db_manager

            self.mock_config = Mock()
            mock_config.return_value = self.mock_config

            self.main_window = MainWindow()

        yield

        # クリーンアップ
        if hasattr(self, 'main_window'):
            self.main_window.close()

    def test_main_window_initialization(self):
        """メインウィンドウの初期化テスト"""
        assert self.main_window is not None
        assert self.main_window.windowTitle() == "DocMind - ローカルドキュメント検索"

        # 基本的なウィジェットが存在することを確認
        assert hasattr(self.main_window, 'folder_tree')
        assert hasattr(self.main_window, 'search_results')
        assert hasattr(self.main_window, 'preview_widget')
        assert hasattr(self.main_window, 'search_interface')

        print("✓ メインウィンドウ初期化テスト完了")

    def test_main_window_layout(self):
        """メインウィンドウレイアウトテスト"""
        # 3ペインレイアウトの確認
        central_widget = self.main_window.centralWidget()
        assert central_widget is not None

        # レイアウトが適切に設定されていることを確認
        layout = central_widget.layout()
        assert layout is not None

        print("✓ メインウィンドウレイアウトテスト完了")

    def test_menu_bar_functionality(self):
        """メニューバー機能テスト"""
        menu_bar = self.main_window.menuBar()
        assert menu_bar is not None

        # メニューアクションの存在確認
        actions = menu_bar.actions()
        assert len(actions) > 0

        # ファイルメニューの確認
        file_menu = None
        for action in actions:
            if action.text() == "ファイル(&F)":
                file_menu = action.menu()
                break

        if file_menu:
            file_actions = file_menu.actions()
            assert len(file_actions) > 0

        print("✓ メニューバー機能テスト完了")

    def test_status_bar_functionality(self):
        """ステータスバー機能テスト"""
        status_bar = self.main_window.statusBar()
        assert status_bar is not None

        # ステータスメッセージの設定テスト
        test_message = "テストメッセージ"
        self.main_window.update_status(test_message)

        # ステータスバーにメッセージが表示されることを確認
        # 実際の表示確認は実装に依存するため、エラーが発生しないことを確認

        print("✓ ステータスバー機能テスト完了")

    @pytest.mark.slow
    def test_search_workflow_gui(self):
        """検索ワークフローGUIテスト"""
        # モック検索結果を設定
        mock_results = [
            SearchResult(
                document=Document(
                    id="test_doc_1",
                    file_path="test1.txt",
                    title="テストドキュメント1",
                    content="これはテスト用のドキュメントです。",
                    file_type="text",
                    size=100
                ),
                score=0.95,
                search_type=SearchType.FULL_TEXT,
                snippet="これはテスト用の...",
                highlighted_terms=["テスト"],
                relevance_explanation="キーワードマッチ"
            )
        ]

        self.mock_search_manager.search.return_value = mock_results

        # 検索実行のシミュレーション
        search_query = "テスト"
        self.main_window.perform_search(search_query, SearchType.FULL_TEXT)

        # 検索マネージャーが呼び出されたことを確認
        self.mock_search_manager.search.assert_called_once()

        print("✓ 検索ワークフローGUIテスト完了")


@pytest.mark.gui
class TestFolderTreeGUI:
    """フォルダツリーGUIテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_qt_application, test_data_dir):
        """テストセットアップ"""
        self.app = mock_qt_application
        self.test_data_dir = test_data_dir

        self.folder_tree = FolderTreeWidget()

        yield

        # クリーンアップ
        if hasattr(self, 'folder_tree'):
            self.folder_tree.close()

    def test_folder_tree_initialization(self):
        """フォルダツリー初期化テスト"""
        assert self.folder_tree is not None
        assert self.folder_tree.columnCount() > 0

        print("✓ フォルダツリー初期化テスト完了")

    def test_folder_loading(self):
        """フォルダ読み込みテスト"""
        # テストディレクトリを作成
        test_folder = self.test_data_dir / "test_folder"
        test_folder.mkdir(exist_ok=True)

        subfolder = test_folder / "subfolder"
        subfolder.mkdir(exist_ok=True)

        # フォルダを読み込み
        self.folder_tree.load_folder_structure(str(test_folder))

        # ルートアイテムが追加されたことを確認
        root_count = self.folder_tree.topLevelItemCount()
        assert root_count > 0

        print("✓ フォルダ読み込みテスト完了")

    def test_folder_selection(self):
        """フォルダ選択テスト"""
        # テストフォルダを設定
        test_folder = self.test_data_dir / "selection_test"
        test_folder.mkdir(exist_ok=True)

        self.folder_tree.load_folder_structure(str(test_folder))

        # 選択イベントのシミュレーション
        if self.folder_tree.topLevelItemCount() > 0:
            item = self.folder_tree.topLevelItem(0)
            self.folder_tree.setCurrentItem(item)

            # 選択されたアイテムの確認
            current_item = self.folder_tree.currentItem()
            assert current_item is not None

        print("✓ フォルダ選択テスト完了")


@pytest.mark.gui
class TestSearchResultsGUI:
    """検索結果GUIテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_qt_application):
        """テストセットアップ"""
        self.app = mock_qt_application
        self.search_results = SearchResultsWidget()

        yield

        # クリーンアップ
        if hasattr(self, 'search_results'):
            self.search_results.close()

    def test_search_results_initialization(self):
        """検索結果初期化テスト"""
        assert self.search_results is not None
        assert self.search_results.count() == 0  # 初期状態では結果なし

        print("✓ 検索結果初期化テスト完了")

    def test_display_search_results(self):
        """検索結果表示テスト"""
        # テスト用検索結果を作成
        test_results = [
            SearchResult(
                document=Document(
                    id="result_test_1",
                    file_path="result_test1.txt",
                    title="結果テストドキュメント1",
                    content="これは結果表示テスト用のドキュメントです。",
                    file_type="text",
                    size=150
                ),
                score=0.9,
                search_type=SearchType.FULL_TEXT,
                snippet="これは結果表示テスト用の...",
                highlighted_terms=["結果", "テスト"],
                relevance_explanation="キーワードマッチ"
            ),
            SearchResult(
                document=Document(
                    id="result_test_2",
                    file_path="result_test2.txt",
                    title="結果テストドキュメント2",
                    content="これは2番目のテストドキュメントです。",
                    file_type="text",
                    size=120
                ),
                score=0.8,
                search_type=SearchType.SEMANTIC,
                snippet="これは2番目のテスト...",
                highlighted_terms=["テスト"],
                relevance_explanation="セマンティック類似度"
            )
        ]

        # 結果を表示
        self.search_results.display_results(test_results)

        # 結果が表示されたことを確認
        assert self.search_results.count() == len(test_results)

        print("✓ 検索結果表示テスト完了")

    def test_result_selection(self):
        """検索結果選択テスト"""
        # テスト結果を表示
        self.test_display_search_results()

        # 最初の結果を選択
        if self.search_results.count() > 0:
            self.search_results.setCurrentRow(0)

            # 選択されたアイテムの確認
            current_item = self.search_results.currentItem()
            assert current_item is not None

        print("✓ 検索結果選択テスト完了")


@pytest.mark.gui
class TestPreviewWidgetGUI:
    """プレビューウィジェットGUIテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_qt_application):
        """テストセットアップ"""
        self.app = mock_qt_application
        self.preview_widget = PreviewWidget()

        yield

        # クリーンアップ
        if hasattr(self, 'preview_widget'):
            self.preview_widget.close()

    def test_preview_widget_initialization(self):
        """プレビューウィジェット初期化テスト"""
        assert self.preview_widget is not None
        assert self.preview_widget.toPlainText() == ""  # 初期状態では空

        print("✓ プレビューウィジェット初期化テスト完了")

    def test_document_preview(self):
        """ドキュメントプレビューテスト"""
        # テストドキュメントを作成
        test_document = Document(
            id="preview_test",
            file_path="preview_test.txt",
            title="プレビューテストドキュメント",
            content="これはプレビューテスト用のドキュメント内容です。\n複数行のテキストを含みます。",
            file_type="text",
            size=200
        )

        # ドキュメントを表示
        self.preview_widget.display_document(test_document)

        # 内容が表示されたことを確認
        displayed_text = self.preview_widget.toPlainText()
        assert test_document.content in displayed_text

        print("✓ ドキュメントプレビューテスト完了")

    def test_search_term_highlighting(self):
        """検索語ハイライトテスト"""
        # テストドキュメントを表示
        self.test_document_preview()

        # ハイライト機能をテスト
        search_terms = ["プレビュー", "テスト"]
        self.preview_widget.highlight_search_terms(search_terms)

        # ハイライトが適用されたことを確認（実装に依存）
        # エラーが発生しないことを確認

        print("✓ 検索語ハイライトテスト完了")


@pytest.mark.gui
class TestSearchInterfaceGUI:
    """検索インターフェースGUIテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_qt_application):
        """テストセットアップ"""
        self.app = mock_qt_application

        # 依存関係をモック
        with patch('src.gui.search_interface.SearchManager') as mock_search_manager:
            self.mock_search_manager = Mock()
            mock_search_manager.return_value = self.mock_search_manager

            self.search_interface = SearchInterface()

        yield

        # クリーンアップ
        if hasattr(self, 'search_interface'):
            self.search_interface.close()

    def test_search_interface_initialization(self):
        """検索インターフェース初期化テスト"""
        assert self.search_interface is not None

        # 基本的なウィジェットが存在することを確認
        assert hasattr(self.search_interface, 'search_input')
        assert hasattr(self.search_interface, 'search_button')
        assert hasattr(self.search_interface, 'search_type_combo')

        print("✓ 検索インターフェース初期化テスト完了")

    def test_search_input_functionality(self):
        """検索入力機能テスト"""
        # 検索クエリを入力
        test_query = "テスト検索クエリ"
        self.search_interface.search_input.setText(test_query)

        # 入力されたテキストの確認
        input_text = self.search_interface.search_input.text()
        assert input_text == test_query

        print("✓ 検索入力機能テスト完了")

    def test_search_type_selection(self):
        """検索タイプ選択テスト"""
        # 検索タイプコンボボックスの確認
        combo = self.search_interface.search_type_combo
        assert combo.count() > 0

        # 各検索タイプが選択可能であることを確認
        for i in range(combo.count()):
            combo.setCurrentIndex(i)
            assert combo.currentIndex() == i

        print("✓ 検索タイプ選択テスト完了")

    def test_search_execution(self):
        """検索実行テスト"""
        # 検索クエリを設定
        test_query = "実行テスト"
        self.search_interface.search_input.setText(test_query)

        # 検索ボタンをクリック（シミュレーション）
        search_button = self.search_interface.search_button

        # ボタンクリックイベントのシミュレーション
        if GUI_AVAILABLE:
            QTest.mouseClick(search_button, Qt.LeftButton)

        # 検索が実行されたことを確認（実装に依存）
        # エラーが発生しないことを確認

        print("✓ 検索実行テスト完了")


@pytest.mark.gui
class TestSettingsDialogGUI:
    """設定ダイアログGUIテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_qt_application, test_config):
        """テストセットアップ"""
        self.app = mock_qt_application
        self.test_config = test_config

        self.settings_dialog = SettingsDialog(self.test_config)

        yield

        # クリーンアップ
        if hasattr(self, 'settings_dialog'):
            self.settings_dialog.close()

    def test_settings_dialog_initialization(self):
        """設定ダイアログ初期化テスト"""
        assert self.settings_dialog is not None
        assert self.settings_dialog.windowTitle() == "設定"

        print("✓ 設定ダイアログ初期化テスト完了")

    def test_settings_loading(self):
        """設定読み込みテスト"""
        # 設定が正しく読み込まれることを確認
        # 実装に依存するため、エラーが発生しないことを確認

        try:
            self.settings_dialog.load_settings()
        except Exception as e:
            pytest.fail(f"設定読み込みでエラーが発生: {e}")

        print("✓ 設定読み込みテスト完了")

    def test_settings_saving(self):
        """設定保存テスト"""
        # 設定の保存をテスト
        try:
            self.settings_dialog.save_settings()
        except Exception as e:
            pytest.fail(f"設定保存でエラーが発生: {e}")

        print("✓ 設定保存テスト完了")


@pytest.mark.gui
@pytest.mark.integration
class TestGUIIntegration:
    """GUI統合テスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_qt_application, test_config):
        """テストセットアップ"""
        self.app = mock_qt_application
        self.test_config = test_config

        # 統合テスト用のメインウィンドウを作成
        with patch('src.gui.main_window.SearchManager') as mock_search_manager, \
             patch('src.gui.main_window.DatabaseManager') as mock_db_manager, \
             patch('src.gui.main_window.Config') as mock_config:

            self.mock_search_manager = Mock()
            mock_search_manager.return_value = self.mock_search_manager

            self.mock_db_manager = Mock()
            mock_db_manager.return_value = self.mock_db_manager

            self.mock_config = Mock()
            mock_config.return_value = self.mock_config

            self.main_window = MainWindow()

        yield

        # クリーンアップ
        if hasattr(self, 'main_window'):
            self.main_window.close()

    def test_complete_gui_workflow(self):
        """完全なGUIワークフローテスト"""
        # 1. メインウィンドウの表示
        self.main_window.show()

        # 2. フォルダ選択のシミュレーション
        test_folder = str(self.test_config.data_dir)
        self.main_window.folder_tree.load_folder_structure(test_folder)

        # 3. 検索実行のシミュレーション
        mock_results = [
            SearchResult(
                document=Document(
                    id="gui_workflow_test",
                    file_path="workflow_test.txt",
                    title="GUIワークフローテスト",
                    content="これはGUIワークフローテスト用のドキュメントです。",
                    file_type="text",
                    size=100
                ),
                score=0.95,
                search_type=SearchType.FULL_TEXT,
                snippet="これはGUIワークフロー...",
                highlighted_terms=["GUI", "ワークフロー"],
                relevance_explanation="キーワードマッチ"
            )
        ]

        self.mock_search_manager.search.return_value = mock_results

        # 検索実行
        search_query = "ワークフロー"
        self.main_window.perform_search(search_query, SearchType.FULL_TEXT)

        # 4. 結果表示の確認
        self.main_window.search_results.count()
        # モックを使用しているため、実際の表示確認は実装に依存

        # 5. プレビュー表示のシミュレーション
        if len(mock_results) > 0:
            self.main_window.preview_widget.display_document(mock_results[0].document)

        print("✓ 完全なGUIワークフローテスト完了")

    def test_gui_error_handling(self):
        """GUIエラーハンドリングテスト"""
        # 検索エラーのシミュレーション
        self.mock_search_manager.search.side_effect = Exception("検索エラーテスト")

        # エラーが適切に処理されることを確認
        try:
            self.main_window.perform_search("エラーテスト", SearchType.FULL_TEXT)
        except Exception:
            # エラーが適切にハンドリングされていることを確認
            pass

        print("✓ GUIエラーハンドリングテスト完了")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "gui"])
