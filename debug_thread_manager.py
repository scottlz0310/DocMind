#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThreadManagerのデバッグ用スクリプト
"""

import os
import sys
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.thread_manager import IndexingThreadManager


def debug_thread_manager():
    """ThreadManagerの動作をデバッグ"""
    
    print("=== ThreadManagerデバッグ開始 ===")
    
    try:
        print("1. ThreadManager初期化")
        thread_manager = IndexingThreadManager(max_concurrent_threads=2, test_mode=True)
        print("   - 初期化完了")
        
        print("2. 基本プロパティ確認")
        print(f"   - max_concurrent_threads: {thread_manager.max_concurrent_threads}")
        print(f"   - test_mode: {thread_manager.test_mode}")
        print(f"   - active_threads辞書: {len(thread_manager.active_threads)}")
        
        print("3. get_active_thread_count()テスト")
        try:
            count = thread_manager.get_active_thread_count()
            print(f"   - アクティブスレッド数: {count}")
        except Exception as e:
            print(f"   - エラー: {e}")
            import traceback
            traceback.print_exc()
        
        print("4. can_start_new_thread()テスト")
        try:
            can_start = thread_manager.can_start_new_thread()
            print(f"   - 新しいスレッドを開始可能: {can_start}")
        except Exception as e:
            print(f"   - エラー: {e}")
            import traceback
            traceback.print_exc()
        
        print("5. get_status_summary()テスト")
        try:
            # ステップバイステップでテスト
            print("   - ロック取得前")
            
            with thread_manager.lock:
                print("   - ロック取得後")
                
                state_counts = {}
                print(f"   - active_threads数: {len(thread_manager.active_threads)}")
                
                for info in thread_manager.active_threads.values():
                    state = info.state.value
                    state_counts[state] = state_counts.get(state, 0) + 1
                
                print(f"   - state_counts: {state_counts}")
                
                # 各フィールドを個別に取得
                total_threads = len(thread_manager.active_threads)
                print(f"   - total_threads: {total_threads}")
                
                # get_active_thread_count()を直接呼ばずに、ロック内で計算
                print("   - active_threads計算開始")
                active_threads = sum(1 for info in thread_manager.active_threads.values() if info.is_active())
                print(f"   - active_threads: {active_threads}")
                
                max_concurrent = thread_manager.max_concurrent_threads
                print(f"   - max_concurrent: {max_concurrent}")
                
                # can_start_new_thread()を直接呼ばずに、ロック内で計算
                print("   - can_start_new計算開始")
                can_start_new = active_threads < thread_manager.max_concurrent_threads
                print(f"   - can_start_new: {can_start_new}")
                
                thread_details = []
                for info in thread_manager.active_threads.values():
                    detail = {
                        'thread_id': info.thread_id,
                        'folder_path': info.folder_path,
                        'state': info.state.value,
                        'duration': info.get_duration(),
                        'error_message': info.error_message
                    }
                    thread_details.append(detail)
                
                print(f"   - thread_details数: {len(thread_details)}")
                
                # 最終的な辞書を作成
                result = {
                    'total_threads': total_threads,
                    'active_threads': active_threads,
                    'max_concurrent': max_concurrent,
                    'can_start_new': can_start_new,
                    'state_counts': state_counts,
                    'thread_details': thread_details
                }
                
                print(f"   - 結果: {result}")
                
        except Exception as e:
            print(f"   - エラー: {e}")
            import traceback
            traceback.print_exc()
        
        print("=== ThreadManagerデバッグ完了 ===")
        
    except Exception as e:
        print(f"デバッグ中にエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_thread_manager()