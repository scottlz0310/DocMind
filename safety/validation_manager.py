#!/usr/bin/env python3
"""
検証管理システム
Phase4リファクタリング用の品質検証
"""

import json
from datetime import datetime
from pathlib import Path


class ValidationManager:
    """検証管理クラス"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)

    def validate_file_structure(self) -> bool:
        """ファイル構造の検証"""

        required_files = [
            "src/gui/folder_tree.py",
            "src/gui/main_window.py",
            "src/gui/search_interface.py",
            "REFACTORING_STATUS.md",
            "PHASE4_PROGRESS_TRACKER.md",
        ]

        all_exist = True
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                pass
            else:
                all_exist = False

        return all_exist

    def validate_dependencies(self) -> bool:
        """依存関係の検証"""

        deps_file = self.project_root / "folder_tree_dependencies.json"
        if not deps_file.exists():
            return False

        try:
            with open(deps_file, encoding="utf-8") as f:
                deps_data = json.load(f)

            deps_data.get("imports", [])
            deps_data.get("external_dependencies", [])

            return True
        except Exception:
            return False

    def validate_line_counts(self) -> dict:
        """行数の検証"""

        files_to_check = {
            "folder_tree.py": "src/gui/folder_tree.py",
            "main_window.py": "src/gui/main_window.py",
            "search_interface.py": "src/gui/search_interface.py",
        }

        line_counts = {}
        for name, path in files_to_check.items():
            full_path = self.project_root / path
            if full_path.exists():
                with open(full_path, encoding="utf-8") as f:
                    lines = len(f.readlines())
                line_counts[name] = lines
            else:
                line_counts[name] = 0

        return line_counts

    def generate_validation_report(self) -> dict:
        """検証レポートの生成"""

        report = {
            "validation_date": datetime.now().isoformat(),
            "file_structure_ok": self.validate_file_structure(),
            "dependencies_ok": self.validate_dependencies(),
            "line_counts": self.validate_line_counts(),
        }

        # レポートファイルに保存
        report_file = self.project_root / "PHASE4_VALIDATION_REPORT.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report


def main():
    """検証管理のメイン関数"""
    manager = ValidationManager()
    report = manager.generate_validation_report()

    all_ok = report["file_structure_ok"] and report["dependencies_ok"]

    if all_ok:
        return True
    else:
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
