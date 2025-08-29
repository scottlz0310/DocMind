#!/usr/bin/env python3
"""
DocMind テストカバレッジ測定スクリプト

現在のテスト状況とカバレッジを分析
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# プロジェクトルートを設定
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def log_message(message, level="INFO"):
    """ログメッセージを出力"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def check_coverage_tools():
    """カバレッジツールの確認・インストール"""
    log_message("=== カバレッジツール確認 ===")
    
    try:
        # coverageパッケージの確認
        import coverage
        log_message("✅ coverage パッケージ利用可能")
        return True
    except ImportError:
        log_message("❌ coverage パッケージが見つかりません")
        log_message("インストール中...")
        
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "coverage"], 
                         check=True, capture_output=True)
            log_message("✅ coverage パッケージインストール完了")
            return True
        except subprocess.CalledProcessError as e:
            log_message(f"❌ インストール失敗: {e}")
            return False

def find_test_files():
    """テストファイルを検索"""
    log_message("=== テストファイル検索 ===")
    
    test_patterns = ["test_*.py", "*_test.py", "tests.py"]
    test_files = []
    
    # プロジェクト全体でテストファイルを検索
    for pattern in test_patterns:
        for file_path in project_root.rglob(pattern):
            if file_path.is_file():
                test_files.append(file_path)
    
    log_message(f"発見されたテストファイル: {len(test_files)}個")
    for test_file in test_files:
        rel_path = test_file.relative_to(project_root)
        log_message(f"  - {rel_path}")
    
    return test_files

def analyze_source_files():
    """ソースファイルを分析"""
    log_message("=== ソースファイル分析 ===")
    
    src_dir = project_root / "src"
    if not src_dir.exists():
        log_message("❌ srcディレクトリが見つかりません")
        return []
    
    python_files = []
    for py_file in src_dir.rglob("*.py"):
        if py_file.is_file() and not py_file.name.startswith("__"):
            python_files.append(py_file)
    
    log_message(f"Pythonソースファイル: {len(python_files)}個")
    
    # 主要コンポーネント別に分類
    components = {
        "main_window": [],
        "search_interface": [],
        "folder_tree": [],
        "managers": [],
        "controllers": [],
        "dialogs": [],
        "other": []
    }
    
    for py_file in python_files:
        rel_path = str(py_file.relative_to(src_dir))
        
        if "main_window" in rel_path:
            components["main_window"].append(py_file)
        elif "search_interface" in rel_path:
            components["search_interface"].append(py_file)
        elif "folder_tree" in rel_path:
            components["folder_tree"].append(py_file)
        elif "managers" in rel_path:
            components["managers"].append(py_file)
        elif "controllers" in rel_path:
            components["controllers"].append(py_file)
        elif "dialogs" in rel_path:
            components["dialogs"].append(py_file)
        else:
            components["other"].append(py_file)
    
    for component, files in components.items():
        if files:
            log_message(f"  {component}: {len(files)}ファイル")
    
    return python_files, components

def create_basic_tests():
    """基本的なテストファイルを作成"""
    log_message("=== 基本テスト作成 ===")
    
    tests_dir = project_root / "tests"
    tests_dir.mkdir(exist_ok=True)
    
    # __init__.pyを作成
    init_file = tests_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")
    
    # 基本的なインポートテストを作成
    import_test_content = '''#!/usr/bin/env python3
"""
基本的なインポートテスト
"""

import unittest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

class TestBasicImports(unittest.TestCase):
    """基本的なインポートテスト"""
    
    def test_main_window_import(self):
        """MainWindowのインポートテスト"""
        try:
            from gui.main_window import MainWindow
            self.assertTrue(True, "MainWindow import successful")
        except ImportError as e:
            self.fail(f"MainWindow import failed: {e}")
    
    def test_search_interface_import(self):
        """SearchInterfaceのインポートテスト"""
        try:
            from gui.search_interface import SearchInterface
            self.assertTrue(True, "SearchInterface import successful")
        except ImportError as e:
            self.fail(f"SearchInterface import failed: {e}")
    
    def test_folder_tree_import(self):
        """FolderTreeWidgetのインポートテスト"""
        try:
            from gui.folder_tree.folder_tree_widget import FolderTreeWidget
            self.assertTrue(True, "FolderTreeWidget import successful")
        except ImportError as e:
            self.fail(f"FolderTreeWidget import failed: {e}")

if __name__ == "__main__":
    unittest.main()
'''
    
    import_test_file = tests_dir / "test_imports.py"
    if not import_test_file.exists():
        import_test_file.write_text(import_test_content)
        log_message(f"✅ 基本インポートテスト作成: {import_test_file}")
    
    return [import_test_file]

