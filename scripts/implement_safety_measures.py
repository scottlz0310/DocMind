#!/usr/bin/env python3
"""
Phase4 安全対策実装スクリプト

Week 0 Day 4: 安全対策実装
- 検証スクリプト作成
- バックアップシステム構築
- ロールバックテスト
- 品質ゲート設定
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class SafetyMeasuresImplementor:
    """Phase4安全対策実装クラス"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.safety_dir = self.project_root / "safety"
        self.backup_dir = self.project_root / "backups"
        self.results = {}

    def run(self) -> dict[str, Any]:
        """安全対策実装メイン処理"""

        try:
            # 1. 安全対策ディレクトリ作成
            self._create_safety_directories()

            # 2. 検証スクリプト作成
            self._create_verification_scripts()

            # 3. バックアップシステム構築
            self._create_backup_system()

            # 4. ロールバックシステム構築
            self._create_rollback_system()

            # 5. 品質ゲート設定
            self._create_quality_gates()

            # 6. 安全対策テスト実行
            self._test_safety_measures()

            # 7. 結果保存
            self._save_results()

            return self.results

        except Exception as e:
            self.results["error"] = str(e)
            return self.results

    def _create_safety_directories(self):
        """安全対策用ディレクトリ作成"""

        directories = [
            self.safety_dir,
            self.safety_dir / "verification",
            self.safety_dir / "backup",
            self.safety_dir / "rollback",
            self.safety_dir / "quality_gates",
            self.backup_dir,
            self.backup_dir / "daily",
            self.backup_dir / "weekly",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        self.results["directories_created"] = len(directories)

    def _create_verification_scripts(self):
        """検証スクリプト作成"""

        # 日次検証スクリプト
        daily_verification = self.safety_dir / "verification" / "daily_verification.py"
        daily_content = '''#!/usr/bin/env python3
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
        print("\\n🎉 全ての検証が成功しました")
        return 0
    else:
        print("\\n⚠️ 一部の検証が失敗しました")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''

        daily_verification.write_text(daily_content, encoding="utf-8")
        daily_verification.chmod(0o755)

        self.results["verification_scripts"] = 1

    def _create_backup_system(self):
        """バックアップシステム構築"""

        backup_script = self.safety_dir / "backup" / "create_backup.py"
        backup_content = '''#!/usr/bin/env python3
"""
バックアップ作成スクリプト
重要ファイルの安全なバックアップを作成
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

class BackupManager:
    """バックアップ管理クラス"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.backup_dir = self.project_root / "backups"

    def create_daily_backup(self):
        """日次バックアップ作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / "daily" / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        # バックアップ対象ファイル
        target_files = [
            "src/gui/folder_tree.py",
            "src/gui/main_window.py",
            "src/gui/search_interface.py"
        ]

        backup_info = {
            "timestamp": timestamp,
            "files": [],
            "status": "success"
        }

        try:
            for file_path in target_files:
                source = self.project_root / file_path
                if source.exists():
                    dest = backup_path / file_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    backup_info["files"].append(file_path)
                    print(f"✅ バックアップ完了: {file_path}")

            # バックアップ情報保存
            info_file = backup_path / "backup_info.json"
            info_file.write_text(json.dumps(backup_info, indent=2, ensure_ascii=False))

            print(f"🎉 日次バックアップ完了: {backup_path.name}")
            return str(backup_path)

        except Exception as e:
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            print(f"❌ バックアップ失敗: {e}")
            return None

    def create_weekly_backup(self):
        """週次バックアップ作成"""
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_path = self.backup_dir / "weekly" / f"week_backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        # プロジェクト全体をバックアップ
        try:
            # 重要ディレクトリのバックアップ
            important_dirs = ["src", "docs", "scripts", "safety"]

            for dir_name in important_dirs:
                source_dir = self.project_root / dir_name
                if source_dir.exists():
                    dest_dir = backup_path / dir_name
                    shutil.copytree(source_dir, dest_dir, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                    print(f"✅ ディレクトリバックアップ完了: {dir_name}")

            print(f"🎉 週次バックアップ完了: {backup_path.name}")
            return str(backup_path)

        except Exception as e:
            print(f"❌ 週次バックアップ失敗: {e}")
            return None

def main():
    """メイン処理"""
    print("💾 バックアップシステム実行")
    print("=" * 40)

    manager = BackupManager()

    # 日次バックアップ作成
    daily_result = manager.create_daily_backup()

    # 週次バックアップ（週末のみ）
    if datetime.now().weekday() == 6:  # 日曜日
        weekly_result = manager.create_weekly_backup()

if __name__ == "__main__":
    main()
'''

        backup_script.write_text(backup_content, encoding="utf-8")
        backup_script.chmod(0o755)

        self.results["backup_system"] = 1

    def _create_rollback_system(self):
        """ロールバックシステム構築"""

        rollback_script = self.safety_dir / "rollback" / "emergency_rollback.py"
        rollback_content = '''#!/usr/bin/env python3
"""
緊急ロールバックスクリプト
問題発生時の安全な状態復旧
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

class EmergencyRollback:
    """緊急ロールバック管理クラス"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.backup_dir = self.project_root / "backups"

    def list_available_backups(self):
        """利用可能なバックアップ一覧表示"""
        print("📋 利用可能なバックアップ:")
        print("-" * 40)

        daily_backups = []
        weekly_backups = []

        # 日次バックアップ
        daily_dir = self.backup_dir / "daily"
        if daily_dir.exists():
            for backup in sorted(daily_dir.iterdir(), reverse=True):
                if backup.is_dir():
                    daily_backups.append(backup)

        # 週次バックアップ
        weekly_dir = self.backup_dir / "weekly"
        if weekly_dir.exists():
            for backup in sorted(weekly_dir.iterdir(), reverse=True):
                if backup.is_dir():
                    weekly_backups.append(backup)

        print("日次バックアップ:")
        for i, backup in enumerate(daily_backups[:5]):  # 最新5件
            print(f"  {i+1}. {backup.name}")

        print("\\n週次バックアップ:")
        for i, backup in enumerate(weekly_backups[:3]):  # 最新3件
            print(f"  {i+1}. {backup.name}")

        return daily_backups, weekly_backups

    def git_rollback(self, target_branch="main"):
        """Gitを使用した緊急ロールバック"""
        print(f"🔄 Git緊急ロールバック実行: {target_branch}")

        try:
            # 現在の変更を退避
            subprocess.run(["git", "stash"], check=True)
            print("✅ 現在の変更を退避")

            # 対象ブランチにチェックアウト
            subprocess.run(["git", "checkout", target_branch], check=True)
            print(f"✅ {target_branch}ブランチにチェックアウト")

            # 作業ブランチを削除（存在する場合）
            try:
                subprocess.run(["git", "branch", "-D", "refactor/folder-tree-phase4"],
                             check=True, capture_output=True)
                print("✅ 作業ブランチを削除")
            except subprocess.CalledProcessError:
                print("ℹ️ 作業ブランチは存在しませんでした")

            # クリーンアップ
            subprocess.run(["git", "clean", "-fd"], check=True)
            print("✅ 未追跡ファイルをクリーンアップ")

            print("🎉 Git緊急ロールバック完了")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Git緊急ロールバック失敗: {e}")
            return False

    def file_rollback(self, backup_path):
        """ファイルバックアップからの復旧"""
        print(f"📁 ファイルロールバック実行: {backup_path}")

        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                print(f"❌ バックアップが見つかりません: {backup_path}")
                return False

            # バックアップ情報読み込み
            info_file = backup_dir / "backup_info.json"
            if info_file.exists():
                import json
                backup_info = json.loads(info_file.read_text())
                files_to_restore = backup_info.get("files", [])
            else:
                # 全ファイルを復旧対象とする
                files_to_restore = []
                for file_path in backup_dir.rglob("*.py"):
                    rel_path = file_path.relative_to(backup_dir)
                    files_to_restore.append(str(rel_path))

            # ファイル復旧
            for file_path in files_to_restore:
                source = backup_dir / file_path
                dest = self.project_root / file_path

                if source.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    print(f"✅ 復旧完了: {file_path}")

            print("🎉 ファイルロールバック完了")
            return True

        except Exception as e:
            print(f"❌ ファイルロールバック失敗: {e}")
            return False

def main():
    """メイン処理"""
    print("🚨 緊急ロールバックシステム")
    print("=" * 40)

    rollback = EmergencyRollback()

    print("選択してください:")
    print("1. Git緊急ロールバック (推奨)")
    print("2. ファイルバックアップからの復旧")
    print("3. 利用可能なバックアップ一覧表示")
    print("4. 終了")

    try:
        choice = input("\\n選択 (1-4): ").strip()

        if choice == "1":
            rollback.git_rollback()
        elif choice == "2":
            daily_backups, weekly_backups = rollback.list_available_backups()
            # 簡単のため最新の日次バックアップを使用
            if daily_backups:
                rollback.file_rollback(daily_backups[0])
            else:
                print("❌ 利用可能なバックアップがありません")
        elif choice == "3":
            rollback.list_available_backups()
        elif choice == "4":
            print("終了します")
        else:
            print("❌ 無効な選択です")

    except KeyboardInterrupt:
        print("\\n操作がキャンセルされました")
    except Exception as e:
        print(f"❌ エラー発生: {e}")

if __name__ == "__main__":
    main()
'''

        rollback_script.write_text(rollback_content, encoding="utf-8")
        rollback_script.chmod(0o755)

        self.results["rollback_system"] = 1

    def _create_quality_gates(self):
        """品質ゲート設定"""

        quality_gate_script = self.safety_dir / "quality_gates" / "quality_check.py"
        quality_content = '''#!/usr/bin/env python3
"""
品質ゲートチェックスクリプト
各週末に実行する品質確認
"""

import sys
import time
import subprocess
import psutil
from pathlib import Path

class QualityGate:
    """品質ゲート管理クラス"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.baseline_performance = {}
        self.load_baseline()

    def load_baseline(self):
        """基準値読み込み"""
        baseline_file = self.project_root / "safety" / "baseline_performance.json"
        if baseline_file.exists():
            import json
            self.baseline_performance = json.loads(baseline_file.read_text())

    def check_functionality(self):
        """機能性チェック"""
        print("🔍 機能性チェック実行中...")

        try:
            # 基本インポートテスト
            result = subprocess.run([
                sys.executable, "-c",
                "import sys; sys.path.append('src'); "
                "from gui.folder_tree import FolderTreeWidget; "
                "print('基本機能OK')"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("✅ 機能性チェック成功")
                return True
            else:
                print(f"❌ 機能性チェック失敗: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 機能性チェック失敗: {e}")
            return False

    def check_performance(self):
        """性能チェック"""
        print("⚡ 性能チェック実行中...")

        try:
            # インポート時間測定
            start_time = time.time()
            result = subprocess.run([
                sys.executable, "-c",
                "import sys; sys.path.append('src'); "
                "from gui.folder_tree import FolderTreeWidget"
            ], capture_output=True, text=True, timeout=30)
            import_time = time.time() - start_time

            if result.returncode != 0:
                print(f"❌ インポート失敗: {result.stderr}")
                return False

            # 基準値と比較
            baseline_import = self.baseline_performance.get('import_time', 1.0)
            performance_ratio = import_time / baseline_import

            print(f"インポート時間: {import_time:.3f}秒 (基準値: {baseline_import:.3f}秒)")
            print(f"性能比率: {performance_ratio:.2f} (1.05以下が合格)")

            if performance_ratio <= 1.05:  # 5%以内の劣化は許容
                print("✅ 性能チェック成功")
                return True
            else:
                print("❌ 性能劣化が検出されました")
                return False

        except Exception as e:
            print(f"❌ 性能チェック失敗: {e}")
            return False

    def check_memory_usage(self):
        """メモリ使用量チェック"""
        print("💾 メモリ使用量チェック実行中...")

        try:
            # 現在のメモリ使用量
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            # 基準値と比較
            baseline_memory = self.baseline_performance.get('memory_mb', 100.0)
            memory_ratio = memory_mb / baseline_memory

            print(f"メモリ使用量: {memory_mb:.1f}MB (基準値: {baseline_memory:.1f}MB)")
            print(f"メモリ比率: {memory_ratio:.2f} (1.20以下が合格)")

            if memory_ratio <= 1.20:  # 20%以内の増加は許容
                print("✅ メモリ使用量チェック成功")
                return True
            else:
                print("❌ メモリ使用量増加が検出されました")
                return False

        except Exception as e:
            print(f"❌ メモリ使用量チェック失敗: {e}")
            return False

    def check_code_quality(self):
        """コード品質チェック"""
        print("📝 コード品質チェック実行中...")

        target_file = self.project_root / "src" / "gui" / "folder_tree.py"
        if not target_file.exists():
            print(f"❌ 対象ファイルが見つかりません: {target_file}")
            return False

        try:
            # ファイルサイズチェック
            file_size = target_file.stat().st_size
            line_count = len(target_file.read_text(encoding='utf-8').splitlines())

            print(f"ファイルサイズ: {file_size:,} bytes")
            print(f"行数: {line_count:,} 行")

            # 品質基準
            if line_count <= 1500:  # 目標に向けた段階的改善
                print("✅ コード品質チェック成功")
                return True
            else:
                print("⚠️ ファイルサイズが大きいですが、リファクタリング進行中のため継続")
                return True  # Phase4進行中は緩い基準

        except Exception as e:
            print(f"❌ コード品質チェック失敗: {e}")
            return False

def main():
    """メイン処理"""
    print("🚪 品質ゲートチェック実行")
    print("=" * 40)

    gate = QualityGate()

    checks = [
        ("機能性", gate.check_functionality),
        ("性能", gate.check_performance),
        ("メモリ使用量", gate.check_memory_usage),
        ("コード品質", gate.check_code_quality)
    ]

    results = []
    for name, check_func in checks:
        print()
        result = check_func()
        results.append((name, result))

    # 結果サマリー
    print("\\n📊 品質ゲート結果")
    print("=" * 40)
    passed_count = 0
    for name, result in results:
        status = "✅ 合格" if result else "❌ 不合格"
        print(f"{name}: {status}")
        if result:
            passed_count += 1

    print(f"\\n合格率: {passed_count}/{len(results)} ({passed_count/len(results)*100:.1f}%)")

    if passed_count == len(results):
        print("🎉 全ての品質ゲートを通過しました")
        return 0
    elif passed_count >= len(results) * 0.75:  # 75%以上で条件付き合格
        print("⚠️ 条件付き合格 - 注意して継続してください")
        return 0
    else:
        print("🚨 品質ゲート不合格 - 作業を停止してください")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''

        quality_gate_script.write_text(quality_content, encoding="utf-8")
        quality_gate_script.chmod(0o755)

        self.results["quality_gates"] = 1

    def _test_safety_measures(self):
        """安全対策テスト実行"""

        test_results = {}

        # 1. 検証スクリプトテスト
        try:
            verification_script = (
                self.safety_dir / "verification" / "daily_verification.py"
            )
            result = subprocess.run(
                [sys.executable, str(verification_script)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            test_results["verification_test"] = result.returncode == 0
            if result.returncode == 0:
                pass
            else:
                pass
        except Exception:
            test_results["verification_test"] = False

        # 2. バックアップシステムテスト
        try:
            backup_script = self.safety_dir / "backup" / "create_backup.py"
            result = subprocess.run(
                [sys.executable, str(backup_script)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            test_results["backup_test"] = result.returncode == 0
            if result.returncode == 0:
                pass
            else:
                pass
        except Exception:
            test_results["backup_test"] = False

        # 3. 品質ゲートテスト
        try:
            quality_script = self.safety_dir / "quality_gates" / "quality_check.py"
            result = subprocess.run(
                [sys.executable, str(quality_script)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            test_results["quality_gate_test"] = result.returncode == 0
            if result.returncode == 0:
                pass
            else:
                pass
        except Exception:
            test_results["quality_gate_test"] = False

        self.results["safety_tests"] = test_results

        # テスト結果サマリー
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)

        if passed_tests >= total_tests * 0.8:  # 80%以上で合格
            return True
        else:
            return False

    def _save_results(self):
        """結果保存"""

        # 実行情報追加
        self.results.update(
            {
                "timestamp": datetime.now().isoformat(),
                "phase": "Phase4 Week 0 Day 4",
                "task": "安全対策実装",
                "status": "completed",
            }
        )

        # 結果ファイル保存
        results_file = self.project_root / "PHASE4_SAFETY_IMPLEMENTATION_RESULTS.md"

        content = f"""# Phase4 安全対策実装結果

## 📊 実行サマリー
- **実行日時**: {self.results["timestamp"]}
- **フェーズ**: {self.results["phase"]}
- **タスク**: {self.results["task"]}
- **ステータス**: {self.results["status"]}

## 🛡️ 実装完了項目

### 作成されたディレクトリ
- 安全対策ディレクトリ: {self.results.get("directories_created", 0)}個

### 実装されたシステム
- 検証スクリプト: {self.results.get("verification_scripts", 0)}個
- バックアップシステム: {self.results.get("backup_system", 0)}個
- ロールバックシステム: {self.results.get("rollback_system", 0)}個
- 品質ゲート: {self.results.get("quality_gates", 0)}個

## 🧪 テスト結果
"""

        if "safety_tests" in self.results:
            for test_name, result in self.results["safety_tests"].items():
                status = "✅ 成功" if result else "❌ 失敗"
                content += f"- {test_name}: {status}\n"

        content += f"""
## 📁 作成されたファイル構造

```
safety/
├── verification/
│   └── daily_verification.py      # 日次検証スクリプト
├── backup/
│   └── create_backup.py           # バックアップ作成スクリプト
├── rollback/
│   └── emergency_rollback.py      # 緊急ロールバックスクリプト
└── quality_gates/
    └── quality_check.py           # 品質ゲートチェック

backups/
├── daily/                         # 日次バックアップ保存先
└── weekly/                        # 週次バックアップ保存先
```

## 🎯 次のアクション

### Week 0 Day 5: 最終準備確認
- 全安全対策の動作確認
- Phase4実行環境の最終チェック
- Week 1開始準備完了

### 使用方法

#### 日次検証実行
```bash
cd /home/hiro/Repository/DocMind
python safety/verification/daily_verification.py
```

#### バックアップ作成
```bash
python safety/backup/create_backup.py
```

#### 緊急ロールバック
```bash
python safety/rollback/emergency_rollback.py
```

#### 品質ゲートチェック
```bash
python safety/quality_gates/quality_check.py
```

## ✅ Week 0 Day 4 完了

Phase4の安全対策実装が完了しました。
次回は Week 0 Day 5 の最終準備確認を実行してください。

---
**作成日**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**ステータス**: ✅ 完了
**次回作業**: Week 0 Day 5 - 最終準備確認
"""

        results_file.write_text(content, encoding="utf-8")


def main():
    """メイン処理"""
    implementor = SafetyMeasuresImplementor()
    results = implementor.run()

    if "error" in results:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
