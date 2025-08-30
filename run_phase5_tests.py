#!/usr/bin/env python3
"""
Phase5テスト実行スクリプト

新しいテストアーキテクチャでのテスト実行
- ユニットテスト: 各コンポーネントの独立テスト
- 統合テスト: コンポーネント間の接続確認のみ
"""

import sys
import subprocess
import time
from pathlib import Path


def run_command(command: list, description: str) -> bool:
    """コマンドを実行し、結果を表示"""
    print(f"\n🔄 {description}")
    print(f"実行コマンド: {' '.join(command)}")
    
    start_time = time.time()
    try:
        # 仮想環境のPythonを使用
        if command[0] == "python":
            venv_python = Path(__file__).parent / "venv" / "bin" / "python"
            if venv_python.exists():
                command[0] = str(venv_python)
            else:
                command[0] = "python"
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        elapsed_time = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} 成功 ({elapsed_time:.2f}秒)")
            if result.stdout:
                print(f"出力:\n{result.stdout}")
            return True
        else:
            print(f"❌ {description} 失敗 ({elapsed_time:.2f}秒)")
            if result.stderr:
                print(f"エラー:\n{result.stderr}")
            if result.stdout:
                print(f"出力:\n{result.stdout}")
            return False
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ {description} 例外発生 ({elapsed_time:.2f}秒): {e}")
        return False


def main():
    """メイン実行関数"""
    print("=" * 60)
    print("🚀 Phase5テスト環境 実行開始")
    print("目標: ユニットテストで品質保証、統合テストは接続確認のみ")
    print("=" * 60)
    
    # 仮想環境の確認
    if not Path("venv").exists():
        print("❌ 仮想環境が見つかりません。先に仮想環境を作成してください。")
        return False
    
    # テストディレクトリの確認
    test_dir = Path("tests")
    if not test_dir.exists():
        print("❌ testsディレクトリが見つかりません。")
        return False
    
    success_count = 0
    total_tests = 0
    
    # 1. ユニットテスト実行
    print("\n" + "=" * 40)
    print("📋 Phase 1: ユニットテスト実行")
    print("=" * 40)
    
    unit_tests = [
        (["python", "-m", "pytest", "tests/unit/", "-v", "--tb=short"], 
         "ユニットテスト全体"),
        (["python", "-m", "pytest", "tests/unit/managers/", "-v"], 
         "マネージャー系ユニットテスト"),
        (["python", "-m", "pytest", "tests/unit/controllers/", "-v"], 
         "コントローラー系ユニットテスト"),
        (["python", "-m", "pytest", "tests/unit/search/", "-v"], 
         "検索機能系ユニットテスト"),
        (["python", "-m", "pytest", "tests/unit/folder_tree/", "-v"], 
         "フォルダツリー系ユニットテスト"),
    ]
    
    for command, description in unit_tests:
        total_tests += 1
        if run_command(command, description):
            success_count += 1
    
    # 2. 統合テスト実行
    print("\n" + "=" * 40)
    print("🔗 Phase 2: 統合テスト実行")
    print("=" * 40)
    
    integration_tests = [
        (["python", "-m", "pytest", "tests/integration/", "-v", "--tb=short"], 
         "統合テスト全体"),
        (["python", "-m", "pytest", "tests/integration/test_main_window_integration.py", "-v"], 
         "メインウィンドウ統合テスト"),
        (["python", "-m", "pytest", "tests/integration/test_search_flow_integration.py", "-v"], 
         "検索フロー統合テスト"),
    ]
    
    for command, description in integration_tests:
        total_tests += 1
        if run_command(command, description):
            success_count += 1
    
    # 3. カバレッジ測定
    print("\n" + "=" * 40)
    print("📊 Phase 3: カバレッジ測定")
    print("=" * 40)
    
    coverage_tests = [
        (["python", "-m", "pytest", "tests/", "--cov=src", "--cov-report=term-missing", "--cov-report=html"], 
         "カバレッジ付きテスト実行"),
    ]
    
    for command, description in coverage_tests:
        total_tests += 1
        if run_command(command, description):
            success_count += 1
    
    # 4. テスト品質チェック
    print("\n" + "=" * 40)
    print("🔍 Phase 4: テスト品質チェック")
    print("=" * 40)
    
    quality_tests = [
        (["python", "-m", "pytest", "tests/", "--collect-only"], 
         "テスト収集確認"),
        (["python", "-c", "import tests; print('テストモジュールのインポート成功')"], 
         "テストモジュールインポート確認"),
    ]
    
    for command, description in quality_tests:
        total_tests += 1
        if run_command(command, description):
            success_count += 1
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📈 Phase5テスト実行結果サマリー")
    print("=" * 60)
    
    success_rate = (success_count / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"✅ 成功: {success_count}/{total_tests} ({success_rate:.1f}%)")
    
    if success_count == total_tests:
        print("🎉 全テスト成功！Phase5テスト環境が正常に動作しています。")
        print("\n📋 次のステップ:")
        print("  1. htmlcov/index.html でカバレッジレポートを確認")
        print("  2. 不足しているテストケースを追加")
        print("  3. カバレッジ80%以上を目指す")
        return True
    else:
        failed_count = total_tests - success_count
        print(f"❌ {failed_count}個のテストが失敗しました。")
        print("\n🔧 対処方法:")
        print("  1. 失敗したテストのエラーメッセージを確認")
        print("  2. 依存関係やモックの設定を見直し")
        print("  3. テストの実装を修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)