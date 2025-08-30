"""
Config強化テスト

設定管理・永続化・バリデーション・復旧テスト
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from src.utils.config import Config


class TestConfig:
    """設定管理コアロジックテスト"""

    @pytest.fixture
    def temp_config_dir(self):
        """テスト用一時設定ディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_config_initialization(self):
        """Config初期化テスト"""
        config = Config()

        assert config is not None
        assert hasattr(config, 'get')
        assert hasattr(config, 'set')

    def test_default_values(self):
        """デフォルト値テスト"""
        config = Config()

        # デフォルト値の確認
        assert config.get('data_directory') is not None
        assert config.get('log_level') == 'INFO'
        assert config.get('max_documents') > 0

    def test_get_set_operations(self):
        """設定値の取得・設定テスト"""
        config = Config()

        # 設定値の設定と取得
        test_key = 'test_setting'
        test_value = 'test_value'

        config.set(test_key, test_value)
        assert config.get(test_key) == test_value

    def test_config_persistence(self, temp_config_dir):
        """設定の永続化テスト"""
        config_file = temp_config_dir / "test_config.json"

        # 設定を保存
        config = Config(str(config_file))
        config.set('test_key', 'test_value')
        config.save_config()

        # 新しいインスタンスで設定を読み込み
        new_config = Config(str(config_file))
        assert new_config.get('test_key') == 'test_value'

    def test_validation(self):
        """設定値の検証テスト"""
        config = Config()

        # 検証機能のテスト
        warnings = config.validate_settings()
        assert isinstance(warnings, list)

    def test_indexed_folders_management(self):
        """インデックス対象フォルダ管理テスト"""
        config = Config()

        # フォルダ追加
        test_folder = "/test/folder"
        result = config.add_indexed_folder(test_folder)
        assert result is True

        # フォルダリスト確認
        folders = config.get_indexed_folders()
        assert test_folder in folders

        # フォルダ削除
        result = config.remove_indexed_folder(test_folder)
        assert result is True

        folders = config.get_indexed_folders()
        assert test_folder not in folders

    def test_path_methods(self):
        """パス取得メソッドテスト"""
        config = Config()

        # 各種パス取得
        assert config.get_database_path() is not None
        assert config.get_embeddings_path() is not None
        assert config.get_index_path() is not None
        assert config.get_log_file_path() is not None

    def test_settings_groups(self):
        """設定グループ取得テスト"""
        config = Config()

        # 各種設定グループ
        search_settings = config.get_search_settings()
        assert isinstance(search_settings, dict)
        assert 'max_results' in search_settings

        performance_settings = config.get_performance_settings()
        assert isinstance(performance_settings, dict)
        assert 'batch_size' in performance_settings

        font_settings = config.get_font_settings()
        assert isinstance(font_settings, dict)
        assert 'family' in font_settings

    def test_export_import_settings(self, temp_config_dir):
        """設定エクスポート・インポートテスト"""
        config = Config()
        export_file = temp_config_dir / "export.json"

        # テスト設定
        config.set('test_export', 'export_value')

        # エクスポート
        result = config.export_settings(str(export_file))
        assert result is True
        assert export_file.exists()

        # 新しいConfigでインポート
        new_config = Config()
        result = new_config.import_settings(str(export_file))
        assert result is True
        assert new_config.get('test_export') == 'export_value'

    def test_reset_to_defaults(self):
        """デフォルト値リセットテスト"""
        config = Config()

        # カスタム値設定
        config.set('custom_key', 'custom_value')
        assert config.get('custom_key') == 'custom_value'

        # リセット
        config.reset_to_defaults()
        assert config.get('custom_key') is None
        assert config.get('log_level') == 'INFO'  # デフォルト値確認
