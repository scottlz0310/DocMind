#!/usr/bin/env python3
"""
包括的検証スイート

DocMindアプリケーションの全機能を統合的に検証するメインスイート。
すべての検証コンポーネントを統合し、包括的な品質保証を実行します。
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# 検証コンポーネントのインポート
from .application_startup_validator import ApplicationStartupValidator
from .document_processing_validator import DocumentProcessingValidator
from .search_functionality_validator import SearchFunctionalityValidator
from .gui_functionality_validator import GUIFunctionalityValidator
from .data_persistence_validator import DataPersistenceValidator
from .error_handling_validator import ErrorHandlingValidator
from .performance_validator import PerformanceValidator
from .security_validator import SecurityValidator
from .end_to_end_workflow_validator import EndToEndWorkflowValidator
from .compatibility_validator import CompatibilityValidator
from .real_world_simulator import RealWorldSimulator
from .validation_report_generator import ValidationReportGenerator
from .statistics_collector import StatisticsCollector


class ValidationLevel(Enum):
    """検証レベルの定義"""
    COMMIT = "commit"      # コミット時の基本検証
    DAILY = "daily"        # 日次の包括検証
    WEEKLY = "weekly"      # 週次の詳細検証
    RELEASE = "release"    # リリース前の完全検証


class ValidationResult(Enum):
    """検証結果の定義"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationConfig:
    """検証設定"""
    level: ValidationLevel
    timeout_seconds: int = 3600  # 1時間のデフォルトタイムアウト
    parallel_execution: bool = True
    generate_report: bool = True
    fail_fast: bool = False
    output_dir: Path = Path("validation_results")
    
    # 各検証の有効/無効設定
    enable_startup: bool = True
    enable_document_processing: bool = True
    enable_search: bool = True
    enable_gui: bool = True
    enable_data_persistence: bool = True
    enable_error_handling: bool = True
    enable_performance: bool = True
    enable_security: bool = True
    enable_end_to_end: bool = True
    enable_compatibility: bool = True
    enable_real_world: bool = True


