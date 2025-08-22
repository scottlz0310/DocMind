#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind フォルダツリーウィジェットのユニットテスト

フォルダツリーナビゲーション機能のテストを実装します。
"""

import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# テスト用のQt環境設定
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication, QTreeWidgetItem, QTreeWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.gui.folder_tree import (
    FolderTreeWidget, FolderTreeContainer, FolderTreeItem, 
    FolderItemType, FolderLoadWorker
)


class TestFolderTreeItem(unittest.TestCase):
    """FolderTreeItemクラスのテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラス全体の初期化"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """各テストの初期化"""
        self.item = FolderTreeItem()
    
    def test_set_folder_data(self):
        """フォルダデータ設定のテスト"""
        test_path = "/test/folder"
        self.item.set_folder_data(test_path, FolderItemType.FOLDER)
        
        self.assertEqual(self.item.folder_path, test_path)
        self.assertEqual(self.item.item_type, FolderItemType.FOLDER)
        self.assertEqual(self.item.text(0), "folder")
        self.assertEqual(self.item.toolTip(0), test_path)
    
    def test_set_folder_data_root(self):
        """ルートフォルダデータ設定のテスト"""
        test_path = "C:\\"
        self.item.set_folder_data(test_path, FolderItemType.ROOT)
        
        self.assertEqual(self.item.folder_path, test_path)
        self.assertEqual(self.item.item_type, FolderItemType.ROOT)
        self.assertEqual(self.item.text(0), test_path)  # ドライブルートの場合はパス全体
    
    def test_update_statistics(self):
        """統計情報更新のテスト"""
        test_path = "/test/folder"
        self.item.set_folder_data(test_path)
        
        self.item.update_statistics(10, 5)
        
        self.assertEqual(self.item.file_count, 10)
        self.assertEqual(self.item.indexed_count, 5)
        self.assertEqual(self.item.text(0), "folder (5/10)")
    
    def test_update_statistics_no_files(self):
        """ファイルなしの統計情報更新のテスト"""
        test_path = "/test/folder"
        self.item.set_folder_data(test_path)
        
        self.item.update_statistics(0, 0)
        
        self.assertEqual(self.item.file_count, 0)
        self.assertEqual(self.item.indexed_count, 0)
        self.assertEqual(self.item.text(0), "folder")


class TestFolderLoadWorker(unittest.TestCase):
    """FolderLoadWorkerクラスのテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラス全体の初期化"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """各テストの初期化"""
        # テスト用の一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用のディレクトリ構造を作成
        os.makedirs(os.path.join(self.temp_dir, "folder1"))
        os.makedirs(os.path.join(self.temp_dir, "folder2"))
        os.makedirs(os.path.join(self.temp_dir, "folder1", "subfolder1"))
        
        # テスト用ファイルを作成
        with open(os.path.join(self.temp_dir, "file1.txt"), "w") as f:
            f.write("test content")
    
    def tearDown(self):
        """各テストの後処理"""
        # 一時ディレクトリを削除
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_folder_loading(self):
        """フォルダ読み込みのテスト"""
        worker = FolderLoadWorker(self.temp_dir, max_depth=1)
        
        # シグナルをキャプチャするためのモック
        folder_loaded_mock = Mock()
        load_finished_mock = Mock()
        
        worker.folder_loaded.connect(folder_loaded_mock)
        worker.load_finished.connect(load_finished_mock)
        
        # ワーカーを実行
        worker.run()
        
        # シグナルが発行されたことを確認
        self.assertTrue(folder_loaded_mock.called)
        self.assertTrue(load_finished_mock.called)
        
        # 読み込まれたフォルダを確認
        call_args = folder_loaded_mock.call_args_list[0][0]
        loaded_path = call_args[0]
        subdirs = call_args[1]
        
        self.assertEqual(loaded_path, self.temp_dir)
        self.assertIn(os.path.join(self.temp_dir, "folder1"), subdirs)
        self.assertIn(os.path.join(self.temp_dir, "folder2"), subdirs)
    
    def test_worker_stop(self):
        """ワーカー停止のテスト"""
        worker = FolderLoadWorker(self.temp_dir)
        
        # 停止フラグを設定
        worker.stop()
        
        self.assertTrue(worker.should_stop)


class TestFolderTreeWidget(unittest.TestCase):
    """FolderTreeWidgetクラスのテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラス全体の初期化"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """各テストの初期化"""
        self.widget = FolderTreeWidget()
        
        # テスト用の一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用のディレクトリ構造を作成
        self.test_folder1 = os.path.join(self.temp_dir, "test_folder1")
        self.test_folder2 = os.path.join(self.temp_dir, "test_folder2")
        os.makedirs(self.test_folder1)
        os.makedirs(self.test_folder2)
        os.makedirs(os.path.join(self.test_folder1, "subfolder"))
    
    def tearDown(self):
        """各テストの後処理"""
        # ワーカーを停止
        if self.widget.load_worker and self.widget.load_worker.isRunning():
            self.widget.load_worker.stop()
            self.widget.load_worker.wait()
        
        # ウィジェットを削除
        self.widget.deleteLater()
        
        # 一時ディレクトリを削除
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_widget_initialization(self):
        """ウィジェット初期化のテスト"""
        self.assertIsNotNone(self.widget)
        # ヘッダーラベルの確認（PySide6では直接取得できないため、設定されていることを確認）
        self.assertFalse(self.widget.isHeaderHidden())
        self.assertTrue(self.widget.alternatingRowColors())
        self.assertEqual(self.widget.selectionMode(), QTreeWidget.SingleSelection)
    
    def test_load_folder_structure(self):
        """フォルダ構造読み込みのテスト"""
        # シグナルをキャプチャするためのモック
        folder_selected_mock = Mock()
        self.widget.folder_selected.connect(folder_selected_mock)
        
        # 非同期処理を無効化してテスト
        with patch.object(self.widget, '_load_subfolders_async'):
            # フォルダ構造を読み込み
            self.widget.load_folder_structure(self.temp_dir)
            
            # ルートアイテムが作成されたことを確認
            self.assertEqual(self.widget.topLevelItemCount(), 1)
            
            root_item = self.widget.topLevelItem(0)
            self.assertIsInstance(root_item, FolderTreeItem)
            self.assertEqual(root_item.folder_path, self.temp_dir)
            self.assertEqual(root_item.item_type, FolderItemType.ROOT)
            
            # 内部マップに追加されたことを確認
            self.assertIn(self.temp_dir, self.widget.item_map)
            self.assertIn(self.temp_dir, self.widget.root_paths)
    
    def test_load_invalid_folder(self):
        """無効なフォルダ読み込みのテスト"""
        invalid_path = "/nonexistent/folder"
        
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            self.widget.load_folder_structure(invalid_path)
            
            # 警告ダイアログが表示されたことを確認
            mock_warning.assert_called_once()
    
    def test_folder_selection(self):
        """フォルダ選択のテスト"""
        # フォルダ構造を読み込み
        self.widget.load_folder_structure(self.temp_dir)
        
        # シグナルをキャプチャするためのモック
        folder_selected_mock = Mock()
        self.widget.folder_selected.connect(folder_selected_mock)
        
        # ルートアイテムを選択
        root_item = self.widget.topLevelItem(0)
        self.widget.setCurrentItem(root_item)
        
        # 選択変更イベントを発生させる
        self.widget._on_selection_changed()
        
        # シグナルが発行されたことを確認
        folder_selected_mock.assert_called_once_with(self.temp_dir)
    
    def test_get_selected_folder(self):
        """選択フォルダ取得のテスト"""
        # フォルダ構造を読み込み
        self.widget.load_folder_structure(self.temp_dir)
        
        # 初期状態では何も選択されていない
        self.assertIsNone(self.widget.get_selected_folder())
        
        # ルートアイテムを選択
        root_item = self.widget.topLevelItem(0)
        self.widget.setCurrentItem(root_item)
        
        # 選択されたフォルダパスを確認
        self.assertEqual(self.widget.get_selected_folder(), self.temp_dir)
    
    def test_indexed_folders_management(self):
        """インデックス済みフォルダ管理のテスト"""
        # 初期状態では空
        self.assertEqual(self.widget.get_indexed_folders(), [])
        
        # インデックス済みフォルダを設定
        test_paths = [self.test_folder1, self.test_folder2]
        self.widget.set_indexed_folders(test_paths)
        
        # 設定されたことを確認
        indexed_folders = self.widget.get_indexed_folders()
        self.assertEqual(set(indexed_folders), set(test_paths))
    
    def test_excluded_folders_management(self):
        """除外フォルダ管理のテスト"""
        # 初期状態では空
        self.assertEqual(self.widget.get_excluded_folders(), [])
        
        # 除外フォルダを設定
        test_paths = [self.test_folder1]
        self.widget.set_excluded_folders(test_paths)
        
        # 設定されたことを確認
        excluded_folders = self.widget.get_excluded_folders()
        self.assertEqual(excluded_folders, test_paths)
    
    def test_folder_filtering(self):
        """フォルダフィルタリングのテスト"""
        # フォルダ構造を読み込み
        self.widget.load_folder_structure(self.temp_dir)
        
        # フィルターを適用
        self.widget.filter_folders("test_folder1")
        
        # フィルター結果を確認（実際の表示状態は非同期なので、メソッドが呼ばれることを確認）
        # より詳細なテストは統合テストで行う
        
        # フィルターをクリア
        self.widget.filter_folders("")
    
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_expand_to_path(self, mock_isdir, mock_exists):
        """パス展開のテスト"""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        
        # フォルダ構造を読み込み
        self.widget.load_folder_structure(self.temp_dir)
        
        # 存在しないパスの場合は何も起こらない
        self.widget.expand_to_path("/nonexistent/path")
        
        # 存在するパスの場合
        self.widget.expand_to_path(self.temp_dir)


class TestFolderTreeContainer(unittest.TestCase):
    """FolderTreeContainerクラスのテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラス全体の初期化"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """各テストの初期化"""
        self.container = FolderTreeContainer()
        
        # テスト用の一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.temp_dir, "test_folder"))
    
    def tearDown(self):
        """各テストの後処理"""
        # コンテナを削除
        self.container.deleteLater()
        
        # 一時ディレクトリを削除
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_container_initialization(self):
        """コンテナ初期化のテスト"""
        self.assertIsNotNone(self.container)
        self.assertIsNotNone(self.container.tree_widget)
        self.assertIsNotNone(self.container.filter_input)
        self.assertIsNotNone(self.container.add_button)
        self.assertIsNotNone(self.container.stats_label)
    
    def test_filter_functionality(self):
        """フィルター機能のテスト"""
        # フィルター入力をテスト
        self.container.filter_input.setText("test")
        
        # フィルタークリアをテスト
        self.container._clear_filter()
        self.assertEqual(self.container.filter_input.text(), "")
    
    def test_stats_update(self):
        """統計情報更新のテスト"""
        # 初期状態
        self.assertEqual(self.container.stats_label.text(), "フォルダ: 0, インデックス: 0")
        
        # フォルダを追加してから統計を更新
        self.container.load_folder_structure(self.temp_dir)
        self.container._update_stats()
        
        # 統計が更新されたことを確認
        stats_text = self.container.stats_label.text()
        self.assertIn("フォルダ:", stats_text)
        self.assertIn("インデックス:", stats_text)
    
    def test_signal_forwarding(self):
        """シグナル転送のテスト"""
        # シグナルをキャプチャするためのモック
        folder_selected_mock = Mock()
        folder_indexed_mock = Mock()
        folder_excluded_mock = Mock()
        refresh_requested_mock = Mock()
        
        self.container.folder_selected.connect(folder_selected_mock)
        self.container.folder_indexed.connect(folder_indexed_mock)
        self.container.folder_excluded.connect(folder_excluded_mock)
        self.container.refresh_requested.connect(refresh_requested_mock)
        
        # 内部ツリーウィジェットからシグナルを発行
        test_path = "/test/path"
        self.container.tree_widget.folder_selected.emit(test_path)
        self.container.tree_widget.folder_indexed.emit(test_path)
        self.container.tree_widget.folder_excluded.emit(test_path)
        self.container.tree_widget.refresh_requested.emit()
        
        # シグナルが転送されたことを確認
        folder_selected_mock.assert_called_once_with(test_path)
        folder_indexed_mock.assert_called_once_with(test_path)
        folder_excluded_mock.assert_called_once_with(test_path)
        refresh_requested_mock.assert_called_once()
    
    def test_public_methods(self):
        """パブリックメソッドのテスト"""
        # フォルダ構造読み込み
        self.container.load_folder_structure(self.temp_dir)
        
        # 各メソッドが正常に動作することを確認
        selected_folder = self.container.get_selected_folder()
        indexed_folders = self.container.get_indexed_folders()
        excluded_folders = self.container.get_excluded_folders()
        
        # 型チェック
        self.assertIsInstance(indexed_folders, list)
        self.assertIsInstance(excluded_folders, list)
        
        # 設定メソッドのテスト
        test_paths = [self.temp_dir]
        self.container.set_indexed_folders(test_paths)
        self.container.set_excluded_folders(test_paths)
        
        # パス展開のテスト
        self.container.expand_to_path(self.temp_dir)


class TestFolderTreeIntegration(unittest.TestCase):
    """フォルダツリーの統合テスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラス全体の初期化"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """各テストの初期化"""
        self.container = FolderTreeContainer()
        
        # より複雑なテスト用ディレクトリ構造を作成
        self.temp_dir = tempfile.mkdtemp()
        
        # 複数レベルのディレクトリ構造
        self.folders = {
            'root': self.temp_dir,
            'docs': os.path.join(self.temp_dir, "documents"),
            'images': os.path.join(self.temp_dir, "images"),
            'docs_sub1': os.path.join(self.temp_dir, "documents", "reports"),
            'docs_sub2': os.path.join(self.temp_dir, "documents", "presentations"),
            'images_sub1': os.path.join(self.temp_dir, "images", "photos"),
        }
        
        for folder in self.folders.values():
            os.makedirs(folder, exist_ok=True)
        
        # テスト用ファイルを作成
        for i in range(5):
            with open(os.path.join(self.folders['docs'], f"doc{i}.txt"), "w") as f:
                f.write(f"Document {i} content")
    
    def tearDown(self):
        """各テストの後処理"""
        self.container.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_workflow(self):
        """完全なワークフローのテスト"""
        # 1. フォルダ構造を読み込み
        self.container.load_folder_structure(self.temp_dir)
        
        # 2. フォルダをインデックスに追加
        self.container.set_indexed_folders([self.folders['docs']])
        
        # 3. フォルダを除外
        self.container.set_excluded_folders([self.folders['images']])
        
        # 4. 統計情報を確認
        indexed_folders = self.container.get_indexed_folders()
        excluded_folders = self.container.get_excluded_folders()
        
        self.assertIn(self.folders['docs'], indexed_folders)
        self.assertIn(self.folders['images'], excluded_folders)
        
        # 5. フィルタリングをテスト
        self.container.filter_input.setText("documents")
        self.container._on_filter_changed("documents")
        
        # 6. フィルターをクリア
        self.container._clear_filter()
        
        # 7. 統計情報が正しく更新されることを確認
        stats_text = self.container.stats_label.text()
        self.assertIn("インデックス: 1", stats_text)
        self.assertIn("除外: 1", stats_text)
    
    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        # 存在しないフォルダを読み込み
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            self.container.load_folder_structure("/nonexistent/folder")
            mock_warning.assert_called_once()
        
        # 権限のないフォルダのシミュレーション
        with patch('os.listdir', side_effect=PermissionError("Access denied")):
            # エラーが適切に処理されることを確認
            worker = FolderLoadWorker(self.temp_dir)
            
            error_mock = Mock()
            worker.load_error.connect(error_mock)
            
            worker.run()
            
            # エラーシグナルが発行されたことを確認
            self.assertTrue(error_mock.called)


if __name__ == '__main__':
    # テストスイートを実行
    unittest.main(verbosity=2)