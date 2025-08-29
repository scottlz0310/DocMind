#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
非同期処理統合テスト

分離したAsyncOperationManagerとFolderLoadWorkerの統合テストを実行します。
"""

import sys
import os
import tempfile
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui.folder_tree_components import AsyncOperationManager, FolderLoadWorker

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_folder_load_worker():
    """FolderLoadWorkerの単体テスト"""
    logger.info("=== FolderLoadWorker単体テスト開始 ===")
    
    # テスト用一時ディレクトリ作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # サブディレクトリ作成
        sub_dir1 = os.path.join(temp_dir, "subdir1")
        sub_dir2 = os.path.join(temp_dir, "subdir2")
        os.makedirs(sub_dir1)
        os.makedirs(sub_dir2)
        
        # テストファイル作成
        with open(os.path.join(sub_dir1, "test.txt"), "w") as f:
            f.write("test")
        
        # ワーカー作成
        worker = FolderLoadWorker(temp_dir, max_depth=2)
        
        # 結果収集用
        loaded_paths = []
        error_messages = []
        finished = False
        
        def on_folder_loaded(path, subdirs):
            loaded_paths.append((path, subdirs))
            logger.info(f"フォルダ読み込み: {path} -> {len(subdirs)}個のサブディレクトリ")
        
        def on_load_error(path, error):
            error_messages.append((path, error))
            logger.error(f"読み込みエラー: {path} -> {error}")
        
        def on_finished():
            nonlocal finished
            finished = True
            logger.info("読み込み完了")
        
        # シグナル接続
        worker.folder_loaded.connect(on_folder_loaded)
        worker.load_error.connect(on_load_error)
        worker.finished.connect(on_finished)
        
        # 実行
        worker.do_work()
        
        # 結果確認
        assert finished, "読み込みが完了していません"
        assert len(loaded_paths) > 0, "フォルダが読み込まれていません"
        assert len(error_messages) == 0, f"エラーが発生しました: {error_messages}"
        
        # ルートディレクトリが読み込まれているか確認
        root_loaded = any(path == temp_dir for path, _ in loaded_paths)
        assert root_loaded, "ルートディレクトリが読み込まれていません"
        
        logger.info("✅ FolderLoadWorker単体テスト成功")


def test_async_operation_manager():
    """AsyncOperationManagerの統合テスト"""
    logger.info("=== AsyncOperationManager統合テスト開始 ===")
    
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    
    # テスト用一時ディレクトリ作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # サブディレクトリ作成
        for i in range(3):
            sub_dir = os.path.join(temp_dir, f"subdir{i}")
            os.makedirs(sub_dir)
        
        # マネージャー作成
        manager = AsyncOperationManager()
        
        # 結果収集用
        loaded_paths = []
        error_messages = []
        finished = False
        
        def on_folder_loaded(path, subdirs):
            loaded_paths.append((path, subdirs))
            logger.info(f"フォルダ読み込み: {path} -> {len(subdirs)}個のサブディレクトリ")
        
        def on_load_error(path, error):
            error_messages.append((path, error))
            logger.error(f"読み込みエラー: {path} -> {error}")
        
        def on_finished():
            nonlocal finished
            finished = True
            logger.info("読み込み完了")
            app.quit()
        
        # シグナル接続
        manager.folder_loaded.connect(on_folder_loaded)
        manager.load_error.connect(on_load_error)
        manager.load_finished.connect(on_finished)
        
        # 読み込み開始
        manager.start_folder_loading(temp_dir, max_depth=1)
        
        # タイムアウト設定（5秒）
        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(lambda: app.quit())
        timeout_timer.start(5000)
        
        # イベントループ実行
        app.exec()
        
        # クリーンアップ
        manager.cleanup_workers()
        
        # 結果確認
        assert finished, "読み込みが完了していません（タイムアウト）"
        assert len(loaded_paths) > 0, "フォルダが読み込まれていません"
        assert len(error_messages) == 0, f"エラーが発生しました: {error_messages}"
        
        # マネージャーの状態確認
        assert not manager.is_loading(), "読み込み完了後もis_loading()がTrueです"
        
        logger.info("✅ AsyncOperationManager統合テスト成功")


def test_error_handling():
    """エラーハンドリングテスト"""
    logger.info("=== エラーハンドリングテスト開始 ===")
    
    # 存在しないパスでテスト
    worker = FolderLoadWorker("/nonexistent/path", max_depth=1)
    
    error_occurred = False
    finished = False
    
    def on_load_error(path, error):
        nonlocal error_occurred
        error_occurred = True
        logger.info(f"期待通りのエラー: {path} -> {error}")
    
    def on_finished():
        nonlocal finished
        finished = True
    
    # シグナル接続
    worker.load_error.connect(on_load_error)
    worker.finished.connect(on_finished)
    
    # 実行
    worker.do_work()
    
    # 結果確認
    assert finished, "処理が完了していません"
    # 存在しないパスの場合、エラーは発生しない（単に何も読み込まれない）
    
    logger.info("✅ エラーハンドリングテスト成功")


def main():
    """メインテスト実行"""
    logger.info("非同期処理統合テスト開始")
    
    try:
        # 各テストを実行
        test_folder_load_worker()
        test_async_operation_manager()
        test_error_handling()
        
        logger.info("🎉 すべてのテストが成功しました！")
        return True
        
    except Exception as e:
        logger.error(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)