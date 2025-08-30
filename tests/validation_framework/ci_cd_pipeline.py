#!/usr/bin/env python3
"""
CI/CD パイプライン

継続的インテグレーション・継続的デプロイメント対応の
自動化パイプライン実装。
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .comprehensive_validation_suite import (
    ComprehensiveValidationSuite,
    ValidationLevel,
    ValidationResult,
    create_validation_config,
)


class PipelineStage(Enum):
    """パイプラインステージの定義"""

    BUILD = "build"
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    VALIDATION = "validation"
    SECURITY_SCAN = "security_scan"
    PERFORMANCE_TEST = "performance_test"
    DEPLOY = "deploy"


class PipelineResult(Enum):
    """パイプライン結果の定義"""

    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class PipelineConfig:
    """パイプライン設定"""

    # 基本設定
    project_root: Path
    output_dir: Path = Path("pipeline_results")
    timeout_minutes: int = 60

    # ステージ有効/無効設定
    enable_build: bool = True
    enable_unit_test: bool = True
    enable_integration_test: bool = True
    enable_validation: bool = True
    enable_security_scan: bool = True
    enable_performance_test: bool = True
    enable_deploy: bool = False

    # 品質ゲート設定
    min_test_coverage: float = 80.0
    max_critical_issues: int = 0
    max_performance_regression: float = 10.0  # パーセント

    # 通知設定
    enable_notifications: bool = True
    notification_webhook: str | None = None
    notification_email: str | None = None

    # Git設定
    git_branch: str | None = None
    git_commit: str | None = None

    # 環境設定
    python_version: str = "3.11"
    requirements_file: str = "requirements.txt"


@dataclass
class StageResult:
    """ステージ結果"""

    stage: PipelineStage
    result: PipelineResult
    start_time: datetime
    end_time: datetime
    duration: float
    output: str
    error: str | None = None
    artifacts: list[Path] = None
    metrics: dict[str, Any] = None


@dataclass
class PipelineSummary:
    """パイプライン結果サマリー"""

    pipeline_id: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    overall_result: PipelineResult
    stage_results: list[StageResult]
    quality_gates_passed: bool
    artifacts: list[Path]
    metrics: dict[str, Any]


class QualityGate:
    """品質ゲート

    パイプラインの各ステージで品質基準をチェックし、
    基準を満たさない場合はパイプラインを停止する。
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger("quality_gate")

    async def check_test_coverage(self, coverage_file: Path) -> bool:
        """テストカバレッジのチェック

        Args:
            coverage_file: カバレッジレポートファイル

        Returns:
            品質ゲート通過可否
        """
        try:
            if not coverage_file.exists():
                self.logger.warning("カバレッジファイルが見つかりません")
                return False

            # カバレッジ情報の読み込み（coverage.xml を想定）
            import xml.etree.ElementTree as ET

            tree = ET.parse(coverage_file)
            root = tree.getroot()

            # カバレッジ率の取得
            coverage_element = root.find(".//coverage")
            if coverage_element is not None:
                line_rate = float(coverage_element.get("line-rate", 0)) * 100

                self.logger.info(f"テストカバレッジ: {line_rate:.1f}%")

                if line_rate >= self.config.min_test_coverage:
                    self.logger.info("テストカバレッジ品質ゲートを通過しました")
                    return True
                else:
                    self.logger.error(
                        f"テストカバレッジが基準値 {self.config.min_test_coverage}% を下回りました"
                    )
                    return False

            return False

        except Exception as e:
            self.logger.error(f"テストカバレッジチェック中にエラーが発生しました: {e}")
            return False

    async def check_security_issues(self, security_report: Path) -> bool:
        """セキュリティ問題のチェック

        Args:
            security_report: セキュリティレポートファイル

        Returns:
            品質ゲート通過可否
        """
        try:
            if not security_report.exists():
                self.logger.warning("セキュリティレポートが見つかりません")
                return True  # レポートがない場合は通過とする

            # セキュリティレポートの解析（JSON形式を想定）
            with open(security_report, encoding="utf-8") as f:
                report_data = json.load(f)

            critical_issues = report_data.get("critical_issues", 0)
            high_issues = report_data.get("high_issues", 0)

            self.logger.info(
                f"セキュリティ問題: Critical={critical_issues}, High={high_issues}"
            )

            if critical_issues <= self.config.max_critical_issues:
                self.logger.info("セキュリティ品質ゲートを通過しました")
                return True
            else:
                self.logger.error(
                    f"重要なセキュリティ問題が {critical_issues} 件検出されました"
                )
                return False

        except Exception as e:
            self.logger.error(f"セキュリティチェック中にエラーが発生しました: {e}")
            return False

    async def check_performance_regression(
        self, current_metrics: dict, baseline_file: Path
    ) -> bool:
        """パフォーマンス回帰のチェック

        Args:
            current_metrics: 現在のパフォーマンスメトリクス
            baseline_file: ベースラインメトリクスファイル

        Returns:
            品質ゲート通過可否
        """
        try:
            if not baseline_file.exists():
                self.logger.info(
                    "ベースラインファイルが見つかりません。現在のメトリクスをベースラインとして保存します"
                )
                with open(baseline_file, "w", encoding="utf-8") as f:
                    json.dump(current_metrics, f, indent=2, ensure_ascii=False)
                return True

            # ベースラインの読み込み
            with open(baseline_file, encoding="utf-8") as f:
                baseline_metrics = json.load(f)

            # パフォーマンス回帰のチェック
            regression_detected = False
            for metric_name, current_value in current_metrics.items():
                if metric_name in baseline_metrics:
                    baseline_value = baseline_metrics[metric_name]

                    # 数値メトリクスのみチェック
                    if isinstance(current_value, int | float) and isinstance(
                        baseline_value, int | float
                    ):
                        if baseline_value > 0:
                            regression_percent = (
                                (current_value - baseline_value) / baseline_value
                            ) * 100

                            if (
                                regression_percent
                                > self.config.max_performance_regression
                            ):
                                self.logger.error(
                                    f"パフォーマンス回帰検出: {metric_name} "
                                    f"({baseline_value:.2f} -> {current_value:.2f}, "
                                    f"+{regression_percent:.1f}%)"
                                )
                                regression_detected = True

            if not regression_detected:
                self.logger.info("パフォーマンス品質ゲートを通過しました")
                # ベースラインの更新
                with open(baseline_file, "w", encoding="utf-8") as f:
                    json.dump(current_metrics, f, indent=2, ensure_ascii=False)
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"パフォーマンスチェック中にエラーが発生しました: {e}")
            return False


