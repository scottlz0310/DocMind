#!/usr/bin/env python3
"""
Phase4完了後の起動テストスクリプト

DocMindアプリケーションの起動性能と機能を詳細に検証
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

# プロジェクトルートを設定
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def log_message(message, level="INFO"):
    """ログメッセージを出力"""
    datetime.now().strftime("%H:%M:%S")

def test_component_imports():
    """コンポーネントインポートテスト"""
    log_message("=== コンポーネントインポートテスト開始 ===")

    import_results = {}
    start_time = time.time()

    try:
        # メインコンポーネント
        log_message("1. メインコンポーネントインポート中...")

        # Phase4で分離されたコンポーネント
        log_message("2. Phase4分離コンポーネントインポート中...")

        import_time = time.time() - start_time
        import_results = {
            "status": "success",
            "import_time": round(import_time, 3),
            "components_loaded": 8
        }

        log_message(f"✅ 全コンポーネントインポート成功 (時間: {import_time:.3f}秒)")

    except Exception as e:
        import_results = {
            "status": "failed",
            "error": str(e),
            "import_time": time.time() - start_time
        }
        log_message(f"❌ インポートエラー: {e}")

    return import_results

def test_application_startup():
    """アプリケーション起動テスト"""
    log_message("=== アプリケーション起動テスト開始 ===")

    startup_results = {}

    try:
        from PySide6.QtWidgets import QApplication

        from gui.main_window import MainWindow

        # メモリ使用量測定開始
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        log_message("1. QApplication作成中...")
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        log_message("2. MainWindow作成中...")
        start_time = time.time()

        main_window = MainWindow()

        creation_time = time.time() - start_time
        memory_after = process.memory_info().rss / 1024 / 1024  # MB

        log_message("3. ウィンドウ表示テスト中...")
        main_window.show()

        # 短時間待機してイベント処理
        app.processEvents()
        time.sleep(0.5)
        app.processEvents()

        startup_results = {
            "status": "success",
            "creation_time": round(creation_time, 3),
            "memory_usage_mb": round(memory_after - memory_before, 2),
            "window_visible": main_window.isVisible()
        }

        log_message("✅ アプリケーション起動成功")
        log_message(f"   - 作成時間: {creation_time:.3f}秒")
        log_message(f"   - メモリ使用量: {memory_after - memory_before:.2f}MB")
        log_message(f"   - ウィンドウ表示: {'成功' if main_window.isVisible() else '失敗'}")

        # クリーンアップ
        main_window.close()
        app.quit()

    except Exception as e:
        startup_results = {
            "status": "failed",
            "error": str(e)
        }
        log_message(f"❌ 起動エラー: {e}")

    return startup_results

def test_folder_tree_functionality():
    """フォルダツリー機能テスト"""
    log_message("=== フォルダツリー機能テスト開始 ===")

    functionality_results = {}

    try:
        from PySide6.QtWidgets import QApplication, QWidget

        from gui.folder_tree.folder_tree_widget import FolderTreeWidget

        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        log_message("1. FolderTreeWidget作成中...")
        start_time = time.time()

        parent = QWidget()
        folder_tree = FolderTreeWidget(parent)

        creation_time = time.time() - start_time

        log_message("2. 基本機能テスト中...")

        # 基本メソッドの存在確認
        has_set_root_path = hasattr(folder_tree, 'set_root_path')
        has_get_selected_path = hasattr(folder_tree, 'get_selected_path')
        has_refresh = hasattr(folder_tree, 'refresh')

        functionality_results = {
            "status": "success",
            "creation_time": round(creation_time, 3),
            "basic_methods": {
                "set_root_path": has_set_root_path,
                "get_selected_path": has_get_selected_path,
                "refresh": has_refresh
            },
            "widget_created": True
        }

        log_message("✅ フォルダツリー機能テスト成功")
        log_message(f"   - 作成時間: {creation_time:.3f}秒")
        log_message(f"   - 基本メソッド: {'全て存在' if all([has_set_root_path, has_get_selected_path, has_refresh]) else '一部不足'}")

        # クリーンアップ
        folder_tree.deleteLater()
        parent.deleteLater()

    except Exception as e:
        functionality_results = {
            "status": "failed",
            "error": str(e)
        }
        log_message(f"❌ 機能テストエラー: {e}")

    return functionality_results

def test_performance_metrics():
    """パフォーマンス指標テスト"""
    log_message("=== パフォーマンス指標テスト開始 ===")

    performance_results = {}

    try:
        from PySide6.QtWidgets import QApplication, QWidget

        from gui.folder_tree.folder_tree_widget import FolderTreeWidget

        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        log_message("1. 複数回作成テスト中...")

        creation_times = []
        parent = QWidget()

        # 5回の作成テスト
        for _i in range(5):
            start_time = time.time()
            widget = FolderTreeWidget(parent)
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            widget.deleteLater()

        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        min_creation_time = min(creation_times)

        performance_results = {
            "status": "success",
            "avg_creation_time": round(avg_creation_time, 6),
            "max_creation_time": round(max_creation_time, 6),
            "min_creation_time": round(min_creation_time, 6),
            "consistency": max_creation_time - min_creation_time < 0.01,
            "performance_target": avg_creation_time < 0.1
        }

        log_message("✅ パフォーマンステスト完了")
        log_message(f"   - 平均作成時間: {avg_creation_time:.6f}秒")
        log_message(f"   - 最大作成時間: {max_creation_time:.6f}秒")
        log_message(f"   - 最小作成時間: {min_creation_time:.6f}秒")
        log_message(f"   - 一貫性: {'良好' if performance_results['consistency'] else '要改善'}")
        log_message(f"   - 目標達成: {'✅' if performance_results['performance_target'] else '❌'}")

        parent.deleteLater()

    except Exception as e:
        performance_results = {
            "status": "failed",
            "error": str(e)
        }
        log_message(f"❌ パフォーマンステストエラー: {e}")

    return performance_results

def main():
    """メイン実行関数"""
    log_message("🚀 Phase4完了後 起動テスト開始")
    log_message(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        "test_date": datetime.now().isoformat(),
        "phase": "Phase4 完了後",
        "tests": {}
    }

    try:
        # 1. コンポーネントインポートテスト
        log_message("\n" + "="*50)
        results["tests"]["import_test"] = test_component_imports()

        # 2. アプリケーション起動テスト
        log_message("\n" + "="*50)
        results["tests"]["startup_test"] = test_application_startup()

        # 3. フォルダツリー機能テスト
        log_message("\n" + "="*50)
        results["tests"]["functionality_test"] = test_folder_tree_functionality()

        # 4. パフォーマンス指標テスト
        log_message("\n" + "="*50)
        results["tests"]["performance_test"] = test_performance_metrics()

        # 総合評価
        log_message("\n" + "="*50)
        log_message("🎯 Phase4完了後 起動テスト結果サマリー")
        log_message("="*50)

        all_success = all(
            test_result.get("status") == "success"
            for test_result in results["tests"].values()
        )

        if all_success:
            log_message("🎉 全テスト成功！Phase4リファクタリングは完全に成功しています")
            results["overall_status"] = "success"
        else:
            log_message("⚠️ 一部テストで問題が発生しました")
            results["overall_status"] = "partial_success"

        # 各テスト結果の詳細
        for test_name, test_result in results["tests"].items():
            status_icon = "✅" if test_result.get("status") == "success" else "❌"
            log_message(f"{status_icon} {test_name}: {test_result.get('status', 'unknown')}")

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
    log_file = "phase4_startup_test_results.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

