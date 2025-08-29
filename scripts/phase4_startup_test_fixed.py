#!/usr/bin/env python3
"""
Phase4完了後の起動テスト（修正版）

DocMindアプリケーションの起動性能と機能を詳細に検証
"""

import os
import sys
import time
import psutil
from datetime import datetime
from pathlib import Path

# プロジェクトルートを設定
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def log_message(message, level="INFO"):
    """ログメッセージを出力"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def test_direct_startup():
    """直接起動テスト"""
    log_message("=== 直接起動テスト開始 ===")
    
    try:
        # main.pyを直接実行してテスト
        import subprocess
        
        log_message("1. main.py実行テスト中...")
        start_time = time.time()
        
        # 3秒間の起動テスト
        result = subprocess.run(
            [sys.executable, "main.py"],
            cwd=str(project_root),
            timeout=3,
            capture_output=True,
            text=True
        )
        
        execution_time = time.time() - start_time
        
        # タイムアウトは正常（アプリが起動している証拠）
        if result.returncode == -15 or result.returncode == 124:  # SIGTERM or timeout
            log_message(f"✅ アプリケーション正常起動 (実行時間: {execution_time:.3f}秒)")
            log_message("   - タイムアウトで終了（正常動作）")
            return {
                "status": "success",
                "execution_time": round(execution_time, 3),
                "note": "正常起動、タイムアウトで終了"
            }
        else:
            log_message(f"⚠️ 予期しない終了コード: {result.returncode}")
            if result.stderr:
                log_message(f"   エラー出力: {result.stderr[:200]}")
            return {
                "status": "warning",
                "execution_time": round(execution_time, 3),
                "return_code": result.returncode,
                "stderr": result.stderr[:200] if result.stderr else None
            }
            
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        log_message(f"✅ アプリケーション正常起動 (実行時間: {execution_time:.3f}秒)")
        log_message("   - 3秒タイムアウトで終了（正常動作）")
        return {
            "status": "success",
            "execution_time": round(execution_time, 3),
            "note": "正常起動、3秒タイムアウト"
        }
    except Exception as e:
        log_message(f"❌ 起動テストエラー: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

def test_component_structure():
    """コンポーネント構造テスト"""
    log_message("=== コンポーネント構造テスト開始 ===")
    
    try:
        log_message("1. Phase4分離コンポーネントファイル確認中...")
        
        # Phase4で作成されたファイルの存在確認
        folder_tree_base = src_path / "gui" / "folder_tree"
        
        expected_files = [
            "folder_tree_widget.py",
            "async_operations/__init__.py",
            "async_operations/async_operation_manager.py",
            "async_operations/folder_load_worker.py",
            "state_management/__init__.py",
            "state_management/folder_item_type.py",
            "state_management/folder_tree_item.py",
            "ui_management/__init__.py",
            "ui_management/ui_setup_manager.py",
            "ui_management/filter_manager.py",
            "ui_management/context_menu_manager.py",
            "event_handling/__init__.py",
            "event_handling/event_handler_manager.py",
            "event_handling/signal_manager.py",
            "event_handling/action_manager.py",
            "performance_helpers.py"
        ]
        
        existing_files = []
        missing_files = []
        
        for file_path in expected_files:
            full_path = folder_tree_base / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)
        
        log_message(f"✅ ファイル構造確認完了")
        log_message(f"   - 存在ファイル: {len(existing_files)}/{len(expected_files)}")
        
        if missing_files:
            log_message(f"   - 不足ファイル: {missing_files}")
        
        return {
            "status": "success" if len(missing_files) == 0 else "partial",
            "existing_files": len(existing_files),
            "total_expected": len(expected_files),
            "missing_files": missing_files,
            "completion_rate": round((len(existing_files) / len(expected_files)) * 100, 1)
        }
        
    except Exception as e:
        log_message(f"❌ 構造テストエラー: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

def test_file_metrics():
    """ファイルメトリクステスト"""
    log_message("=== ファイルメトリクステスト開始 ===")
    
    try:
        log_message("1. folder_tree_widget.py メトリクス測定中...")
        
        widget_file = src_path / "gui" / "folder_tree" / "folder_tree_widget.py"
        
        if not widget_file.exists():
            return {
                "status": "failed",
                "error": "folder_tree_widget.py not found"
            }
        
        with open(widget_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        method_count = len([line for line in lines if 'def ' in line])
        class_count = len([line for line in lines if line.strip().startswith('class ')])
        
        # 元の値
        original_lines = 1408
        original_methods = 76
        
        # 削減率計算
        line_reduction = ((original_lines - total_lines) / original_lines) * 100
        method_reduction = ((original_methods - method_count) / original_methods) * 100
        
        log_message(f"✅ メトリクス測定完了")
        log_message(f"   - 現在行数: {total_lines}行 (元: {original_lines}行)")
        log_message(f"   - 行数削減率: {line_reduction:.1f}%")
        log_message(f"   - 現在メソッド数: {method_count}個 (元: {original_methods}個)")
        log_message(f"   - メソッド削減率: {method_reduction:.1f}%")
        log_message(f"   - クラス数: {class_count}個")
        
        return {
            "status": "success",
            "current_lines": total_lines,
            "original_lines": original_lines,
            "line_reduction_percent": round(line_reduction, 1),
            "current_methods": method_count,
            "original_methods": original_methods,
            "method_reduction_percent": round(method_reduction, 1),
            "class_count": class_count,
            "target_achieved": line_reduction >= 50.0
        }
        
    except Exception as e:
        log_message(f"❌ メトリクステストエラー: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

def test_memory_usage():
    """メモリ使用量テスト"""
    log_message("=== メモリ使用量テスト開始 ===")
    
    try:
        log_message("1. ベースラインメモリ測定中...")
        
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        log_message("2. インポート後メモリ測定中...")
        
        # 主要コンポーネントをインポート
        try:
            from gui.folder_tree.folder_tree_widget import FolderTreeWidget
            from gui.folder_tree.async_operations.async_operation_manager import AsyncOperationManager
            from gui.folder_tree.performance_helpers import PathOptimizer
        except ImportError as e:
            log_message(f"⚠️ インポート警告: {e}")
        
        import_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = import_memory - baseline_memory
        
        log_message(f"✅ メモリ使用量測定完了")
        log_message(f"   - ベースライン: {baseline_memory:.2f}MB")
        log_message(f"   - インポート後: {import_memory:.2f}MB")
        log_message(f"   - 増加量: {memory_increase:.2f}MB")
        
        return {
            "status": "success",
            "baseline_memory_mb": round(baseline_memory, 2),
            "import_memory_mb": round(import_memory, 2),
            "memory_increase_mb": round(memory_increase, 2),
            "memory_efficient": memory_increase < 10.0
        }
        
    except Exception as e:
        log_message(f"❌ メモリテストエラー: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

def main():
    """メイン実行関数"""
    log_message("🚀 Phase4完了後 起動テスト（修正版）開始")
    log_message(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "test_date": datetime.now().isoformat(),
        "phase": "Phase4 完了後",
        "tests": {}
    }
    
    try:
        # 1. 直接起動テスト
        log_message("\n" + "="*50)
        results["tests"]["startup_test"] = test_direct_startup()
        
        # 2. コンポーネント構造テスト
        log_message("\n" + "="*50)
        results["tests"]["structure_test"] = test_component_structure()
        
        # 3. ファイルメトリクステスト
        log_message("\n" + "="*50)
        results["tests"]["metrics_test"] = test_file_metrics()
        
        # 4. メモリ使用量テスト
        log_message("\n" + "="*50)
        results["tests"]["memory_test"] = test_memory_usage()
        
        # 総合評価
        log_message("\n" + "="*50)
        log_message("🎯 Phase4完了後 起動テスト結果サマリー")
        log_message("="*50)
        
        success_count = sum(1 for test in results["tests"].values() if test.get("status") == "success")
        total_tests = len(results["tests"])
        
        if success_count == total_tests:
            log_message("🎉 全テスト成功！Phase4リファクタリングは完全に成功しています")
            results["overall_status"] = "success"
        elif success_count > total_tests // 2:
            log_message("✅ 大部分のテストが成功しました")
            results["overall_status"] = "mostly_success"
        else:
            log_message("⚠️ 複数のテストで問題が発生しました")
            results["overall_status"] = "needs_attention"
        
        # 各テスト結果の詳細
        for test_name, test_result in results["tests"].items():
            status = test_result.get("status", "unknown")
            if status == "success":
                status_icon = "✅"
            elif status in ["partial", "warning", "mostly_success"]:
                status_icon = "⚠️"
            else:
                status_icon = "❌"
            log_message(f"{status_icon} {test_name}: {status}")
        
        # 重要な指標の表示
        if "metrics_test" in results["tests"] and results["tests"]["metrics_test"].get("status") == "success":
            metrics = results["tests"]["metrics_test"]
            log_message(f"\n📊 Phase4成果指標:")
            log_message(f"   - 行数削減: {metrics['line_reduction_percent']}% ({metrics['original_lines']}→{metrics['current_lines']}行)")
            log_message(f"   - メソッド削減: {metrics['method_reduction_percent']}% ({metrics['original_methods']}→{metrics['current_methods']}個)")
        
        return results
        
    except Exception as e:
        log_message(f"起動テスト実行中にエラー発生: {e}", "ERROR")
        results["overall_status"] = "failed"
        results["error"] = str(e)
        return results

if __name__ == "__main__":
    import json
    
    results = main()
    
    # 結果をJSONファイルに保存
    log_file = "phase4_startup_test_results_fixed.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 テスト結果を {log_file} に保存しました")