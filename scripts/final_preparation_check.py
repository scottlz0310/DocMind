#!/usr/bin/env python3
"""
Phase4最終準備確認スクリプト
Week 0 Day 5: 最終準備確認

全安全対策の動作確認とPhase4実行環境の最終チェックを実行
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def check_virtual_environment():
    """仮想環境の確認"""
    print("🔍 仮想環境確認...")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 仮想環境がアクティブです")
        return True
    else:
        print("❌ 仮想環境がアクティブではありません")
        return False

def check_safety_measures():
    """安全対策の確認"""
    print("\n🛡️ 安全対策確認...")
    
    safety_dir = Path("safety")
    if not safety_dir.exists():
        print("❌ safety/ディレクトリが存在しません")
        return False
    
    required_files = [
        "safety/backup_manager.py",
        "safety/rollback_manager.py", 
        "safety/test_runner.py",
        "safety/validation_manager.py"
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            all_exist = False
    
    return all_exist

def check_phase4_target():
    """Phase4対象ファイルの確認"""
    print("\n🎯 Phase4対象ファイル確認...")
    
    target_file = Path("src/gui/folder_tree.py")
    if not target_file.exists():
        print("❌ folder_tree.py が存在しません")
        return False
    
    # ファイルサイズ確認
    with open(target_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        line_count = len(lines)
    
    print(f"✅ folder_tree.py: {line_count}行")
    
    if line_count > 1000:
        print("✅ リファクタリング対象として適切なサイズです")
        return True
    else:
        print("⚠️ ファイルサイズが小さいです")
        return True

def check_dependencies():
    """依存関係分析結果の確認"""
    print("\n📊 依存関係分析結果確認...")
    
    deps_file = Path("folder_tree_dependencies.json")
    if not deps_file.exists():
        print("❌ folder_tree_dependencies.json が存在しません")
        return False
    
    try:
        with open(deps_file, 'r', encoding='utf-8') as f:
            deps_data = json.load(f)
        
        print(f"✅ 依存関係分析結果: {len(deps_data.get('imports', []))}個のimport")
        print(f"✅ 外部依存: {len(deps_data.get('external_dependencies', []))}個")
        return True
    except Exception as e:
        print(f"❌ 依存関係分析結果の読み込みエラー: {e}")
        return False

def check_backup_system():
    """バックアップシステムの確認"""
    print("\n💾 バックアップシステム確認...")
    
    backup_dir = Path("backups")
    if not backup_dir.exists():
        print("❌ backups/ディレクトリが存在しません")
        return False
    
    # 最新バックアップの確認
    backup_files = list(backup_dir.glob("*.tar.gz"))
    if backup_files:
        latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
        print(f"✅ 最新バックアップ: {latest_backup.name}")
        return True
    else:
        print("⚠️ バックアップファイルが見つかりません")
        return False

def check_test_environment():
    """テスト環境の確認"""
    print("\n🧪 テスト環境確認...")
    
    try:
        # 基本的なimportテスト
        result = subprocess.run([
            sys.executable, "-c", 
            "import sys; sys.path.insert(0, 'src'); from gui.folder_tree import FolderTreeWidget; print('✅ folder_tree.py import成功')"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ folder_tree.py のimportテスト成功")
            return True
        else:
            print(f"❌ folder_tree.py のimportテスト失敗: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return False

def check_progress_tracking():
    """進捗追跡システムの確認"""
    print("\n📈 進捗追跡システム確認...")
    
    required_files = [
        "PHASE4_PROGRESS_TRACKER.md",
        "PHASE4_SAFETY_PLAN.md",
        "FOLDER_TREE_ANALYSIS.md"
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            all_exist = False
    
    return all_exist

def generate_final_report():
    """最終確認レポートの生成"""
    print("\n📋 最終確認レポート生成...")
    
    report = {
        "check_date": datetime.now().isoformat(),
        "phase": "Phase4準備完了確認",
        "target_file": "src/gui/folder_tree.py",
        "status": "準備完了",
        "next_action": "Phase4 Week1開始可能"
    }
    
    report_file = Path("PHASE4_FINAL_PREPARATION_REPORT.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"""# Phase4最終準備確認レポート

**確認日時**: {report['check_date']}
**対象フェーズ**: {report['phase']}
**対象ファイル**: {report['target_file']}

## 確認結果

✅ 全ての準備項目が完了しました

## 次回アクション

{report['next_action']}

---
自動生成: scripts/final_preparation_check.py
""")
    
    print(f"✅ レポート生成完了: {report_file}")
    return True

def main():
    """メイン実行関数"""
    print("🎯 Phase4最終準備確認開始")
    print("=" * 50)
    
    checks = [
        ("仮想環境", check_virtual_environment),
        ("安全対策", check_safety_measures),
        ("Phase4対象ファイル", check_phase4_target),
        ("依存関係分析", check_dependencies),
        ("バックアップシステム", check_backup_system),
        ("テスト環境", check_test_environment),
        ("進捗追跡システム", check_progress_tracking)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name}確認中にエラー: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📊 最終確認結果")
    print("=" * 50)
    
    success_count = 0
    for name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{name}: {status}")
        if result:
            success_count += 1
    
    print(f"\n成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    
    if success_count == len(results):
        print("\n🎉 Phase4実行準備完了！")
        print("Week 1開始可能です")
        generate_final_report()
        return True
    else:
        print("\n⚠️ 一部の確認項目で問題があります")
        print("問題を解決してから再実行してください")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)