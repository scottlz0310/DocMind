#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスク4「IndexingThreadManagerとの連携実装」の簡単な統合テスト

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
from src.core.thread_manager import IndexingThreadManager


def test_thread_manager_basic_functionality():
    """ThreadManagerの基本機能テスト"""
    
    print("=== ThreadManager基本機能テスト開始 ===")
    
    try:
        # ThreadManagerを直接テスト（テストモード）
        thread_manager = IndexingThreadManager(max_concurrent_threads=2, test_mode=True)
        
        print("1. ThreadManager初期化テスト")
        print(f"   - 最大同時実行数: {thread_manager.max_concurrent_threads}")
        print(f"   - 初期アクティブスレッド数: {thread_manager.get_active_thread_count()}")
        print(f"   - 新しいスレッドを開始可能: {thread_manager.can_start_new_thread()}")
        
        # 基本的な検証
        assert thread_manager.max_concurrent_threads == 2, "最大同時実行数が正しく設定されるべき"
        assert thread_manager.get_active_thread_count() == 0, "初期状態ではアクティブスレッドは0であるべき"
        assert thread_manager.can_start_new_thread(), "初期状態では新しいスレッドを開始できるべき"
        
        print("2. ステータス取得テスト")
        status = thread_manager.get_status_summary()
        print(f"   - ステータス概要: アクティブ={status['active_threads']}, 最大={status['max_concurrent']}")
        
        assert isinstance(status, dict), "ステータスは辞書形式で返されるべき"
        assert 'total_threads' in status, "total_threadsキーが含まれるべき"
        assert 'active_threads' in status, "active_threadsキーが含まれるべき"
        assert 'max_concurrent' in status, "max_concurrentキーが含まれるべき"
        
        print("3. スレッド開始テスト（テストモード）")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_folder = Path(temp_dir) / "test_docs"
            test_folder.mkdir()
            (test_folder / "test.txt").write_text("テスト内容")
            
            # モックのdocument_processorとindex_managerを作成
            mock_doc_processor = Mock()
            mock_index_manager = Mock()
            
            # スレッドを開始
            thread_id = thread_manager.start_indexing_thread(
                folder_path=str(test_folder),
                document_processor=mock_doc_processor,
                index_manager=mock_index_manager
            )
            
            print(f"   - 開始されたスレッドID: {thread_id}")
            
            # テストモードでは即座に完了するため、少し待機
            time.sleep(0.3)
            
            # 最終ステータスを確認
            final_status = thread_manager.get_status_summary()
            print(f"   - 最終ステータス: アクティブ={final_status['active_threads']}, 総数={final_status['total_threads']}")
            
            assert thread_id is not None, "スレッドIDが返されるべき"
        
        print("=== ThreadManager基本機能テスト完了 ===")
        
    except Exception as e:
        print(f"基本機能テスト中にエラー: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_rebuild_index_integration():
    """MainWindowの_rebuild_indexメソッドとThreadManagerの統合テスト"""
    
    # QApplicationが必要
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        print("=== _rebuild_index統合テスト開始 ===")
        
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
                from src.gui.main_window import MainWindow
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
                
                print("=== _rebuild_index統合テスト完了 ===")
                
                # クリーンアップ
                main_window.close()
                
    except Exception as e:
        print(f"統合テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        # QApplicationをクリーンアップ
        if app:
            app.quit()


def test_error_handling_scenarios():
    """エラーハンドリングシナリオのテスト"""
    
    print("=== エラーハンドリングテスト開始 ===")
    
    try:
        # ThreadManagerのエラーハンドリングをテスト
        thread_manager = IndexingThreadManager(max_concurrent_threads=1, test_mode=True)
        
        print("1. 無効なフォルダパスでのスレッド開始テスト")
        
        # 存在しないフォルダパスでスレッドを開始
        mock_doc_processor = Mock()
        mock_index_manager = Mock()
        
        thread_id = thread_manager.start_indexing_thread(
            folder_path="/nonexistent/folder",
            document_processor=mock_doc_processor,
            index_manager=mock_index_manager
        )
        
        print(f"   - 無効なパスでのスレッドID: {thread_id}")
        
        # テストモードでは例外が発生しないため、スレッドIDが返される
        assert thread_id is not None, "テストモードでは無効なパスでもスレッドIDが返される"
        
        print("2. ThreadManagerの状態確認")
        
        status = thread_manager.get_status_summary()
        print(f"   - 現在のステータス: {status}")
        
        # 基本的な状態確認
        assert isinstance(status['active_threads'], int), "アクティブスレッド数は整数であるべき"
        assert isinstance(status['total_threads'], int), "総スレッド数は整数であるべき"
        
        print("=== エラーハンドリングテスト完了 ===")
        
    except Exception as e:
        print(f"エラーハンドリングテスト中にエラー: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("タスク4統合テスト（簡単版）を実行中...")
    
    try:
        test_thread_manager_basic_functionality()
        print()
        test_error_handling_scenarios()
        print()
        test_rebuild_index_integration()
        print("\n✅ すべてのテストが成功しました！")
        
    except Exception as e:
        print(f"\n❌ テストが失敗しました: {e}")
        sys.exit(1)