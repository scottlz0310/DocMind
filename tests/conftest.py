"""
pytest設定とフィクスチャ定義

テストスイート全体で使用される共通フィクスチャとセットアップ
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import Config
from tests.test_data_generator import TestDataGenerator


@pytest.fixture(scope="session")
def test_data_dir():
    """
    テストセッション全体で使用するテストデータディレクトリ
    """
    temp_dir = tempfile.mkdtemp(prefix="docmind_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_config(test_data_dir):
    """
    テスト用設定オブジェクト
    """
    config = Config()
    # 設定値を直接更新
    config._config.update(
        {
            "data_directory": str(test_data_dir / "data"),
            "whoosh_index_dir": str(test_data_dir / "index"),
            "embeddings_file": str(test_data_dir / "embeddings.pkl"),
            "database_file": str(test_data_dir / "test_documents.db"),
            "log_file": str(test_data_dir / "logs" / "docmind.log"),
        }
    )

    # ディレクトリを作成
    (test_data_dir / "data").mkdir(parents=True, exist_ok=True)
    (test_data_dir / "index").mkdir(parents=True, exist_ok=True)
    (test_data_dir / "logs").mkdir(parents=True, exist_ok=True)

    return config


@pytest.fixture
def test_data_generator(test_data_dir):
    """
    テストデータジェネレーター
    """
    generator = TestDataGenerator(str(test_data_dir / "test_documents"))
    yield generator
    generator.cleanup()


@pytest.fixture
def sample_documents(test_data_generator):
    """
    サンプルドキュメントセット
    """
    return test_data_generator.create_comprehensive_test_dataset(
        text_count=5, markdown_count=3, pdf_count=2, word_count=2, excel_count=1
    )


@pytest.fixture
def large_document_set(test_data_generator):
    """
    パフォーマンステスト用の大きなドキュメントセット
    """
    return test_data_generator.create_comprehensive_test_dataset(
        text_count=100, markdown_count=75, pdf_count=25, word_count=25, excel_count=10
    )


@pytest.fixture
def mock_database(test_config):
    """
    モックデータベースマネージャー
    """
    with patch("src.data.database.DatabaseManager") as mock_db:
        db_instance = Mock()
        mock_db.return_value = db_instance

        # 基本的なメソッドをモック
        db_instance.initialize.return_value = None
        db_instance.add_document.return_value = True
        db_instance.get_document.return_value = None
        db_instance.update_document.return_value = True
        db_instance.delete_document.return_value = True
        db_instance.get_all_documents.return_value = []

        yield db_instance


@pytest.fixture
def mock_index_manager(test_config):
    """
    モックインデックスマネージャー
    """
    with patch("src.core.index_manager.IndexManager") as mock_index:
        index_instance = Mock()
        mock_index.return_value = index_instance

        # 基本的なメソッドをモック
        index_instance.create_index.return_value = None
        index_instance.add_document.return_value = None
        index_instance.search_text.return_value = []
        index_instance.update_document.return_value = None
        index_instance.remove_document.return_value = None

        yield index_instance


@pytest.fixture
def mock_embedding_manager(test_config):
    """
    モック埋め込みマネージャー
    """
    with patch("src.core.embedding_manager.EmbeddingManager") as mock_embedding:
        embedding_instance = Mock()
        mock_embedding.return_value = embedding_instance

        # 基本的なメソッドをモック
        embedding_instance.load_model.return_value = None
        embedding_instance.generate_embedding.return_value = [0.1] * 384  # MiniLM次元
        embedding_instance.search_similar.return_value = []
        embedding_instance.add_document_embedding.return_value = None

        yield embedding_instance


@pytest.fixture
def mock_qt_application():
    """
    QTアプリケーションのモック（GUIテスト用）
    """
    try:
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        yield app

        # テスト後のクリーンアップ
        app.processEvents()

    except ImportError:
        # PySide6が利用できない場合はモックを使用
        mock_app = Mock()
        yield mock_app


@pytest.fixture(autouse=True)
def setup_test_environment(test_config):
    """
    各テストの前後で実行される環境セットアップ
    """
    # テスト前のセットアップ
    original_env = os.environ.copy()

    # テスト用環境変数を設定
    os.environ["DOCMIND_TEST_MODE"] = "1"
    os.environ["DOCMIND_DATA_DIR"] = str(test_config.data_dir)

    yield

    # テスト後のクリーンアップ
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def performance_timer():
    """
    パフォーマンス測定用タイマー
    """
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()
            return self.elapsed_time

        @property
        def elapsed_time(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


@pytest.fixture
def memory_monitor():
    """
    メモリ使用量監視用フィクスチャ
    """
    import os

    import psutil

    class MemoryMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.initial_memory = self.get_memory_usage()

        def get_memory_usage(self):
            """現在のメモリ使用量を取得（MB）"""
            return self.process.memory_info().rss / 1024 / 1024

        def get_memory_increase(self):
            """初期値からのメモリ増加量を取得（MB）"""
            current = self.get_memory_usage()
            return current - self.initial_memory

    return MemoryMonitor()


# テストマーカーの定義
def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line("markers", "slow: 実行時間が長いテスト")
    config.addinivalue_line("markers", "integration: 統合テスト")
    config.addinivalue_line("markers", "performance: パフォーマンステスト")
    config.addinivalue_line("markers", "gui: GUIテスト")
    config.addinivalue_line("markers", "unit: ユニットテスト")


# テスト収集時のフィルタリング
def pytest_collection_modifyitems(config, items):
    """テスト収集時の処理"""
    # 環境に応じてテストをスキップ
    skip_gui = pytest.mark.skip(reason="GUI環境が利用できません")
    skip_slow = pytest.mark.skip(reason="高速テストモードです")

    for item in items:
        # GUIテストのスキップ判定
        if "gui" in item.keywords:
            try:
                import PySide6
            except ImportError:
                item.add_marker(skip_gui)

        # 高速テストモードでのスローテストスキップ
        if config.getoption("--fast") and "slow" in item.keywords:
            item.add_marker(skip_slow)


def pytest_addoption(parser):
    """コマンドラインオプションの追加"""
    parser.addoption(
        "--fast",
        action="store_true",
        default=False,
        help="高速テストモード（スローテストをスキップ）",
    )
    parser.addoption(
        "--performance",
        action="store_true",
        default=False,
        help="パフォーマンステストを実行",
    )