@dataclass
class ValidationSummary:
    """検証結果サマリー"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    warning_tests: int
    skipped_tests: int
    execution_time: float
    overall_result: ValidationResult
    critical_failures: List[str]
    performance_metrics: Dict[str, Any]


class ComprehensiveValidationSuite:
    """包括的検証スイート
    
    すべての検証コンポーネントを統合し、設定に基づいて
    適切な検証レベルで実行する統合スイート。
    """
    
    def __init__(self, config: ValidationConfig):
        """初期化
        
        Args:
            config: 検証設定
        """
        self.config = config
        self.logger = self._setup_logging()
        self.statistics = StatisticsCollector()
        self.report_generator = ValidationReportGenerator()
        
        # 検証結果の保存
        self.results: Dict[str, Dict] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # 検証コンポーネントの初期化
        self._initialize_validators()
    
    def _setup_logging(self) -> logging.Logger:
        """ログ設定の初期化"""
        logger = logging.getLogger("comprehensive_validation")
        logger.setLevel(logging.INFO)
        
        # ログファイルハンドラー
        log_file = self.config.output_dir / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
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
    
    def _initialize_validators(self):
        """検証コンポーネントの初期化"""
        self.validators = {}
        
        if self.config.enable_startup:
            self.validators['startup'] = ApplicationStartupValidator()
        
        if self.config.enable_document_processing:
            self.validators['document_processing'] = DocumentProcessingValidator()
        
        if self.config.enable_search:
            self.validators['search'] = SearchFunctionalityValidator()
        
        if self.config.enable_gui:
            self.validators['gui'] = GUIFunctionalityValidator()
        
        if self.config.enable_data_persistence:
            self.validators['data_persistence'] = DataPersistenceValidator()
        
        if self.config.enable_error_handling:
            self.validators['error_handling'] = ErrorHandlingValidator()
        
        if self.config.enable_performance:
            self.validators['performance'] = PerformanceValidator()
        
        if self.config.enable_security:
            self.validators['security'] = SecurityValidator()
        
        if self.config.enable_end_to_end:
            self.validators['end_to_end'] = EndToEndWorkflowValidator()
        
        if self.config.enable_compatibility:
            self.validators['compatibility'] = CompatibilityValidator()
        
        if self.config.enable_real_world:
            self.validators['real_world'] = RealWorldSimulator()
    
    async def run_validation(self) -> ValidationSummary:
        """包括的検証の実行
        
        Returns:
            検証結果サマリー
        """
        self.logger.info(f"包括的検証を開始します - レベル: {self.config.level.value}")
        self.start_time = datetime.now()
        
        try:
            # 検証レベルに応じた設定調整
            self._adjust_config_for_level()
            
            # 検証の実行
            if self.config.parallel_execution:
                await self._run_parallel_validation()
            else:
                await self._run_sequential_validation()
            
            # 結果の集計
            summary = self._generate_summary()
            
            # レポート生成
            if self.config.generate_report:
                await self._generate_reports(summary)
            
            self.logger.info(f"包括的検証が完了しました - 結果: {summary.overall_result.value}")
            return summary
            
        except Exception as e:
            self.logger.error(f"検証実行中にエラーが発生しました: {e}")
            raise
        finally:
            self.end_time = datetime.now()
    
    def _adjust_config_for_level(self):
        """検証レベルに応じた設定調整"""
        if self.config.level == ValidationLevel.COMMIT:
            # コミット時は基本的な検証のみ
            self.config.enable_gui = False
            self.config.enable_real_world = False
            self.config.timeout_seconds = 300  # 5分
            
        elif self.config.level == ValidationLevel.DAILY:
            # 日次は GUI を除く包括検証
            self.config.enable_gui = False
            self.config.timeout_seconds = 1800  # 30分
            
        elif self.config.level == ValidationLevel.WEEKLY:
            # 週次は GUI を含む詳細検証
            self.config.timeout_seconds = 3600  # 1時間
            
        elif self.config.level == ValidationLevel.RELEASE:
            # リリース前は完全検証
            self.config.timeout_seconds = 7200  # 2時間
            self.config.fail_fast = False
    
    async def _run_parallel_validation(self):
        """並列検証の実行"""
        self.logger.info("並列検証を開始します")
        
        # 検証タスクの作成
        tasks = []
        for name, validator in self.validators.items():
            task = asyncio.create_task(
                self._run_single_validator(name, validator),
                name=f"validation_{name}"
            )
            tasks.append(task)
        
        # 並列実行
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError:
            self.logger.error(f"検証がタイムアウトしました ({self.config.timeout_seconds}秒)")
            # 実行中のタスクをキャンセル
            for task in tasks:
                if not task.done():
                    task.cancel()
    
    async def _run_sequential_validation(self):
        """順次検証の実行"""
        self.logger.info("順次検証を開始します")
        
        for name, validator in self.validators.items():
            try:
                await self._run_single_validator(name, validator)
                
                # fail_fast が有効で失敗した場合は中断
                if (self.config.fail_fast and 
                    name in self.results and 
                    self.results[name].get('result') == ValidationResult.FAILED):
                    self.logger.error(f"検証 {name} が失敗したため、検証を中断します")
                    break
                    
            except Exception as e:
                self.logger.error(f"検証 {name} でエラーが発生しました: {e}")
                if self.config.fail_fast:
                    raise
    
    async def _run_single_validator(self, name: str, validator):
        """単一検証の実行
        
        Args:
            name: 検証名
            validator: 検証コンポーネント
        """
        self.logger.info(f"検証 '{name}' を開始します")
        start_time = time.time()
        
        try:
            # 検証の実行
            if hasattr(validator, 'run_validation'):
                result = await validator.run_validation()
            elif hasattr(validator, 'validate'):
                result = await validator.validate()
            else:
                # 同期メソッドの場合
                result = validator.run_all_validations()
            
            execution_time = time.time() - start_time
            
            # 結果の保存
            self.results[name] = {
                'result': ValidationResult.PASSED if result.get('success', False) else ValidationResult.FAILED,
                'execution_time': execution_time,
                'details': result,
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"検証 '{name}' が完了しました - 実行時間: {execution_time:.2f}秒")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"検証 '{name}' でエラーが発生しました: {e}")
            
            self.results[name] = {
                'result': ValidationResult.FAILED,
                'execution_time': execution_time,
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def _generate_summary(self) -> ValidationSummary:
        """検証結果サマリーの生成"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r['result'] == ValidationResult.PASSED)
        failed_tests = sum(1 for r in self.results.values() if r['result'] == ValidationResult.FAILED)
        warning_tests = sum(1 for r in self.results.values() if r['result'] == ValidationResult.WARNING)
        skipped_tests = sum(1 for r in self.results.values() if r['result'] == ValidationResult.SKIPPED)
        
        # 全体の実行時間
        execution_time = (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0
        
        # 全体結果の判定
        if failed_tests > 0:
            overall_result = ValidationResult.FAILED
        elif warning_tests > 0:
            overall_result = ValidationResult.WARNING
        else:
            overall_result = ValidationResult.PASSED
        
        # 重要な失敗の抽出
        critical_failures = []
        for name, result in self.results.items():
            if result['result'] == ValidationResult.FAILED:
                if 'error' in result:
                    critical_failures.append(f"{name}: {result['error']}")
                else:
                    critical_failures.append(f"{name}: 検証失敗")
        
        # パフォーマンスメトリクスの収集
        performance_metrics = {}
        for name, result in self.results.items():
            performance_metrics[f"{name}_execution_time"] = result['execution_time']
            if 'details' in result and isinstance(result['details'], dict):
                if 'performance' in result['details']:
                    performance_metrics[f"{name}_performance"] = result['details']['performance']
        
        return ValidationSummary(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            warning_tests=warning_tests,
            skipped_tests=skipped_tests,
            execution_time=execution_time,
            overall_result=overall_result,
            critical_failures=critical_failures,
            performance_metrics=performance_metrics
        )
    
    async def _generate_reports(self, summary: ValidationSummary):
        """検証レポートの生成"""
        self.logger.info("検証レポートを生成しています")
        
        try:
            # 統計情報の収集
            stats = {
                'validation_level': self.config.level.value,
                'timestamp': datetime.now().isoformat(),
                'summary': summary.__dict__,
                'detailed_results': self.results,
                'configuration': self.config.__dict__
            }
            
            # レポート生成
            report_data = {
                'summary': summary,
                'results': self.results,
                'statistics': stats
            }
            
            # HTML レポートの生成
            html_report = await self.report_generator.generate_html_report(
                report_data, 
                self.config.output_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            )
            
            # JSON レポートの生成
            json_report = await self.report_generator.generate_json_report(
                report_data,
                self.config.output_dir / f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            self.logger.info(f"レポートが生成されました: {html_report}, {json_report}")
            
        except Exception as e:
            self.logger.error(f"レポート生成中にエラーが発生しました: {e}")


def create_validation_config(level: ValidationLevel, **kwargs) -> ValidationConfig:
    """検証設定の作成ヘルパー
    
    Args:
        level: 検証レベル
        **kwargs: 追加設定
    
    Returns:
        検証設定
    """
    config = ValidationConfig(level=level)
    
    # 追加設定の適用
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return config


async def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DocMind 包括的検証スイート")
    parser.add_argument(
        "--level", 
        choices=[level.value for level in ValidationLevel],
        default=ValidationLevel.DAILY.value,
        help="検証レベル"
    )
    parser.add_argument("--output-dir", default="validation_results", help="出力ディレクトリ")
    parser.add_argument("--timeout", type=int, default=3600, help="タイムアウト時間（秒）")
    parser.add_argument("--no-parallel", action="store_true", help="並列実行を無効化")
    parser.add_argument("--fail-fast", action="store_true", help="最初の失敗で中断")
    parser.add_argument("--no-report", action="store_true", help="レポート生成を無効化")
    
    args = parser.parse_args()
    
    # 設定の作成
    config = create_validation_config(
        level=ValidationLevel(args.level),
        output_dir=Path(args.output_dir),
        timeout_seconds=args.timeout,
        parallel_execution=not args.no_parallel,
        fail_fast=args.fail_fast,
        generate_report=not args.no_report
    )
    
    # 検証スイートの実行
    suite = ComprehensiveValidationSuite(config)
    summary = await suite.run_validation()
    
    # 結果の出力
    print(f"\n=== 検証結果サマリー ===")
    print(f"総テスト数: {summary.total_tests}")
    print(f"成功: {summary.passed_tests}")
    print(f"失敗: {summary.failed_tests}")
    print(f"警告: {summary.warning_tests}")
    print(f"スキップ: {summary.skipped_tests}")
    print(f"実行時間: {summary.execution_time:.2f}秒")
    print(f"全体結果: {summary.overall_result.value}")
    
    if summary.critical_failures:
        print(f"\n重要な失敗:")
        for failure in summary.critical_failures:
            print(f"  - {failure}")
    
    # 終了コード
    sys.exit(0 if summary.overall_result != ValidationResult.FAILED else 1)


if __name__ == "__main__":
    asyncio.run(main())