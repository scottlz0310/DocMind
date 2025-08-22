# -*- coding: utf-8 -*-
"""
設定ダイアログのユニットテスト

SettingsDialog クラスのテストを実装します。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# PySide6のテスト環境設定
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

from src.utils.config import Config
from src.gui.settings_dialog import SettingsDialog


class TestSettingsDialog(unittest.TestCase):
    """設定ダイアログのテストクラス"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラス全体の準備"""
        # QApplicationが存在しない場合は作成
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """テスト前の準備"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        
        # テスト用設定オブジェクトを作成
        self.config = Config(config_file=self.config_file)
        
        # 設定ダイアログを作成
        self.dialog = SettingsDialog(self.config)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # ダイアログを閉じる
        if self.dialog:
            self.dialog.close()
        
        # 一時ファイルを削除
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_dialog_initialization(self):
        """ダイアログの初期化テスト"""
        self.assertIsNotNone(self.dialog)
        self.assertEqual(self.dialog.windowTitle(), "DocMind 設定")
        self.assertTrue(self.dialog.isModal())
        
        # タブウィジェットの存在確認
        self.assertIsNotNone(self.dialog.tab_widget)
        self.assertGreater(self.dialog.tab_widget.count(), 0)
    
    def test_tab_creation(self):
        """タブの作成テスト"""
        tab_widget = self.dialog.tab_widget
        
        # 期待されるタブ名
        expected_tabs = ["一般", "検索", "フォルダ", "ストレージ", "ログ", "UI"]
        
        # タブ数の確認
        self.assertEqual(tab_widget.count(), len(expected_tabs))
        
        # 各タブの存在確認
        for i, expected_tab in enumerate(expected_tabs):
            self.assertEqual(tab_widget.tabText(i), expected_tab)
    
    def test_load_current_settings(self):
        """現在の設定値の読み込みテスト"""
        # 設定値を変更
        self.config.set("max_documents", 75000)
        self.config.set("search_timeout", 10.0)
        self.config.set("log_level", "DEBUG")
        
        # 新しいダイアログを作成（設定値が読み込まれる）
        dialog = SettingsDialog(self.config)
        
        # UI要素に設定値が反映されていることを確認
        self.assertEqual(dialog.max_documents_spin.value(), 75000)
        self.assertEqual(dialog.search_timeout_spin.value(), 10.0)
        self.assertEqual(dialog.log_level_combo.currentText(), "DEBUG")
        
        dialog.close()
    
    def test_collect_settings(self):
        """設定値の収集テスト"""
        # UI要素の値を変更
        self.dialog.max_documents_spin.setValue(80000)
        self.dialog.search_timeout_spin.setValue(8.0)
        self.dialog.batch_size_spin.setValue(200)
        self.dialog.enable_file_watching_check.setChecked(False)
        
        # 設定値を収集
        settings = self.dialog._collect_settings()
        
        # 収集された設定値の確認
        self.assertEqual(settings["max_documents"], 80000)
        self.assertEqual(settings["search_timeout"], 8.0)
        self.assertEqual(settings["batch_size"], 200)
        self.assertFalse(settings["enable_file_watching"])
    
    def test_folder_management(self):
        """フォルダ管理機能のテスト"""
        # フォルダリストが空であることを確認
        self.assertEqual(self.dialog.folders_list.count(), 0)
        
        # フォルダを手動で追加（ダイアログをモック）
        with patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = "/test/folder"
            
            # フォルダ追加ボタンをクリック
            self.dialog._add_folder()
            
            # フォルダが追加されたことを確認
            self.assertEqual(self.dialog.folders_list.count(), 1)
            self.assertEqual(self.dialog.folders_list.item(0).text(), "/test/folder")
        
        # 同じフォルダを再度追加（重複チェック）
        with patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = "/test/folder"
            with patch('PySide6.QtWidgets.QMessageBox.information') as mock_msg:
                self.dialog._add_folder()
                mock_msg.assert_called_once()
                # フォルダ数は変わらない
                self.assertEqual(self.dialog.folders_list.count(), 1)
        
        # フォルダを選択して削除
        self.dialog.folders_list.setCurrentRow(0)
        with patch('PySide6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.Yes
            
            self.dialog._remove_folder()
            
            # フォルダが削除されたことを確認
            self.assertEqual(self.dialog.folders_list.count(), 0)
    
    def test_exclude_patterns(self):
        """除外パターンのテスト"""
        # 除外パターンを設定
        patterns = "*.tmp\n*.log\n__pycache__/*"
        self.dialog.exclude_patterns_text.setPlainText(patterns)
        
        # 設定値を収集
        settings = self.dialog._collect_settings()
        
        # 除外パターンが正しく収集されることを確認
        expected_patterns = ["*.tmp", "*.log", "__pycache__/*"]
        self.assertEqual(settings["exclude_patterns"], expected_patterns)
    
    def test_data_directory_browse(self):
        """データディレクトリ参照のテスト"""
        with patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = "/new/data/directory"
            
            self.dialog._browse_data_directory()
            
            # データディレクトリが更新されたことを確認
            self.assertEqual(self.dialog.data_directory_edit.text(), "/new/data/directory")
    
    def test_log_file_browse(self):
        """ログファイル参照のテスト"""
        with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ("/new/log/file.log", "")
            
            self.dialog._browse_log_file()
            
            # ログファイルパスが更新されたことを確認
            self.assertEqual(self.dialog.log_file_edit.text(), "/new/log/file.log")
    
    def test_settings_validation(self):
        """設定値の検証テスト"""
        # 正常な設定値
        settings = {
            "data_directory": self.temp_dir,
            "indexed_folders": [],
            "max_documents": 50000,
            "search_timeout": 5.0
        }
        
        self.assertTrue(self.dialog._validate_settings(settings))
        
        # 異常な設定値（最大ドキュメント数が少なすぎる）
        settings["max_documents"] = 500
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            result = self.dialog._validate_settings(settings)
            self.assertFalse(result)
            mock_warning.assert_called_once()
        
        # 異常な設定値（検索タイムアウトが短すぎる）
        settings["max_documents"] = 50000
        settings["search_timeout"] = 0.5
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            result = self.dialog._validate_settings(settings)
            self.assertFalse(result)
            mock_warning.assert_called_once()
    
    def test_apply_settings(self):
        """設定適用のテスト"""
        # UI要素の値を変更
        self.dialog.max_documents_spin.setValue(60000)
        self.dialog.log_level_combo.setCurrentText("WARNING")
        
        # シグナルのモック
        signal_emitted = False
        emitted_settings = None
        
        def on_settings_changed(settings):
            nonlocal signal_emitted, emitted_settings
            signal_emitted = True
            emitted_settings = settings
        
        self.dialog.settings_changed.connect(on_settings_changed)
        
        # 設定を適用
        with patch('PySide6.QtWidgets.QMessageBox.information'):
            self.dialog._apply_settings()
        
        # シグナルが発行されたことを確認
        self.assertTrue(signal_emitted)
        self.assertIsNotNone(emitted_settings)
        self.assertEqual(emitted_settings["max_documents"], 60000)
        self.assertEqual(emitted_settings["log_level"], "WARNING")
    
    def test_save_and_close(self):
        """設定保存と閉じるのテスト"""
        # UI要素の値を変更
        self.dialog.max_documents_spin.setValue(70000)
        
        # 設定保存のモック
        with patch.object(self.config, 'save_config', return_value=True):
            with patch.object(self.dialog, 'accept') as mock_accept:
                self.dialog._save_and_close()
                
                # 設定がConfigオブジェクトに適用されたことを確認
                self.assertEqual(self.config.get("max_documents"), 70000)
                
                # ダイアログが閉じられたことを確認
                mock_accept.assert_called_once()
    
    def test_semantic_weight_slider(self):
        """セマンティック検索重みスライダーのテスト"""
        # スライダーの値を変更
        self.dialog.semantic_weight_slider.setValue(75)
        
        # ラベルが更新されることを確認
        self.assertEqual(self.dialog.semantic_weight_label.text(), "75%")
        
        # 設定値の収集で正しい値が取得されることを確認
        settings = self.dialog._collect_settings()
        self.assertEqual(settings["semantic_weight"], 75)
    
    def test_window_size_settings(self):
        """ウィンドウサイズ設定のテスト"""
        # ウィンドウサイズを変更
        self.dialog.window_width_spin.setValue(1600)
        self.dialog.window_height_spin.setValue(900)
        
        # 設定値の収集
        settings = self.dialog._collect_settings()
        
        # 正しい値が収集されることを確認
        self.assertEqual(settings["window_width"], 1600)
        self.assertEqual(settings["window_height"], 900)
    
    def test_ui_theme_settings(self):
        """UIテーマ設定のテスト"""
        # テーマを変更
        self.dialog.ui_theme_combo.setCurrentText("dark")
        
        # 設定値の収集
        settings = self.dialog._collect_settings()
        
        # 正しいテーマが収集されることを確認
        self.assertEqual(settings["ui_theme"], "dark")
    
    def test_font_settings(self):
        """フォント設定のテスト"""
        # フォント設定を変更
        self.dialog.font_family_combo.setCurrentText("Arial")
        self.dialog.font_size_spin.setValue(12)
        
        # 設定値の収集
        settings = self.dialog._collect_settings()
        
        # 正しいフォント設定が収集されることを確認
        self.assertEqual(settings["font_family"], "Arial")
        self.assertEqual(settings["font_size"], 12)


if __name__ == '__main__':
    unittest.main()