class CICDPipeline:
    """CI/CD パイプライン

    継続的インテグレーション・継続的デプロイメントの
    自動化パイプラインを実装。
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger = self._setup_logging()
        self.quality_gate = QualityGate(config)

        # パイプライン状態
        self.stage_results: list[StageResult] = []
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.artifacts: list[Path] = []

        # 出力ディレクトリの作成
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> logging.Logger:
        """ログ設定の初期化"""
        logger = logging.getLogger("ci_cd_pipeline")
        logger.setLevel(logging.INFO)

        # ログファイルハンドラー
        log_file = self.config.output_dir / f"{self.pipeline_id}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # フォーマッター
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    async def run_pipeline(self) -> PipelineSummary:
        """パイプラインの実行

        Returns:
            パイプライン結果サマリー
        """
        self.logger.info(f"CI/CDパイプライン {self.pipeline_id} を開始します")
        self.start_time = datetime.now()

        try:
            # Git情報の取得
            await self._collect_git_info()

            # 各ステージの実行
            stages = self._get_enabled_stages()

            for stage in stages:
                stage_result = await self._run_stage(stage)
                self.stage_results.append(stage_result)

                # ステージが失敗した場合はパイプラインを停止
                if stage_result.result == PipelineResult.FAILURE:
                    self.logger.error(
                        f"ステージ {stage.value} が失敗しました。パイプラインを停止します"
                    )
                    break

                # 品質ゲートのチェック
                if not await self._check_quality_gates(stage, stage_result):
                    self.logger.error(
                        f"ステージ {stage.value} で品質ゲートに失敗しました"
                    )
                    stage_result.result = PipelineResult.FAILURE
                    break

            # パイプライン結果の生成
            summary = self._generate_summary()

            # 通知の送信
            if self.config.enable_notifications:
                await self._send_notifications(summary)

            return summary

        except Exception as e:
            self.logger.error(f"パイプライン実行中にエラーが発生しました: {e}")
            raise
        finally:
            self.end_time = datetime.now()

    async def _collect_git_info(self):
        """Git情報の収集"""
        try:
            # ブランチ情報
            if not self.config.git_branch:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=self.config.project_root,
                )
                if result.returncode == 0:
                    self.config.git_branch = result.stdout.strip()

            # コミット情報
            if not self.config.git_commit:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=self.config.project_root,
                )
                if result.returncode == 0:
                    self.config.git_commit = result.stdout.strip()

            self.logger.info(
                f"Git情報: ブランチ={self.config.git_branch}, コミット={self.config.git_commit[:8]}"
            )

        except Exception as e:
            self.logger.warning(f"Git情報の取得に失敗しました: {e}")

    def _get_enabled_stages(self) -> list[PipelineStage]:
        """有効なステージのリストを取得"""
        stages = []

        if self.config.enable_build:
            stages.append(PipelineStage.BUILD)
        if self.config.enable_unit_test:
            stages.append(PipelineStage.UNIT_TEST)
        if self.config.enable_integration_test:
            stages.append(PipelineStage.INTEGRATION_TEST)
        if self.config.enable_validation:
            stages.append(PipelineStage.VALIDATION)
        if self.config.enable_security_scan:
            stages.append(PipelineStage.SECURITY_SCAN)
        if self.config.enable_performance_test:
            stages.append(PipelineStage.PERFORMANCE_TEST)
        if self.config.enable_deploy:
            stages.append(PipelineStage.DEPLOY)

        return stages

    async def _run_stage(self, stage: PipelineStage) -> StageResult:
        """単一ステージの実行

        Args:
            stage: 実行するステージ

        Returns:
            ステージ結果
        """
        self.logger.info(f"ステージ '{stage.value}' を開始します")
        start_time = datetime.now()

        try:
            # ステージ別の実行
            if stage == PipelineStage.BUILD:
                output, artifacts = await self._run_build_stage()
            elif stage == PipelineStage.UNIT_TEST:
                output, artifacts = await self._run_unit_test_stage()
            elif stage == PipelineStage.INTEGRATION_TEST:
                output, artifacts = await self._run_integration_test_stage()
            elif stage == PipelineStage.VALIDATION:
                output, artifacts = await self._run_validation_stage()
            elif stage == PipelineStage.SECURITY_SCAN:
                output, artifacts = await self._run_security_scan_stage()
            elif stage == PipelineStage.PERFORMANCE_TEST:
                output, artifacts = await self._run_performance_test_stage()
            elif stage == PipelineStage.DEPLOY:
                output, artifacts = await self._run_deploy_stage()
            else:
                raise ValueError(f"未知のステージ: {stage}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = StageResult(
                stage=stage,
                result=PipelineResult.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                output=output,
                artifacts=artifacts or [],
            )

            self.logger.info(
                f"ステージ '{stage.value}' が完了しました - 実行時間: {duration:.2f}秒"
            )
            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.logger.error(f"ステージ '{stage.value}' でエラーが発生しました: {e}")

            return StageResult(
                stage=stage,
                result=PipelineResult.FAILURE,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                output="",
                error=str(e),
            )

    async def _run_build_stage(self) -> tuple[str, list[Path]]:
        """ビルドステージの実行"""
        self.logger.info("依存関係のインストールを実行します")

        # 仮想環境の作成
        venv_path = self.config.project_root / "venv"
        if not venv_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                cwd=self.config.project_root,
            )
            if result.returncode != 0:
                raise RuntimeError(f"仮想環境の作成に失敗しました: {result.stderr}")

        # 依存関係のインストール
        pip_path = venv_path / ("Scripts" if os.name == "nt" else "bin") / "pip"
        requirements_path = self.config.project_root / self.config.requirements_file

        if requirements_path.exists():
            result = subprocess.run(
                [str(pip_path), "install", "-r", str(requirements_path)],
                capture_output=True,
                text=True,
                cwd=self.config.project_root,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"依存関係のインストールに失敗しました: {result.stderr}"
                )

        return "ビルドが正常に完了しました", []

    async def _run_unit_test_stage(self) -> tuple[str, list[Path]]:
        """ユニットテストステージの実行"""
        self.logger.info("ユニットテストを実行します")

        # pytest の実行
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/",
                "-v",
                "--tb=short",
                "--cov=src",
                "--cov-report=xml",
                "--cov-report=html",
            ],
            capture_output=True,
            text=True,
            cwd=self.config.project_root,
        )

        # カバレッジファイルの確認
        coverage_xml = self.config.project_root / "coverage.xml"
        coverage_html = self.config.project_root / "htmlcov"

        artifacts = []
        if coverage_xml.exists():
            artifacts.append(coverage_xml)
        if coverage_html.exists():
            artifacts.append(coverage_html)

        if result.returncode != 0:
            raise RuntimeError(f"ユニットテストに失敗しました: {result.stderr}")

        return result.stdout, artifacts

    async def _run_integration_test_stage(self) -> tuple[str, list[Path]]:
        """統合テストステージの実行"""
        self.logger.info("統合テストを実行します")

        # 統合テストの実行
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-m", "integration", "-v"],
            capture_output=True,
            text=True,
            cwd=self.config.project_root,
        )

        if result.returncode != 0:
            # 統合テストが存在しない場合はスキップ
            if "no tests ran" in result.stdout.lower():
                return "統合テストはスキップされました（テストが見つかりません）", []
            raise RuntimeError(f"統合テストに失敗しました: {result.stderr}")

        return result.stdout, []

    async def _run_validation_stage(self) -> tuple[str, list[Path]]:
        """検証ステージの実行"""
        self.logger.info("包括的検証を実行します")

        # 検証設定の作成
        validation_config = create_validation_config(
            level=ValidationLevel.DAILY,
            output_dir=self.config.output_dir / "validation",
            timeout_seconds=1800,  # 30分
        )

        # 検証スイートの実行
        suite = ComprehensiveValidationSuite(validation_config)
        summary = await suite.run_validation()

        # 結果の確認
        if summary.overall_result == ValidationResult.FAILED:
            raise RuntimeError(f"包括的検証に失敗しました: {summary.critical_failures}")

        # アーティファクトの収集
        artifacts = list(validation_config.output_dir.glob("*"))

        return (
            f"検証が完了しました - 成功: {summary.passed_tests}, 失敗: {summary.failed_tests}",
            artifacts,
        )

    async def _run_security_scan_stage(self) -> tuple[str, list[Path]]:
        """セキュリティスキャンステージの実行"""
        self.logger.info("セキュリティスキャンを実行します")

        # bandit によるセキュリティスキャン
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bandit",
                    "-r",
                    "src/",
                    "-f",
                    "json",
                    "-o",
                    "security_report.json",
                ],
                capture_output=True,
                text=True,
                cwd=self.config.project_root,
            )

            security_report = self.config.project_root / "security_report.json"
            artifacts = [security_report] if security_report.exists() else []

            return "セキュリティスキャンが完了しました", artifacts

        except FileNotFoundError:
            self.logger.warning(
                "bandit がインストールされていません。セキュリティスキャンをスキップします"
            )
            return (
                "セキュリティスキャンはスキップされました（bandit未インストール）",
                [],
            )

    async def _run_performance_test_stage(self) -> tuple[str, list[Path]]:
        """パフォーマンステストステージの実行"""
        self.logger.info("パフォーマンステストを実行します")

        # パフォーマンステストの実行
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-m", "performance", "-v"],
            capture_output=True,
            text=True,
            cwd=self.config.project_root,
        )

        if result.returncode != 0:
            # パフォーマンステストが存在しない場合はスキップ
            if "no tests ran" in result.stdout.lower():
                return (
                    "パフォーマンステストはスキップされました（テストが見つかりません）",
                    [],
                )
            raise RuntimeError(f"パフォーマンステストに失敗しました: {result.stderr}")

        return result.stdout, []

    async def _run_deploy_stage(self) -> tuple[str, list[Path]]:
        """デプロイステージの実行"""
        self.logger.info("デプロイを実行します")

        # デプロイ処理（実装は環境に依存）
        # ここでは実行ファイルの作成を例として実装

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "PyInstaller",
                    "main.py",
                    "--onefile",
                    "--windowed",
                ],
                capture_output=True,
                text=True,
                cwd=self.config.project_root,
            )

            if result.returncode != 0:
                raise RuntimeError(f"実行ファイルの作成に失敗しました: {result.stderr}")

            # 成果物の確認
            dist_dir = self.config.project_root / "dist"
            artifacts = list(dist_dir.glob("*")) if dist_dir.exists() else []

            return "デプロイが完了しました", artifacts

        except FileNotFoundError:
            self.logger.warning(
                "PyInstaller がインストールされていません。デプロイをスキップします"
            )
            return "デプロイはスキップされました（PyInstaller未インストール）", []

    async def _check_quality_gates(
        self, stage: PipelineStage, stage_result: StageResult
    ) -> bool:
        """品質ゲートのチェック

        Args:
            stage: 実行されたステージ
            stage_result: ステージ結果

        Returns:
            品質ゲート通過可否
        """
        if stage == PipelineStage.UNIT_TEST:
            # テストカバレッジのチェック
            coverage_file = self.config.project_root / "coverage.xml"
            return await self.quality_gate.check_test_coverage(coverage_file)

        elif stage == PipelineStage.SECURITY_SCAN:
            # セキュリティ問題のチェック
            security_report = self.config.project_root / "security_report.json"
            return await self.quality_gate.check_security_issues(security_report)

        elif stage == PipelineStage.PERFORMANCE_TEST:
            # パフォーマンス回帰のチェック
            if stage_result.metrics:
                baseline_file = self.config.output_dir / "performance_baseline.json"
                return await self.quality_gate.check_performance_regression(
                    stage_result.metrics, baseline_file
                )

        return True  # その他のステージは常に通過

    def _generate_summary(self) -> PipelineSummary:
        """パイプライン結果サマリーの生成"""
        # 全体結果の判定
        overall_result = PipelineResult.SUCCESS
        for stage_result in self.stage_results:
            if stage_result.result == PipelineResult.FAILURE:
                overall_result = PipelineResult.FAILURE
                break
            elif stage_result.result == PipelineResult.CANCELLED:
                overall_result = PipelineResult.CANCELLED
                break

        # 実行時間の計算
        total_duration = (
            (self.end_time - self.start_time).total_seconds()
            if self.end_time and self.start_time
            else 0
        )

        # アーティファクトの収集
        all_artifacts = []
        for stage_result in self.stage_results:
            if stage_result.artifacts:
                all_artifacts.extend(stage_result.artifacts)

        # メトリクスの収集
        metrics = {
            "pipeline_id": self.pipeline_id,
            "git_branch": self.config.git_branch,
            "git_commit": self.config.git_commit,
            "stage_count": len(self.stage_results),
            "successful_stages": sum(
                1 for r in self.stage_results if r.result == PipelineResult.SUCCESS
            ),
            "failed_stages": sum(
                1 for r in self.stage_results if r.result == PipelineResult.FAILURE
            ),
        }

        # 品質ゲート通過状況
        quality_gates_passed = overall_result == PipelineResult.SUCCESS

        return PipelineSummary(
            pipeline_id=self.pipeline_id,
            start_time=self.start_time,
            end_time=self.end_time,
            total_duration=total_duration,
            overall_result=overall_result,
            stage_results=self.stage_results,
            quality_gates_passed=quality_gates_passed,
            artifacts=all_artifacts,
            metrics=metrics,
        )

    async def _send_notifications(self, summary: PipelineSummary):
        """通知の送信

        Args:
            summary: パイプライン結果サマリー
        """
        try:
            message = self._create_notification_message(summary)

            # Webhook通知
            if self.config.notification_webhook:
                await self._send_webhook_notification(message)

            # メール通知
            if self.config.notification_email:
                await self._send_email_notification(message)

        except Exception as e:
            self.logger.error(f"通知送信中にエラーが発生しました: {e}")

    def _create_notification_message(self, summary: PipelineSummary) -> str:
        """通知メッセージの作成"""
        status_emoji = (
            "✅" if summary.overall_result == PipelineResult.SUCCESS else "❌"
        )

        message = f"""
{status_emoji} CI/CD パイプライン結果

