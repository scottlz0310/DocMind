# -*- coding: utf-8 -*-
"""
設定管理システムのユニットテスト

Config クラスと関連機能のテストを実装します。
"""

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.config import Config


class TestConfig(unittest.TestCase):
    """設定管理システムのテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        
        # テスト用設定オブジェクトを作成
        self.config = Config(config_file=self.config_file)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        # 一時ディレクトリを再帰的に削除
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_default_values(self):
        """デフォルト値のテスト"""
        self.assertEqual(self.config.get("data_directory"), "./docmind_data")
        self.assertEqual(self.config.get("log_level"), "INFO")
        self.assertEqual(self.config.get("max_documents"), 50000)
        self.assertEqual(self.config.get("search_timeout"), 5.0)
        self.assertEqual(self.config.get("embedding_model"), "all-MiniLM-L6-v2")
        self.assertTrue(self.config.get("enable_file_watching"))
    
    def test_get_and_set(self):
        """設定値の取得と設定のテスト"""
        # 設定値の変更
        self.config.set("test_key", "test_value")
        self.assertEqual(self.config.get("test_key"), "test_value")
        
        # 存在しないキーのデフォルト値
        self.assertEqual(self.config.get("nonexistent_key", "default"), "default")
        self.assertIsNone(self.config.get("nonexistent_key"))
    
    def test_environment_variable_override(self):
        """環境変数による設定値の上書きテスト"""
        with patch.dict(os.environ, {"DOCMIND_LOG_LEVEL": "DEBUG"}):
            self.assertEqual(self.config.get("log_level"), "DEBUG")
    
    def test_save_and_load_config(self):
        """設定ファイルの保存と読み込みテスト"""
        # 設定値を変更
        self.config.set("test_setting", "test_value")
        self.config.set("max_documents", 100000)
        
        # 設定を保存
        self.assertTrue(self.config.save_config())
        self.assertTrue(os.path.exists(self.config_file))
        
        # 新しい設定オブジェクトで読み込み
        new_config = Config(config_file=self.config_file)
        self.assertEqual(new_config.get("test_setting"), "test_value")
        self.assertEqual(new_config.get("max_documents"), 100000)
    
    def test_config_file_creation(self):
        """設定ファイルの作成テスト"""
        # 存在しないディレクトリに設定ファイルを保存
        nested_config_file = os.path.join(self.temp_dir, "nested", "config.json")
        config = Config(config_file=nested_config_file)
        config.set("test", "value")
        
        self.assertTrue(config.save_config())
        self.assertTrue(os.path.exists(nested_config_file))
    
    def test_invalid_config_file(self):
        """無効な設定ファイルの処理テスト"""
        # 無効なJSONファイルを作成
        with open(self.config_file, 'w') as f:
            f.write("invalid json content")
        
        # 設定オブジェクトの作成（エラーが発生しないことを確認）
        config = Config(config_file=self.config_file)
        
        # デフォルト値が使用されることを確認
        self.assertEqual(config.get("log_level"), "INFO")
    
    def test_helper_methods(self):
        """ヘルパーメソッドのテスト"""
        # データディレクトリ
        self.assertEqual(self.config.get_data_directory(), "./docmind_data")
        self.assertEqual(self.config.data_dir, "./docmind_data")
        
        # ログレベル
        self.assertEqual(self.config.get_log_level(), "INFO")
        
        # 最大ドキュメント数
        self.assertEqual(self.config.get_max_documents(), 50000)
        
        # 検索タイムアウト
        self.assertEqual(self.config.get_search_timeout(), 5.0)
        
        # 埋め込みモデル
        self.assertEqual(self.config.get_embedding_model(), "all-MiniLM-L6-v2")
        
        # ウィンドウサイズ
        width, height = self.config.get_window_size()
        self.assertEqual(width, 1200)
        self.assertEqual(height, 800)
        
        # ファイル監視
        self.assertTrue(self.config.is_file_watching_enabled())
        
        # バッチサイズとキャッシュサイズ
        self.assertEqual(self.config.get_batch_size(), 100)
        self.assertEqual(self.config.get_cache_size(), 1000)
    
    def test_path_methods(self):
        """パス関連メソッドのテスト"""
        data_dir = self.config.get_data_directory()
        
        # データベースパス
        expected_db_path = os.path.join(data_dir, "documents.db")
        self.assertEqual(self.config.get_database_path(), expected_db_path)
        
        # 埋め込みパス
        expected_emb_path = os.path.join(data_dir, "embeddings.pkl")
        self.assertEqual(self.config.get_embeddings_path(), expected_emb_path)
        
        # インデックスパス
        expected_idx_path = os.path.join(data_dir, "whoosh_index")
        self.assertEqual(self.config.get_index_path(), expected_idx_path)
    
    def test_indexed_folders_management(self):
        """インデックス対象フォルダ管理のテスト"""
        # 初期状態では空のリスト
        self.assertEqual(self.config.get_indexed_folders(), [])
        
        # フォルダを追加
        self.assertTrue(self.config.add_indexed_folder("/path/to/folder1"))
        self.assertTrue(self.config.add_indexed_folder("/path/to/folder2"))
        
        # フォルダリストの確認
        folders = self.config.get_indexed_folders()
        self.assertEqual(len(folders), 2)
        self.assertIn("/path/to/folder1", folders)
        self.assertIn("/path/to/folder2", folders)
        
        # 重複追加の確認
        self.assertFalse(self.config.add_indexed_folder("/path/to/folder1"))
        self.assertEqual(len(self.config.get_indexed_folders()), 2)
        
        # フォルダを削除
        self.assertTrue(self.config.remove_indexed_folder("/path/to/folder1"))
        folders = self.config.get_indexed_folders()
        self.assertEqual(len(folders), 1)
        self.assertNotIn("/path/to/folder1", folders)
        
        # 存在しないフォルダの削除
        self.assertFalse(self.config.remove_indexed_folder("/nonexistent/folder"))
    
    def test_exclude_patterns(self):
        """除外パターンのテスト"""
        # デフォルトの除外パターン
        patterns = self.config.get_exclude_patterns()
        self.assertIsInstance(patterns, list)
        self.assertIn("*.tmp", patterns)
        self.assertIn("*.log", patterns)
        
        # 除外パターンの設定
        new_patterns = ["*.bak", "temp/*", "*.cache"]
        self.config.set_exclude_patterns(new_patterns)
        self.assertEqual(self.config.get_exclude_patterns(), new_patterns)
    
    def test_log_settings(self):
        """ログ設定のテスト"""
        # ログファイルパス
        log_path = self.config.get_log_file_path()
        self.assertTrue(log_path.endswith("docmind.log"))
        
        # ログ有効性
        self.assertTrue(self.config.is_console_logging_enabled())
        self.assertTrue(self.config.is_file_logging_enabled())
    
    def test_font_settings(self):
        """フォント設定のテスト"""
        font_settings = self.config.get_font_settings()
        self.assertIsInstance(font_settings, dict)
        self.assertIn("family", font_settings)
        self.assertIn("size", font_settings)
        self.assertEqual(font_settings["family"], "システムデフォルト")
        self.assertEqual(font_settings["size"], 10)
    
    def test_search_settings(self):
        """検索設定のテスト"""
        search_settings = self.config.get_search_settings()
        self.assertIsInstance(search_settings, dict)
        self.assertEqual(search_settings["max_results"], 100)
        self.assertEqual(search_settings["semantic_weight"], 50)
        self.assertTrue(search_settings["enable_search_history"])
        self.assertEqual(search_settings["search_history_limit"], 1000)
    
    def test_performance_settings(self):
        """パフォーマンス設定のテスト"""
        perf_settings = self.config.get_performance_settings()
        self.assertIsInstance(perf_settings, dict)
        self.assertTrue(perf_settings["enable_preview_cache"])
        self.assertEqual(perf_settings["preview_cache_size"], 50)
        self.assertEqual(perf_settings["batch_size"], 100)
        self.assertEqual(perf_settings["cache_size"], 1000)
    
    def test_validate_settings(self):
        """設定検証のテスト"""
        # 正常な設定
        warnings = self.config.validate_settings()
        # データディレクトリの親が存在しないため警告が出る可能性がある
        self.assertIsInstance(warnings, list)
        
        # 異常な設定値
        self.config.set("max_documents", 500)  # 1000未満
        warnings = self.config.validate_settings()
        self.assertTrue(any("最大ドキュメント数" in w for w in warnings))
        
        self.config.set("search_timeout", 0.5)  # 1秒未満
        warnings = self.config.validate_settings()
        self.assertTrue(any("検索タイムアウト" in w for w in warnings))
    
    def test_reset_to_defaults(self):
        """デフォルト値へのリセットテスト"""
        # 設定値を変更
        self.config.set("max_documents", 100000)
        self.config.set("log_level", "DEBUG")
        
        # リセット
        self.config.reset_to_defaults()
        
        # デフォルト値に戻ることを確認
        self.assertEqual(self.config.get("max_documents"), 50000)
        self.assertEqual(self.config.get("log_level"), "INFO")
    
    def test_export_import_settings(self):
        """設定のエクスポート・インポートテスト"""
        # 設定値を変更
        self.config.set("test_export", "export_value")
        self.config.set("max_documents", 75000)
        
        # エクスポート
        export_file = os.path.join(self.temp_dir, "export_config.json")
        self.assertTrue(self.config.export_settings(export_file))
        self.assertTrue(os.path.exists(export_file))
        
        # エクスポートファイルの内容確認
        with open(export_file, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        self.assertIn("version", export_data)
        self.assertIn("settings", export_data)
        self.assertEqual(export_data["settings"]["test_export"], "export_value")
        
        # 新しい設定オブジェクトでインポート
        new_config = Config()
        self.assertTrue(new_config.import_settings(export_file))
        self.assertEqual(new_config.get("test_export"), "export_value")
        self.assertEqual(new_config.get("max_documents"), 75000)
    
    def test_invalid_export_import(self):
        """無効なエクスポート・インポートのテスト"""
        # 存在しないディレクトリへのエクスポート
        invalid_export_file = "/nonexistent/path/config.json"
        self.assertFalse(self.config.export_settings(invalid_export_file))
        
        # 存在しないファイルからのインポート
        self.assertFalse(self.config.import_settings("/nonexistent/config.json"))
        
        # 無効なJSONファイルからのインポート
        invalid_json_file = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_json_file, 'w') as f:
            f.write("invalid json")
        
        self.assertFalse(self.config.import_settings(invalid_json_file))


if __name__ == '__main__':
    unittest.main()