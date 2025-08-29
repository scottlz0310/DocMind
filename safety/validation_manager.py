#!/usr/bin/env python3
"""
検証管理システム
Phase4リファクタリング用の品質検証
"""

import os
import json
from pathlib import Path
from datetime import datetime

class ValidationManager:
    """検証管理クラス"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
    
    def validate_file_structure(self) -> bool:
        """ファイル構造の検証"""
        print("📁 ファイル構造検証中...")
        
        required_files = [
            "src/gui/folder_tree.py",
            "src/gui/main_window.py",
            "src/gui/search_interface.py",
            "REFACTORING_STATUS.md",
            "PHASE4_PROGRESS_TRACKER.md"
        ]
        
        all_exist = True
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path}")
                all_exist = False
        
        return all_exist
    
    def validate_dependencies(self) -> bool:
        """依存関係の検証"""
        print("🔗 依存関係検証中...")
        
        deps_file = self.project_root / "folder_tree_dependencies.json"
        if not deps_file.exists():
            print("❌ 依存関係分析結果が見つかりません")
            return False
        
        try:
            with open(deps_file, 'r', encoding='utf-8') as f:
                deps_data = json.load(f)
            
            imports = deps_data.get('imports', [])
            external_deps = deps_data.get('external_dependencies', [])
            
            print(f"✅ import数: {len(imports)}")
            print(f"✅ 外部依存数: {len(external_deps)}")
            
            return True
        except Exception as e:
            print(f"❌ 依存関係検証エラー: {e}")
            return False
    
    def validate_line_counts(self) -> dict:
        """行数の検証"""
        print("📊 行数検証中...")
        
        files_to_check = {
            "folder_tree.py": "src/gui/folder_tree.py",
            "main_window.py": "src/gui/main_window.py",
            "search_interface.py": "src/gui/search_interface.py"
        }
        
        line_counts = {}
        for name, path in files_to_check.items():
            full_path = self.project_root / path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                line_counts[name] = lines
                print(f"✅ {name}: {lines}行")
            else:
                line_counts[name] = 0
                print(f"❌ {name}: ファイルが見つかりません")
        
        return line_counts
    
    def generate_validation_report(self) -> dict:
        """検証レポートの生成"""
        print("📋 検証レポート生成中...")
        
        report = {
            "validation_date": datetime.now().isoformat(),
            "file_structure_ok": self.validate_file_structure(),
            "dependencies_ok": self.validate_dependencies(),
            "line_counts": self.validate_line_counts()
        }
        
        # レポートファイルに保存
        report_file = self.project_root / "PHASE4_VALIDATION_REPORT.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 検証レポート保存: {report_file}")
        return report

def main():
    """検証管理のメイン関数"""
    manager = ValidationManager()
    report = manager.generate_validation_report()
    
    all_ok = (
        report['file_structure_ok'] and 
        report['dependencies_ok']
    )
    
    if all_ok:
        print("✅ 全検証項目成功")
        return True
    else:
        print("❌ 一部検証項目で問題があります")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)