def run_coverage_analysis():
    """カバレッジ分析を実行"""
    log_message("=== カバレッジ分析実行 ===")
    
    try:
        # テストファイルを検索
        test_files = find_test_files()
        
        # テストファイルがない場合は基本テストを作成
        if not test_files:
            log_message("既存テストファイルなし、基本テストを作成...")
            test_files = create_basic_tests()
        
        if not test_files:
            log_message("❌ 実行可能なテストファイルがありません")
            return None
        
        # カバレッジ測定実行
        log_message("カバレッジ測定開始...")
        
        # coverage runコマンドを構築
        coverage_cmd = [
            sys.executable, "-m", "coverage", "run",
            "--source", str(project_root / "src"),
            "--omit", "*/test*,*/__pycache__/*"
        ]
        
        # 最初のテストファイルを実行
        test_file = test_files[0]
        coverage_cmd.append(str(test_file))
        
        log_message(f"実行コマンド: {' '.join(coverage_cmd)}")
        
        result = subprocess.run(
            coverage_cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log_message("✅ カバレッジ測定完了")
            
            # カバレッジレポート生成
            report_result = subprocess.run(
                [sys.executable, "-m", "coverage", "report"],
                cwd=str(project_root),
                capture_output=True,
                text=True
            )
            
            if report_result.returncode == 0:
                log_message("✅ カバレッジレポート生成完了")
                return report_result.stdout
            else:
                log_message(f"⚠️ レポート生成警告: {report_result.stderr}")
                return report_result.stdout
        else:
            log_message(f"❌ カバレッジ測定失敗: {result.stderr}")
            return None
            
    except Exception as e:
        log_message(f"❌ カバレッジ分析エラー: {e}")
        return None

def analyze_coverage_gaps():
    """カバレッジギャップを分析"""
    log_message("=== カバレッジギャップ分析 ===")
    
    python_files, components = analyze_source_files()
    
    # Phase4で作成されたコンポーネントの分析
    phase4_components = [
        "folder_tree/folder_tree_widget.py",
        "folder_tree/event_handling/",
        "folder_tree/state_management/",
        "folder_tree/ui_management/",
        "folder_tree/performance_helpers.py"
    ]
    
    coverage_gaps = {
        "untested_files": [],
        "phase4_components": [],
        "critical_components": []
    }
    
    src_dir = project_root / "src"
    
    for component_path in phase4_components:
        full_path = src_dir / "gui" / component_path
        
        if full_path.is_file():
            coverage_gaps["phase4_components"].append(full_path)
        elif full_path.is_dir():
            for py_file in full_path.rglob("*.py"):
                if py_file.name != "__init__.py":
                    coverage_gaps["phase4_components"].append(py_file)
    
    # 重要コンポーネントの特定
    critical_files = [
        "gui/main_window.py",
        "gui/search_interface.py"
    ]
    
    for critical_file in critical_files:
        full_path = src_dir / critical_file
        if full_path.exists():
            coverage_gaps["critical_components"].append(full_path)
    
    log_message(f"Phase4コンポーネント: {len(coverage_gaps['phase4_components'])}ファイル")
    log_message(f"重要コンポーネント: {len(coverage_gaps['critical_components'])}ファイル")
    
    return coverage_gaps

def generate_coverage_report():
    """カバレッジレポートを生成"""
    log_message("=== カバレッジレポート生成 ===")
    
    report_content = f"""# DocMind テストカバレッジレポート

## 📊 実行サマリー

**測定日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**測定者**: AI Assistant

## 🔍 現在のテスト状況

"""
    
    # テストファイル分析
    test_files = find_test_files()
    python_files, components = analyze_source_files()
    
    report_content += f"""### テストファイル
- **既存テストファイル**: {len(test_files)}個
- **Pythonソースファイル**: {len(python_files)}個

"""
    
    # コンポーネント別分析
    report_content += "### コンポーネント別ファイル数\n"
    for component, files in components.items():
        if files:
            report_content += f"- **{component}**: {len(files)}ファイル\n"
    
    # カバレッジ実行結果
    coverage_result = run_coverage_analysis()
    
    if coverage_result:
        report_content += f"""
## 📈 カバレッジ測定結果

```
{coverage_result}
```

"""
    else:
        report_content += """
## ⚠️ カバレッジ測定結果

カバレッジ測定を実行しましたが、詳細な結果を取得できませんでした。
基本的なインポートテストは作成されています。

"""
    
    # ギャップ分析
    gaps = analyze_coverage_gaps()
    
    report_content += f"""## 🎯 テストカバレッジ改善提案

### Phase4新規コンポーネント
以下のPhase4で作成されたコンポーネントにテストを追加することを推奨：

"""
    
    for component_file in gaps["phase4_components"][:10]:  # 最初の10ファイル
        rel_path = component_file.relative_to(project_root / "src")
        report_content += f"- `{rel_path}`\n"
    
    if len(gaps["phase4_components"]) > 10:
        report_content += f"- ... 他 {len(gaps['phase4_components']) - 10}ファイル\n"
    
    report_content += f"""
### 重要コンポーネント
以下の重要コンポーネントの包括的テストを推奨：

"""
    
    for critical_file in gaps["critical_components"]:
        rel_path = critical_file.relative_to(project_root / "src")
        report_content += f"- `{rel_path}`\n"
    
    report_content += """
## 🚀 次のステップ

### 短期的改善 (1-2週間)
1. **基本機能テスト**: 各コンポーネントの基本機能テスト作成
2. **インポートテスト**: 全モジュールのインポートテスト拡充
3. **ユニットテスト**: 個別メソッドのユニットテスト追加

### 中期的改善 (1-2ヶ月)
1. **統合テスト**: コンポーネント間の統合テスト
2. **UIテスト**: PySide6 UIコンポーネントのテスト
3. **パフォーマンステスト**: 性能回帰テスト

### 長期的改善 (3-6ヶ月)
1. **E2Eテスト**: エンドツーエンドテスト
2. **自動化**: CI/CDパイプラインでの自動テスト
3. **カバレッジ目標**: 80%以上のカバレッジ達成

## 📋 推奨テストフレームワーク

- **ユニットテスト**: `unittest` (標準ライブラリ)
- **UIテスト**: `pytest-qt` (PySide6対応)
- **カバレッジ**: `coverage.py`
- **モック**: `unittest.mock`

---
**作成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**ステータス**: Phase4完了後の初回測定
**次回測定**: テスト追加後に実施推奨
"""
    
    # レポートファイル保存
    report_file = project_root / "TEST_COVERAGE_REPORT.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    log_message(f"✅ カバレッジレポート作成完了: {report_file}")
    return str(report_file)

def main():
    """メイン実行関数"""
    log_message("🔍 DocMind テストカバレッジ測定開始")
    log_message(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. カバレッジツール確認
        log_message("\n" + "="*50)
        if not check_coverage_tools():
            log_message("❌ カバレッジツールの準備に失敗しました")
            return False
        
        # 2. ソースファイル分析
        log_message("\n" + "="*50)
        python_files, components = analyze_source_files()
        
        # 3. テストファイル検索・作成
        log_message("\n" + "="*50)
        test_files = find_test_files()
        if not test_files:
            test_files = create_basic_tests()
        
        # 4. カバレッジレポート生成
        log_message("\n" + "="*50)
        report_file = generate_coverage_report()
        
        # 5. 結果サマリー
        log_message("\n" + "="*50)
        log_message("🎯 テストカバレッジ測定完了")
        log_message("="*50)
        
        log_message(f"✅ Pythonファイル: {len(python_files)}個")
        log_message(f"✅ テストファイル: {len(test_files)}個")
        log_message(f"✅ レポート作成: {report_file}")
        
        # 改善提案
        log_message("\n📋 改善提案:")
        log_message("1. Phase4新規コンポーネントのテスト追加")
        log_message("2. 重要コンポーネントの包括的テスト")
        log_message("3. 継続的なカバレッジ監視")
        
        return True
        
    except Exception as e:
        log_message(f"テストカバレッジ測定中にエラー発生: {e}", "ERROR")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)