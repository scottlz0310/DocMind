#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスク4「IndexingThreadManagerとの連携実装」の統合テスト

このテストは、MainWindowの_rebuild_indexメソッドが
IndexingThreadManagerと正しく連携することを確認します。
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from src.gui.main_window import MainWindow
from src.core.thread_manager import IndexingThreadManager
from src.core.rebuild_timeout_manager import RebuildTimeoutManager


def test_rebuild_index_thread_manager_integration():
    """IndexingThreadManagerとの連携テスト"""
    
    # QApplicationが必要
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        # テスト用の一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            test_folder = Path(temp_dir) / "test_documents"
            test_folder.mkdir()
            
            # テスト用ファイルを作成
            (test_folder / "test1.txt").write_text("テストドキュメント1の内容")
            (test_folder / "test2.txt").write_text("テストドキュメント2の内容")
            
            # MainWindowを作成（テストモード）
            with patch('src.gui.main_window.QMessageBox.question') as mock_question, \
                 patch('src.gui.main_window.QMessageBox.critical') as mock_critical, \
                 patch('src.gui.main_window.QMessageBox.warning') as mock_warning:
                
                # ユーザーが「はい」を選択するようにモック
                mock_question.return_value = QMessageBox.Yes
                
                # MainWindowを初期化
                main_window = MainWindow()
                
                # テストモードでIndexingThreadManagerを再初期化
                main_window.thread_manager = IndexingThreadManager(
                    max_concurrent_threads=1, 
                    test_mode=True
                )
                main_window._connect_thread_manager_signals()
                
                # フォルダ選択をモック
                main_window.folder_tree_container.get_selected_folder = Mock(
                    return_value=str(test_folder)
                )
                
                print("=== テスト開始: IndexingThreadManagerとの連携 ===")
                
                # 1. 正常なケース: インデックス再構築の実行
                print("1. 正常なインデックス再構築をテスト")
                
                # 進捗とステータスの変化を追跡
                progress_calls = []
                status_calls = []
                
                original_show_progress = main_window.show_progress
                original_show_status = main_window.show_status_message
                
                def track_progress(*args, **kwargs):
                    progress_calls.append(args)
                    return original_show_progress(*args, **kwargs)
                
                def track_status(*args, **kwargs):
                    status_calls.append(args)
                    return original_show_status(*args, **kwargs)
                
                main_window.show_progress = track_progress
                main_window.show_status_message = track_status
                
                # インデックス再構築を実行
                main_window._rebuild_index()
                
                # 少し待機してスレッド処理を完了させる
                QApplication.processEvents()
                time.sleep(0.5)
                QApplication.processEvents()
                
                # 結果を検証
                print(f"   - 確認ダイアログが表示された: {mock_question.called}")
                print(f"   - 進捗表示が呼ばれた回数: {len(progress_calls)}")
                print(f"   - ステータス更新が呼ばれた回数: {len(status_calls)}")
                
                # 基本的な検証
                assert mock_question.called, "確認ダイアログが表示されるべき"
                assert len(progress_calls) > 0, "進捗表示が呼ばれるべき"
                
                # 2. エラーケース: フォルダが選択されていない場合
                print("2. フォルダ未選択エラーをテスト")
                
                mock_question.reset_mock()
                mock_warning.reset_mock()
                
                # フォルダが選択されていない状態をモック
                main_window.folder_tree_container.get_selected_folder.return_value = None
                
                main_window._rebuild_index()
                
                print(f"   - 確認ダイアログが表示された: {mock_question.called}")
                print(f"   - 警告ダイアログが表示された: {mock_warning.called}")
                
                assert mock_question.called, "確認ダイアログが表示されるべき"
                assert mock_warning.called, "警告ダイアログが表示されるべき"
                
                # 3. エラーケース: ユーザーがキャンセルした場合
                print("3. ユーザーキャンセルをテスト")
                
                mock_question.reset_mock()
                mock_question.return_value = QMessageBox.No
                
                # フォルダを再設定
                main_window.folder_tree_container.get_selected_folder.return_value = str(test_folder)
                
                main_window._rebuild_index()
                
                print(f"   - 確認ダイアログが表示された: {mock_question.called}")
                print(f"   - エラーダイアログが表示されなかった: {not mock_critical.called}")
                
                assert mock_question.called, "確認ダイアログが表示されるべき"
                assert not mock_critical.called, "エラーダイアログは表示されないべき"
                
                print("=== すべてのテストが成功しました ===")
                
                # クリーンアップ
                main_window.close()
                
    except Exception as e:
        print(f"テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        # QApplicationをクリーンアップ
        if app:
            app.quit()


def test_thread_manager_error_handling():
    """ThreadManagerのエラーハンドリングテスト"""
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        print("=== エラーハンドリングテスト開始 ===")
        
        # ThreadManagerを直接テスト
        thread_manager = IndexingThreadManager(max_concurrent_threads=1, test_mode=True)
        
        # テストにタイムアウトを設定
        start_time = time.time()
        timeout = 10  # 10秒でタイムアウト
        
        # 1. 正常なスレッド開始
        print("1. 正常なスレッド開始をテスト")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_folder = Path(temp_dir) / "test_docs"
            test_folder.mkdir()
            (test_folder / "test.txt").write_text("テスト内容")
            
            # モックのdocument_processorとindex_managerを作成
            mock_doc_processor = Mock()
            mock_index_manager = Mock()
            
            thread_id = thread_manager.start_indexing_thread(
                folder_path=str(test_folder),
                document_processor=mock_doc_processor,
                index_manager=mock_index_manager
            )
            
            print(f"   - スレッドID: {thread_id}")
            print(f"   - アクティブスレッド数: {thread_manager.get_active_thread_count()}")
            
            assert thread_id is not None, "スレッドIDが返されるべき"
            
            # 少し待機（タイムアウトチェック付き）
            elapsed = 0
            while elapsed < timeout:
                time.sleep(0.1)
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    print(f"   - 警告: テストがタイムアウトしました ({timeout}秒)")
                    break
            
            # 2. 同時実行数制限のテスト
            print("2. 同時実行数制限をテスト")
            
            # テストモードでは即座に完了するため、制限テストのために
            # 通常モードのThreadManagerを使用
            normal_thread_manager = IndexingThreadManager(max_concurrent_threads=1, test_mode=False)
            
            # モックワーカーを使用して実際のスレッドを開始しないようにする
            with patch('src.core.thread_manager.IndexingWorker') as mock_worker_class, \
                 patch('src.core.thread_manager.QThread') as mock_qthread_class:
                
                # モックワーカーとスレッドを設定
                mock_worker = Mock()
                mock_thread = Mock()
                mock_thread.isRunning.return_value = True
                mock_worker_class.return_value = mock_worker
                mock_qthread_class.return_value = mock_thread
                
                # 1つ目のスレッドを開始
                thread_id_1 = normal_thread_manager.start_indexing_thread(
                    folder_path=str(test_folder),
                    document_processor=mock_doc_processor,
                    index_manager=mock_index_manager
                )
                
                print(f"   - 1つ目のスレッドID: {thread_id_1}")
                print(f"   - アクティブスレッド数: {normal_thread_manager.get_active_thread_count()}")
                
                # 2つ目のスレッドを開始（制限に引っかかるはず）
                thread_id_2 = normal_thread_manager.start_indexing_thread(
                    folder_path=str(test_folder) + "_2",
                    document_processor=mock_doc_processor,
                    index_manager=mock_index_manager
                )
                
                print(f"   - 2つ目のスレッドID: {thread_id_2}")
                print(f"   - 制限により開始できない: {thread_id_2 is None}")
                
                # ステータスを表示
                status = normal_thread_manager.get_status_summary()
                print(f"   - 最終ステータス: アクティブ={status['active_threads']}, 最大={status['max_concurrent']}")
                
                # 検証
                assert thread_id_1 is not None, "1つ目のスレッドは開始されるべき"
                assert thread_id_2 is None, "2つ目のスレッドは制限により開始されないべき"
            
        print("=== エラーハンドリングテスト完了 ===")
        
    except Exception as e:
        print(f"エラーハンドリングテスト中にエラー: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        if app:
            app.quit()


if __name__ == "__main__":
    print("タスク4統合テストを実行中...")
    
    try:
        test_rebuild_index_thread_manager_integration()
        test_thread_manager_error_handling()
        print("\n✅ すべてのテストが成功しました！")
        
    except Exception as e:
        print(f"\n❌ テストが失敗しました: {e}")
        sys.exit(1)