#!/usr/bin/env python3
"""
日次検証スクリプト
毎日の作業後に実行する安全性チェック
"""

import sys
import subprocess
from pathlib import Path

def run_syntax_check():
    """構文チェック実行"""
    print("🔍 構文チェック実行中...")
    target_file = Path("src/gui/folder_tree.py")
    
    if not target_file.exists():
        print(f"❌ ファイルが見つかりません: {target_file}")
        return False
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "py_compile", str(target_file)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 構文チェック成功")
            return True
        else:
            print(f"❌ 構文エラー: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 構文チェック失敗: {e}")
        return False

def run_import_check():
    """インポートチェック実行"""
    print("🔍 インポートチェック実行中...")
    
    try:
        result = subprocess.run([
            sys.executable, "-c", 
            "import sys; sys.path.append('src'); from gui.folder_tree import FolderTreeWidget; print('インポート成功')"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print("✅ インポートチェック成功")
            return True
        else:
            print(f"❌ インポートエラー: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ インポートチェック失敗: {e}")
        return False

def main():
    """メイン処理"""
    print("🛡️ 日次検証開始")
    print("=" * 40)
    
    checks = [
        ("構文チェック", run_syntax_check),
        ("インポートチェック", run_import_check)
    ]
    
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
        print()
    
    # 結果サマリー
    print("📊 検証結果サマリー")
    print("-" * 40)
    all_passed = True
    for name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 全ての検証が成功しました")
        return 0
    else:
        print("\n⚠️ 一部の検証が失敗しました")
        return 1

if __name__ == "__main__":
    sys.exit(main())
