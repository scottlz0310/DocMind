#!/usr/bin/env python3
"""
DocMind - デプロイメントテストスクリプト
Windows環境でのアプリケーション展開テスト

このスクリプトは以下のテストを実行します:
1. インストーラーの動作確認
2. アプリケーションの起動テスト
3. 基本機能の動作確認
4. アンインストールテスト
"""

import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

import psutil

# テスト結果の記録
test_results = []

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("deployment_test.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class TestResult:
    """テスト結果を格納するクラス"""

    def __init__(
        self,
        test_name: str,
        success: bool,
        message: str = "",
        details: dict[str, Any] = None,
    ):
        self.test_name = test_name
        self.success = success
        self.message = message
        self.details = details or {}
        self.timestamp = time.time()


class DeploymentTester:
    """デプロイメントテスタークラス"""

    def __init__(self, installer_path: str):
        self.installer_path = Path(installer_path)
        self.test_results: list[TestResult] = []
        self.temp_dir = Path(tempfile.mkdtemp(prefix="docmind_test_"))
        self.install_dir = None
        self.app_process = None

        logger.info(f"テスト用一時ディレクトリ: {self.temp_dir}")

    def run_all_tests(self) -> bool:
        """すべてのテストを実行"""
        logger.info("DocMind デプロイメントテストを開始します")

        try:
            # 1. 前提条件チェック
            if not self._check_prerequisites():
                return False

            # 2. インストーラーテスト
            if not self._test_installer():
                return False

            # 3. アプリケーション起動テスト
            if not self._test_application_startup():
                return False

            # 4. 基本機能テスト
            if not self._test_basic_functionality():
                return False

            # 5. パフォーマンステスト
            self._test_performance()

            # 6. アンインストールテスト
            self._test_uninstaller()

            # 7. テスト結果の生成
            self._generate_test_report()

            logger.info("すべてのテストが完了しました")
            return True

        except Exception as e:
            logger.error(f"テスト実行中にエラーが発生: {e}")
            self._add_test_result("全体テスト", False, f"予期しないエラー: {e}")
            return False
        finally:
            self._cleanup()

    def _check_prerequisites(self) -> bool:
        """前提条件をチェック"""
        logger.info("前提条件をチェック中...")

        # インストーラーファイルの存在確認
        if not self.installer_path.exists():
            self._add_test_result(
                "前提条件チェック",
                False,
                f"インストーラーが見つかりません: {self.installer_path}",
            )
            return False

        # Windows バージョンチェック
        try:
            import platform

            windows_version = platform.version()
            logger.info(f"Windows バージョン: {windows_version}")

            # Windows 10以降かチェック(簡易)
            version_parts = windows_version.split(".")
            if len(version_parts) >= 1 and int(version_parts[0]) < 10:
                self._add_test_result("前提条件チェック", False, "Windows 10以降が必要です")
                return False

        except Exception as e:
            logger.warning(f"Windowsバージョンチェックに失敗: {e}")

        # 利用可能メモリチェック
        try:
            memory = psutil.virtual_memory()
            if memory.total < 4 * 1024 * 1024 * 1024:  # 4GB
                logger.warning("推奨メモリ容量(4GB)を下回っています")
        except Exception as e:
            logger.warning(f"メモリチェックに失敗: {e}")

        # ディスク容量チェック
        try:
            disk = psutil.disk_usage("C:")
            if disk.free < 2 * 1024 * 1024 * 1024:  # 2GB
                self._add_test_result(
                    "前提条件チェック",
                    False,
                    "ディスク容量が不足しています(最低2GB必要)",
                )
                return False
        except Exception as e:
            logger.warning(f"ディスク容量チェックに失敗: {e}")

        self._add_test_result("前提条件チェック", True, "すべての前提条件を満たしています")
        return True

    def _test_installer(self) -> bool:
        """インストーラーのテスト"""
        logger.info("インストーラーをテスト中...")

        try:
            # サイレントインストールの実行
            install_dir = self.temp_dir / "DocMind"

            cmd = [
                str(self.installer_path),
                "/SILENT",
                "/NORESTART",
                f"/DIR={install_dir}",
            ]

            logger.info(f"インストールコマンド: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,  # 5分でタイムアウト
            )

            if result.returncode != 0:
                self._add_test_result(
                    "インストーラーテスト",
                    False,
                    f"インストールに失敗: {result.stderr}",
                )
                return False

            # インストール結果の確認
            exe_path = install_dir / "DocMind.exe"
            if not exe_path.exists():
                self._add_test_result(
                    "インストーラーテスト",
                    False,
                    f"実行ファイルが見つかりません: {exe_path}",
                )
                return False

            self.install_dir = install_dir
            self._add_test_result("インストーラーテスト", True, f"インストール成功: {install_dir}")
            return True

        except subprocess.TimeoutExpired:
            self._add_test_result("インストーラーテスト", False, "インストールがタイムアウトしました")
            return False
        except Exception as e:
            self._add_test_result("インストーラーテスト", False, f"インストールエラー: {e}")
            return False

    def _test_application_startup(self) -> bool:
        """アプリケーション起動テスト"""
        logger.info("アプリケーション起動をテスト中...")

        if not self.install_dir:
            self._add_test_result("起動テスト", False, "インストールディレクトリが不明です")
            return False

        try:
            exe_path = self.install_dir / "DocMind.exe"

            # アプリケーションを起動
            self.app_process = subprocess.Popen([str(exe_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # 起動を待機
            time.sleep(10)

            # プロセスが実行中かチェック
            if self.app_process.poll() is not None:
                stdout, stderr = self.app_process.communicate()
                self._add_test_result(
                    "起動テスト",
                    False,
                    f"アプリケーションが終了しました: {stderr.decode('utf-8', errors='ignore')}",
                )
                return False

            # プロセスが存在するかチェック
            try:
                process = psutil.Process(self.app_process.pid)
                if process.is_running():
                    self._add_test_result(
                        "起動テスト",
                        True,
                        f"アプリケーションが正常に起動しました (PID: {self.app_process.pid})",
                    )
                    return True
                else:
                    self._add_test_result("起動テスト", False, "プロセスが実行されていません")
                    return False
            except psutil.NoSuchProcess:
                self._add_test_result("起動テスト", False, "プロセスが見つかりません")
                return False

        except Exception as e:
            self._add_test_result("起動テスト", False, f"起動テストエラー: {e}")
            return False

    def _test_basic_functionality(self) -> bool:
        """基本機能のテスト"""
        logger.info("基本機能をテスト中...")

        if not self.app_process or self.app_process.poll() is not None:
            self._add_test_result("基本機能テスト", False, "アプリケーションが実行されていません")
            return False

        try:
            # データディレクトリの作成確認
            user_data_dir = Path.home() / "DocMind"
            time.sleep(5)  # データディレクトリ作成を待機

            if user_data_dir.exists():
                self._add_test_result(
                    "データディレクトリ作成",
                    True,
                    f"データディレクトリが作成されました: {user_data_dir}",
                )
            else:
                self._add_test_result(
                    "データディレクトリ作成",
                    False,
                    "データディレクトリが作成されませんでした",
                )

            # 設定ファイルの確認
            config_file = user_data_dir / "config.json"
            if config_file.exists():
                self._add_test_result("設定ファイル作成", True, "設定ファイルが作成されました")
            else:
                self._add_test_result("設定ファイル作成", False, "設定ファイルが作成されませんでした")

            # ログファイルの確認
            log_dir = user_data_dir / "logs"
            if log_dir.exists() and any(log_dir.glob("*.log")):
                self._add_test_result("ログファイル作成", True, "ログファイルが作成されました")
            else:
                self._add_test_result("ログファイル作成", False, "ログファイルが作成されませんでした")

            return True

        except Exception as e:
            self._add_test_result("基本機能テスト", False, f"基本機能テストエラー: {e}")
            return False

    def _test_performance(self) -> None:
        """パフォーマンステスト"""
        logger.info("パフォーマンスをテスト中...")

        if not self.app_process or self.app_process.poll() is not None:
            self._add_test_result("パフォーマンステスト", False, "アプリケーションが実行されていません")
            return

        try:
            process = psutil.Process(self.app_process.pid)

            # メモリ使用量の測定
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            if memory_mb < 500:  # 500MB未満
                self._add_test_result("メモリ使用量", True, f"メモリ使用量: {memory_mb:.1f}MB")
            else:
                self._add_test_result(
                    "メモリ使用量",
                    False,
                    f"メモリ使用量が多すぎます: {memory_mb:.1f}MB",
                )

            # CPU使用率の測定
            cpu_percent = process.cpu_percent(interval=5)
            if cpu_percent < 50:  # 50%未満
                self._add_test_result("CPU使用率", True, f"CPU使用率: {cpu_percent:.1f}%")
            else:
                self._add_test_result("CPU使用率", False, f"CPU使用率が高すぎます: {cpu_percent:.1f}%")

        except Exception as e:
            self._add_test_result("パフォーマンステスト", False, f"パフォーマンステストエラー: {e}")

    def _test_uninstaller(self) -> None:
        """アンインストーラーのテスト"""
        logger.info("アンインストーラーをテスト中...")

        try:
            # アプリケーションプロセスを終了
            if self.app_process and self.app_process.poll() is None:
                self.app_process.terminate()
                time.sleep(3)
                if self.app_process.poll() is None:
                    self.app_process.kill()
                    time.sleep(1)

            # アンインストーラーの実行
            uninstall_script = self.install_dir / "uninstall.bat"
            if uninstall_script.exists():
                # バッチファイルによるアンインストール
                result = subprocess.run(
                    [str(uninstall_script)], check=False, capture_output=True, text=True, timeout=60
                )

                if result.returncode == 0:
                    self._add_test_result("アンインストールテスト", True, "アンインストールが成功しました")
                else:
                    self._add_test_result(
                        "アンインストールテスト",
                        False,
                        f"アンインストールに失敗: {result.stderr}",
                    )
            else:
                # 手動でディレクトリを削除
                if self.install_dir.exists():
                    shutil.rmtree(self.install_dir, ignore_errors=True)
                self._add_test_result("アンインストールテスト", True, "手動でアンインストールしました")

        except Exception as e:
            self._add_test_result("アンインストールテスト", False, f"アンインストールエラー: {e}")

    def _add_test_result(
        self,
        test_name: str,
        success: bool,
        message: str = "",
        details: dict[str, Any] = None,
    ) -> None:
        """テスト結果を追加"""
        result = TestResult(test_name, success, message, details)
        self.test_results.append(result)

        status = "成功" if success else "失敗"
        logger.info(f"[{status}] {test_name}: {message}")

    def _generate_test_report(self) -> None:
        """テストレポートを生成"""
        logger.info("テストレポートを生成中...")

        report = {
            "test_summary": {
                "total_tests": len(self.test_results),
                "passed": sum(1 for r in self.test_results if r.success),
                "failed": sum(1 for r in self.test_results if not r.success),
                "timestamp": time.time(),
            },
            "test_results": [],
        }

        for result in self.test_results:
            report["test_results"].append({
                "test_name": result.test_name,
                "success": result.success,
                "message": result.message,
                "details": result.details,
                "timestamp": result.timestamp,
            })

        # JSONレポートの保存
        report_file = Path("deployment_test_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # テキストレポートの生成
        text_report = self._generate_text_report(report)
        text_report_file = Path("deployment_test_report.txt")
        with open(text_report_file, "w", encoding="utf-8") as f:
            f.write(text_report)

        logger.info(f"テストレポートを生成しました: {report_file}, {text_report_file}")

    def _generate_text_report(self, report: dict[str, Any]) -> str:
        """テキスト形式のレポートを生成"""
        lines = []
        lines.append("=" * 60)
        lines.append("DocMind デプロイメントテストレポート")
        lines.append("=" * 60)
        lines.append("")

        summary = report["test_summary"]
        lines.append("テスト概要:")
        lines.append(f"  総テスト数: {summary['total_tests']}")
        lines.append(f"  成功: {summary['passed']}")
        lines.append(f"  失敗: {summary['failed']}")
        lines.append(f"  成功率: {summary['passed'] / summary['total_tests'] * 100:.1f}%")
        lines.append("")

        lines.append("詳細結果:")
        lines.append("-" * 40)

        for result in report["test_results"]:
            status = "✓" if result["success"] else "✗"
            lines.append(f"{status} {result['test_name']}")
            if result["message"]:
                lines.append(f"    {result['message']}")
            lines.append("")

        return "\n".join(lines)

    def _cleanup(self) -> None:
        """クリーンアップ処理"""
        logger.info("クリーンアップを実行中...")

        try:
            # アプリケーションプロセスの終了
            if self.app_process and self.app_process.poll() is None:
                self.app_process.terminate()
                time.sleep(3)
                if self.app_process.poll() is None:
                    self.app_process.kill()

            # 一時ディレクトリの削除
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)

            logger.info("クリーンアップが完了しました")

        except Exception as e:
            logger.error(f"クリーンアップエラー: {e}")


def main():
    """メイン関数"""
    if len(sys.argv) != 2:
        return 1

    installer_path = sys.argv[1]

    if not os.path.exists(installer_path):
        return 1

    tester = DeploymentTester(installer_path)
    success = tester.run_all_tests()

    if success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
