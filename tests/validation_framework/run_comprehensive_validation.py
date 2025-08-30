#!/usr/bin/env python3
"""
包括的検証統合実行スクリプト

すべての検証コンポーネントを統合して実行するメインスクリプト。
CI/CD環境での使用を想定した統合実行機能を提供。
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .ci_cd_pipeline import (
    CICDPipeline,
    PipelineResult,
    create_pipeline_config,
)
from .comprehensive_validation_suite import (
    ComprehensiveValidationSuite,
    ValidationLevel,
    ValidationResult,
    create_validation_config,
)
from .quality_gate_manager import (
    QualityGateManager,
    QualityGateResult,
    create_default_actions,
    create_default_quality_gates,
)
from .validation_scheduler import (
    ScheduleType,
    ValidationScheduler,
    create_default_schedules,
)


class ComprehensiveValidationRunner:
    """包括的検証実行器

    すべての検証コンポーネントを統合して実行し、
    統一された結果レポートを生成する。
    """

    def __init__(self, project_root: Path, output_dir: Path):
        self.project_root = project_root
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger = self._setup_logging()

        # 実行結果
        self.validation_result: ValidationResult | None = None
        self.pipeline_result: PipelineResult | None = None
        self.quality_gate_result: QualityGateResult | None = None

        # 実行時間
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

        # アーティファクト
        self.artifacts: list[Path] = []

    def _setup_logging(self) -> logging.Logger:
        """ログ設定の初期化"""
        logger = logging.getLogger("comprehensive_validation_runner")
        logger.setLevel(logging.INFO)

        # ログファイルハンドラー
        log_file = self.output_dir / f"comprehensive_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # フォーマッター
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    async def run_full_validation(
        self,
        validation_level: ValidationLevel = ValidationLevel.DAILY,
        enable_pipeline: bool = True,
        enable_quality_gates: bool = True,
        timeout_minutes: int = 120
    ) -> dict[str, Any]:
        """完全な検証の実行

        Args:
            validation_level: 検証レベル
            enable_pipeline: CI/CDパイプラインの有効化
            enable_quality_gates: 品質ゲートの有効化
            timeout_minutes: タイムアウト時間（分）

        Returns:
            統合結果
        """
        self.logger.info("包括的検証を開始します")
        self.start_time = datetime.now()

        try:
            # 1. 包括的検証スイートの実行
            await self._run_validation_suite(validation_level)

            # 2. CI/CDパイプラインの実行
            if enable_pipeline:
                await self._run_ci_cd_pipeline(timeout_minutes)

            # 3. 品質ゲートの実行
            if enable_quality_gates:
                await self._run_quality_gates()

            # 4. 統合結果の生成
            result = await self._generate_integrated_result()

            self.logger.info("包括的検証が完了しました")
            return result

        except Exception as e:
            self.logger.error(f"包括的検証中にエラーが発生しました: {e}")
            raise
        finally:
            self.end_time = datetime.now()

    async def _run_validation_suite(self, validation_level: ValidationLevel):
        """検証スイートの実行"""
        self.logger.info("検証スイートを実行しています")

        try:
            # 検証設定の作成
            validation_config = create_validation_config(
                level=validation_level,
                output_dir=self.output_dir / "validation_suite",
                timeout_seconds=3600  # 1時間
            )

            # 検証スイートの実行
            suite = ComprehensiveValidationSuite(validation_config)
            summary = await suite.run_validation()

            self.validation_result = summary.overall_result
            self.artifacts.extend(list(validation_config.output_dir.glob("*")))

            self.logger.info(f"検証スイート完了: {summary.overall_result.value}")

        except Exception as e:
            self.logger.error(f"検証スイート実行中にエラーが発生しました: {e}")
            self.validation_result = ValidationResult.FAILED
            raise

    async def _run_ci_cd_pipeline(self, timeout_minutes: int):
        """CI/CDパイプラインの実行"""
        self.logger.info("CI/CDパイプラインを実行しています")

        try:
            # パイプライン設定の作成
            pipeline_config = create_pipeline_config(
                project_root=self.project_root,
                output_dir=self.output_dir / "ci_cd_pipeline",
                timeout_minutes=timeout_minutes
            )

            # パイプラインの実行
            pipeline = CICDPipeline(pipeline_config)
            summary = await pipeline.run_pipeline()

            self.pipeline_result = summary.overall_result
            self.artifacts.extend(summary.artifacts)

            self.logger.info(f"CI/CDパイプライン完了: {summary.overall_result.value}")

        except Exception as e:
            self.logger.error(f"CI/CDパイプライン実行中にエラーが発生しました: {e}")
            self.pipeline_result = PipelineResult.FAILURE
            raise

    async def _run_quality_gates(self):
        """品質ゲートの実行"""
        self.logger.info("品質ゲートを実行しています")

        try:
            # 品質ゲート管理システムの初期化
            quality_manager = QualityGateManager(self.output_dir / "quality_gates")

            # デフォルト品質ゲートの追加
            for gate in create_default_quality_gates():
                quality_manager.add_gate(gate)

            # デフォルト自動対応アクションの追加
            for action in create_default_actions():
                quality_manager.add_action(action)

            # 品質ゲートデータの準備
            gate_data = await self._prepare_quality_gate_data()

            # 品質ゲートの実行
            await quality_manager.check_all_gates(gate_data)

            self.quality_gate_result = quality_manager.get_overall_result()
            self.artifacts.extend(list(quality_manager.output_dir.glob("*")))

            self.logger.info(f"品質ゲート完了: {self.quality_gate_result.value}")

        except Exception as e:
            self.logger.error(f"品質ゲート実行中にエラーが発生しました: {e}")
            self.quality_gate_result = QualityGateResult.FAILED
            raise

    async def _prepare_quality_gate_data(self) -> dict[str, Any]:
        """品質ゲートデータの準備"""
        gate_data = {}

        # カバレッジファイルの検索
        coverage_files = list(self.project_root.glob("coverage.xml"))
        if coverage_files:
            gate_data['coverage_file'] = str(coverage_files[0])

        # セキュリティレポートの検索
        security_files = list(self.project_root.glob("security_report.json"))
        if security_files:
            gate_data['security_report'] = str(security_files[0])

        # パフォーマンスメトリクスの検索
        performance_files = list(self.output_dir.glob("**/performance_*.json"))
        if performance_files:
            try:
                with open(performance_files[0], encoding='utf-8') as f:
                    gate_data['current_metrics'] = json.load(f)

                gate_data['baseline_file'] = str(self.output_dir / "performance_baseline.json")
            except Exception as e:
                self.logger.warning(f"パフォーマンスメトリクスの読み込みに失敗しました: {e}")

        return gate_data

    async def _generate_integrated_result(self) -> dict[str, Any]:
        """統合結果の生成"""
        # 全体結果の判定
        overall_success = True

        if self.validation_result == ValidationResult.FAILED:
            overall_success = False

        if self.pipeline_result == PipelineResult.FAILURE:
            overall_success = False

        if self.quality_gate_result == QualityGateResult.FAILED:
            overall_success = False

        # 実行時間の計算
        execution_time = 0.0
        if self.start_time and self.end_time:
            execution_time = (self.end_time - self.start_time).total_seconds()

        # 統合結果の作成
        result = {
            'overall_success': overall_success,
            'execution_time': execution_time,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'results': {
                'validation_suite': self.validation_result.value if self.validation_result else None,
                'ci_cd_pipeline': self.pipeline_result.value if self.pipeline_result else None,
                'quality_gates': self.quality_gate_result.value if self.quality_gate_result else None
            },
            'artifacts': [str(p) for p in self.artifacts],
            'summary': self._create_summary()
        }

        # 結果の保存
        await self._save_integrated_result(result)

        return result

    def _create_summary(self) -> str:
        """サマリーの作成"""
        summary_parts = []

        if self.validation_result:
            summary_parts.append(f"検証スイート: {self.validation_result.value}")

        if self.pipeline_result:
            summary_parts.append(f"CI/CDパイプライン: {self.pipeline_result.value}")

        if self.quality_gate_result:
            summary_parts.append(f"品質ゲート: {self.quality_gate_result.value}")

        return " | ".join(summary_parts)

    async def _save_integrated_result(self, result: dict[str, Any]):
        """統合結果の保存"""
        try:
            result_file = self.output_dir / f"integrated_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            self.logger.info(f"統合結果を保存しました: {result_file}")

        except Exception as e:
            self.logger.error(f"統合結果保存中にエラーが発生しました: {e}")


async def run_validation_level(level: ValidationLevel, project_root: Path, output_dir: Path) -> bool:
    """指定されたレベルの検証を実行

    Args:
        level: 検証レベル
        project_root: プロジェクトルート
        output_dir: 出力ディレクトリ

    Returns:
        成功可否
    """
    runner = ComprehensiveValidationRunner(project_root, output_dir)

    try:
        result = await runner.run_full_validation(
            validation_level=level,
            enable_pipeline=True,
            enable_quality_gates=True,
            timeout_minutes=120
        )

        return result['overall_success']

    except Exception as e:
        logging.error(f"検証実行中にエラーが発生しました: {e}")
        return False


async def run_scheduler_mode(project_root: Path, output_dir: Path):
    """スケジューラーモードの実行"""
    scheduler = ValidationScheduler(project_root, output_dir / "scheduler")

    # デフォルトスケジュールの追加
    for schedule_config in create_default_schedules():
        scheduler.add_schedule(schedule_config)

    print("検証スケジューラーを開始します...")
    await scheduler.start_scheduler()

    try:
        # 無限ループで実行継続
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\n検証スケジューラーを停止しています...")
        await scheduler.stop_scheduler()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="DocMind 包括的検証統合実行システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # コミット時検証の実行
  python run_comprehensive_validation.py --level commit

  # 日次検証の実行
  python run_comprehensive_validation.py --level daily

  # 週次検証の実行
  python run_comprehensive_validation.py --level weekly

  # リリース前検証の実行
  python run_comprehensive_validation.py --level release

  # スケジューラーモードで実行
  python run_comprehensive_validation.py --scheduler

  # 特定のスケジュールを即座に実行
  python run_comprehensive_validation.py --execute daily
        """
    )

    # 基本オプション
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="プロジェクトルートディレクトリ (デフォルト: 現在のディレクトリ)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("comprehensive_validation_results"),
        help="出力ディレクトリ (デフォルト: comprehensive_validation_results)"
    )

    # 実行モード
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--level",
        choices=[level.value for level in ValidationLevel],
        help="検証レベルを指定して実行"
    )
    mode_group.add_argument(
        "--scheduler",
        action="store_true",
        help="スケジューラーモードで実行"
    )
    mode_group.add_argument(
        "--execute",
        choices=[schedule.value for schedule in ScheduleType],
        help="指定されたスケジュールを即座に実行"
    )

    # 詳細オプション
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="タイムアウト時間（分） (デフォルト: 120)"
    )
    parser.add_argument(
        "--no-pipeline",
        action="store_true",
        help="CI/CDパイプラインを無効化"
    )
    parser.add_argument(
        "--no-quality-gates",
        action="store_true",
        help="品質ゲートを無効化"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細ログを出力"
    )

    args = parser.parse_args()

    # ログレベルの設定
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # 出力ディレクトリの作成
    args.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_async():
        if args.level:
            # 検証レベル指定実行
            level = ValidationLevel(args.level)
            runner = ComprehensiveValidationRunner(args.project_root, args.output_dir)

            result = await runner.run_full_validation(
                validation_level=level,
                enable_pipeline=not args.no_pipeline,
                enable_quality_gates=not args.no_quality_gates,
                timeout_minutes=args.timeout
            )

            # 結果の出力
            print("\n=== 包括的検証結果 ===")
            print(f"全体結果: {'成功' if result['overall_success'] else '失敗'}")
            print(f"実行時間: {result['execution_time']:.2f}秒")
            print(f"サマリー: {result['summary']}")

            if result['results']['validation_suite']:
                print(f"検証スイート: {result['results']['validation_suite']}")

            if result['results']['ci_cd_pipeline']:
                print(f"CI/CDパイプライン: {result['results']['ci_cd_pipeline']}")

            if result['results']['quality_gates']:
                print(f"品質ゲート: {result['results']['quality_gates']}")

            print(f"\nアーティファクト数: {len(result['artifacts'])}")
            print(f"出力ディレクトリ: {args.output_dir}")

            # 終了コード
            sys.exit(0 if result['overall_success'] else 1)

        elif args.scheduler:
            # スケジューラーモード
            await run_scheduler_mode(args.project_root, args.output_dir)

        elif args.execute:
            # 指定スケジュール実行
            schedule_type = ScheduleType(args.execute)
            scheduler = ValidationScheduler(args.project_root, args.output_dir / "scheduler")

            # デフォルトスケジュールの追加
            for schedule_config in create_default_schedules():
                scheduler.add_schedule(schedule_config)

            execution = await scheduler.execute_validation(schedule_type, "manual")

            if execution:
                print(f"実行完了: {execution.execution_id}")
                print(f"状態: {execution.status.value}")
                if execution.error_message:
                    print(f"エラー: {execution.error_message}")
                    sys.exit(1)
                else:
                    sys.exit(0)
            else:
                print("実行条件を満たさないため、実行されませんでした")
                sys.exit(1)

    # 非同期実行
    try:
        asyncio.run(run_async())
    except KeyboardInterrupt:
        print("\n実行が中断されました")
        sys.exit(130)
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