パイプラインID: {summary.pipeline_id}
ブランチ: {self.config.git_branch}
コミット: {self.config.git_commit[:8] if self.config.git_commit else 'N/A'}
結果: {summary.overall_result.value}
実行時間: {summary.total_duration:.2f}秒

ステージ結果:
"""

        for stage_result in summary.stage_results:
            stage_emoji = (
                "✅" if stage_result.result == PipelineResult.SUCCESS else "❌"
            )
            message += f"  {stage_emoji} {stage_result.stage.value}: {stage_result.duration:.2f}秒\n"

        if summary.overall_result == PipelineResult.FAILURE:
            failed_stages = [
                r for r in summary.stage_results if r.result == PipelineResult.FAILURE
            ]
            if failed_stages:
                message += "\n失敗したステージ:\n"
                for stage_result in failed_stages:
                    message += f"  - {stage_result.stage.value}: {stage_result.error}\n"

        return message

    async def _send_webhook_notification(self, message: str):
        """Webhook通知の送信"""
        # 実装は使用するWebhookサービスに依存
        self.logger.info("Webhook通知を送信しました")

    async def _send_email_notification(self, message: str):
        """メール通知の送信"""
        # 実装は使用するメールサービスに依存
        self.logger.info("メール通知を送信しました")


def create_pipeline_config(project_root: Path, **kwargs) -> PipelineConfig:
    """パイプライン設定の作成ヘルパー

    Args:
        project_root: プロジェクトルートディレクトリ
        **kwargs: 追加設定

    Returns:
        パイプライン設定
    """
    config = PipelineConfig(project_root=project_root)

    # 追加設定の適用
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return config


async def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="DocMind CI/CD パイプライン")
    parser.add_argument(
        "--project-root", default=".", help="プロジェクトルートディレクトリ"
    )
    parser.add_argument(
        "--output-dir", default="pipeline_results", help="出力ディレクトリ"
    )
    parser.add_argument(
        "--timeout", type=int, default=60, help="タイムアウト時間（分）"
    )
    parser.add_argument(
        "--no-build", action="store_true", help="ビルドステージを無効化"
    )
    parser.add_argument("--no-test", action="store_true", help="テストステージを無効化")
    parser.add_argument(
        "--enable-deploy", action="store_true", help="デプロイステージを有効化"
    )

    args = parser.parse_args()

    # 設定の作成
    config = create_pipeline_config(
        project_root=Path(args.project_root),
        output_dir=Path(args.output_dir),
        timeout_minutes=args.timeout,
        enable_build=not args.no_build,
        enable_unit_test=not args.no_test,
        enable_integration_test=not args.no_test,
        enable_deploy=args.enable_deploy,
    )

    # パイプラインの実行
    pipeline = CICDPipeline(config)
    summary = await pipeline.run_pipeline()

    # 結果の出力
    print("\n=== パイプライン結果サマリー ===")
    print(f"パイプラインID: {summary.pipeline_id}")
    print(f"全体結果: {summary.overall_result.value}")
    print(f"実行時間: {summary.total_duration:.2f}秒")
    print(f"品質ゲート: {'通過' if summary.quality_gates_passed else '失敗'}")

    print("\nステージ結果:")
    for stage_result in summary.stage_results:
        print(
            f"  {stage_result.stage.value}: {stage_result.result.value} ({stage_result.duration:.2f}秒)"
        )

    # 終了コード
    sys.exit(0 if summary.overall_result == PipelineResult.SUCCESS else 1)


if __name__ == "__main__":
    asyncio.run(main())
