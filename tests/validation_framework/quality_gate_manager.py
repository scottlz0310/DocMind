#!/usr/bin/env python3
"""
品質ゲート管理システム

品質基準の定義、チェック、不合格時の自動対応機能を提供する。
"""

import asyncio
import json
import logging
import smtplib
import subprocess
import time
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

import requests


class QualityGateType(Enum):
    """品質ゲートタイプ"""
    TEST_COVERAGE = "test_coverage"
    SECURITY_ISSUES = "security_issues"
    PERFORMANCE_REGRESSION = "performance_regression"
    CODE_QUALITY = "code_quality"
    DEPENDENCY_VULNERABILITIES = "dependency_vulnerabilities"
    DOCUMENTATION_COVERAGE = "documentation_coverage"


class QualityGateResult(Enum):
    """品質ゲート結果"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    BLOCKED = "blocked"


class ActionType(Enum):
    """自動対応アクションタイプ"""
    NOTIFICATION = "notification"
    ROLLBACK = "rollback"
    BLOCK_DEPLOYMENT = "block_deployment"
    CREATE_ISSUE = "create_issue"
    SEND_EMAIL = "send_email"
    WEBHOOK = "webhook"
    CUSTOM_SCRIPT = "custom_script"


@dataclass
class QualityThreshold:
    """品質閾値"""
    name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    target_value: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    unit: str = ""
    description: str = ""


@dataclass
class QualityGateConfig:
    """品質ゲート設定"""
    gate_type: QualityGateType
    enabled: bool = True
    thresholds: List[QualityThreshold] = None
    blocking: bool = True  # ゲート失敗時にパイプラインをブロックするか
    warning_only: bool = False  # 警告のみで継続するか
    timeout_seconds: int = 300
    retry_count: int = 3
    retry_delay: int = 30


@dataclass
class AutoActionConfig:
    """自動対応アクション設定"""
    action_type: ActionType
    enabled: bool = True
    trigger_conditions: List[QualityGateResult] = None  # トリガー条件
    parameters: Dict[str, Any] = None
    timeout_seconds: int = 60
    retry_count: int = 1


@dataclass
class QualityGateCheckResult:
    """品質ゲートチェック結果"""
    gate_type: QualityGateType
    result: QualityGateResult
    score: Optional[float] = None
    threshold_name: Optional[str] = None
    actual_value: Optional[float] = None
    expected_value: Optional[float] = None
    message: str = ""
    details: Dict[str, Any] = None
    timestamp: datetime = None
    execution_time: float = 0.0


class QualityGateChecker(ABC):
    """品質ゲートチェッカーの基底クラス"""
    
    def __init__(self, config: QualityGateConfig):
        self.config = config
        self.logger = logging.getLogger(f"quality_gate_{config.gate_type.value}")
    
    @abstractmethod
    async def check(self, data: Dict[str, Any]) -> QualityGateCheckResult:
        """品質ゲートのチェックを実行
        
        Args:
            data: チェック対象データ
            
        Returns:
            チェック結果
        """
        pass
    
    def _create_result(self, result: QualityGateResult, **kwargs) -> QualityGateCheckResult:
        """結果オブジェクトの作成ヘルパー"""
        return QualityGateCheckResult(
            gate_type=self.config.gate_type,
            result=result,
            timestamp=datetime.now(),
            **kwargs
        )


class TestCoverageGate(QualityGateChecker):
    """テストカバレッジ品質ゲート"""
    
    async def check(self, data: Dict[str, Any]) -> QualityGateCheckResult:
        """テストカバレッジのチェック"""
        start_time = time.time()
        
        try:
            coverage_file = data.get('coverage_file')
            if not coverage_file or not Path(coverage_file).exists():
                return self._create_result(
                    QualityGateResult.FAILED,
                    message="カバレッジファイルが見つかりません",
                    execution_time=time.time() - start_time
                )
            
            # カバレッジ情報の解析
            coverage_data = await self._parse_coverage_file(coverage_file)
            line_coverage = coverage_data.get('line_coverage', 0.0)
            branch_coverage = coverage_data.get('branch_coverage', 0.0)
            
            # 閾値チェック
            for threshold in self.config.thresholds:
                if threshold.name == "line_coverage":
                    if line_coverage < threshold.min_value:
                        return self._create_result(
                            QualityGateResult.FAILED,
                            threshold_name=threshold.name,
                            actual_value=line_coverage,
                            expected_value=threshold.min_value,
                            message=f"ラインカバレッジが基準値を下回りました: {line_coverage:.1f}% < {threshold.min_value:.1f}%",
                            execution_time=time.time() - start_time
                        )
                    elif threshold.warning_threshold and line_coverage < threshold.warning_threshold:
                        return self._create_result(
                            QualityGateResult.WARNING,
                            threshold_name=threshold.name,
                            actual_value=line_coverage,
                            expected_value=threshold.warning_threshold,
                            message=f"ラインカバレッジが警告レベルです: {line_coverage:.1f}%",
                            execution_time=time.time() - start_time
                        )
            
            return self._create_result(
                QualityGateResult.PASSED,
                actual_value=line_coverage,
                message=f"テストカバレッジチェック通過: {line_coverage:.1f}%",
                details={'line_coverage': line_coverage, 'branch_coverage': branch_coverage},
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return self._create_result(
                QualityGateResult.FAILED,
                message=f"カバレッジチェック中にエラーが発生しました: {e}",
                execution_time=time.time() - start_time
            )
    
    async def _parse_coverage_file(self, coverage_file: str) -> Dict[str, float]:
        """カバレッジファイルの解析"""
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        coverage_element = root.find('.//coverage')
        if coverage_element is not None:
            line_rate = float(coverage_element.get('line-rate', 0)) * 100
            branch_rate = float(coverage_element.get('branch-rate', 0)) * 100
            
            return {
                'line_coverage': line_rate,
                'branch_coverage': branch_rate
            }
        
        return {'line_coverage': 0.0, 'branch_coverage': 0.0}


class SecurityIssuesGate(QualityGateChecker):
    """セキュリティ問題品質ゲート"""
    
    async def check(self, data: Dict[str, Any]) -> QualityGateCheckResult:
        """セキュリティ問題のチェック"""
        start_time = time.time()
        
        try:
            security_report = data.get('security_report')
            if not security_report or not Path(security_report).exists():
                return self._create_result(
                    QualityGateResult.PASSED,
                    message="セキュリティレポートが見つかりません（問題なしと判定）",
                    execution_time=time.time() - start_time
                )
            
            # セキュリティレポートの解析
            security_data = await self._parse_security_report(security_report)
            critical_issues = security_data.get('critical_issues', 0)
            high_issues = security_data.get('high_issues', 0)
            medium_issues = security_data.get('medium_issues', 0)
            
            # 閾値チェック
            for threshold in self.config.thresholds:
                if threshold.name == "critical_issues":
                    if critical_issues > threshold.max_value:
                        return self._create_result(
                            QualityGateResult.FAILED,
                            threshold_name=threshold.name,
                            actual_value=critical_issues,
                            expected_value=threshold.max_value,
                            message=f"重要なセキュリティ問題が検出されました: {critical_issues}件",
                            execution_time=time.time() - start_time
                        )
                elif threshold.name == "high_issues":
                    if high_issues > threshold.max_value:
                        return self._create_result(
                            QualityGateResult.WARNING,
                            threshold_name=threshold.name,
                            actual_value=high_issues,
                            expected_value=threshold.max_value,
                            message=f"高レベルのセキュリティ問題が検出されました: {high_issues}件",
                            execution_time=time.time() - start_time
                        )
            
            return self._create_result(
                QualityGateResult.PASSED,
                message=f"セキュリティチェック通過: Critical={critical_issues}, High={high_issues}",
                details={'critical_issues': critical_issues, 'high_issues': high_issues, 'medium_issues': medium_issues},
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return self._create_result(
                QualityGateResult.FAILED,
                message=f"セキュリティチェック中にエラーが発生しました: {e}",
                execution_time=time.time() - start_time
            )
    
    async def _parse_security_report(self, security_report: str) -> Dict[str, int]:
        """セキュリティレポートの解析"""
        with open(security_report, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # bandit レポート形式を想定
        if 'results' in report_data:
            issues_by_severity = {}
            for result in report_data['results']:
                severity = result.get('issue_severity', 'UNDEFINED').lower()
                issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1
            
            return {
                'critical_issues': issues_by_severity.get('high', 0),  # bandit では HIGH が最高レベル
                'high_issues': issues_by_severity.get('medium', 0),
                'medium_issues': issues_by_severity.get('low', 0)
            }
        
        return {'critical_issues': 0, 'high_issues': 0, 'medium_issues': 0}


class PerformanceRegressionGate(QualityGateChecker):
    """パフォーマンス回帰品質ゲート"""
    
    async def check(self, data: Dict[str, Any]) -> QualityGateCheckResult:
        """パフォーマンス回帰のチェック"""
        start_time = time.time()
        
        try:
            current_metrics = data.get('current_metrics', {})
            baseline_file = data.get('baseline_file')
            
            if not baseline_file or not Path(baseline_file).exists():
                # ベースラインファイルが存在しない場合は作成
                await self._create_baseline(current_metrics, baseline_file)
                return self._create_result(
                    QualityGateResult.PASSED,
                    message="ベースラインファイルを作成しました",
                    execution_time=time.time() - start_time
                )
            
            # ベースラインとの比較
            baseline_metrics = await self._load_baseline(baseline_file)
            regression_results = await self._check_regression(current_metrics, baseline_metrics)
            
            # 回帰チェック
            max_regression = 0.0
            regression_details = []
            
            for metric_name, regression_percent in regression_results.items():
                if regression_percent > max_regression:
                    max_regression = regression_percent
                
                # 閾値チェック
                for threshold in self.config.thresholds:
                    if threshold.name == "max_regression_percent":
                        if regression_percent > threshold.max_value:
                            regression_details.append(f"{metric_name}: +{regression_percent:.1f}%")
            
            if regression_details:
                return self._create_result(
                    QualityGateResult.FAILED,
                    actual_value=max_regression,
                    message=f"パフォーマンス回帰が検出されました: {', '.join(regression_details)}",
                    details=regression_results,
                    execution_time=time.time() - start_time
                )
            
            # ベースラインの更新
            await self._update_baseline(current_metrics, baseline_file)
            
            return self._create_result(
                QualityGateResult.PASSED,
                message="パフォーマンス回帰チェック通過",
                details=regression_results,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return self._create_result(
                QualityGateResult.FAILED,
                message=f"パフォーマンス回帰チェック中にエラーが発生しました: {e}",
                execution_time=time.time() - start_time
            )
    
    async def _create_baseline(self, metrics: Dict[str, Any], baseline_file: str):
        """ベースラインファイルの作成"""
        Path(baseline_file).parent.mkdir(parents=True, exist_ok=True)
        with open(baseline_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    async def _load_baseline(self, baseline_file: str) -> Dict[str, Any]:
        """ベースラインファイルの読み込み"""
        with open(baseline_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    async def _check_regression(self, current: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, float]:
        """回帰チェック"""
        regression_results = {}
        
        for metric_name, current_value in current.items():
            if metric_name in baseline:
                baseline_value = baseline[metric_name]
                
                if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
                    if baseline_value > 0:
                        regression_percent = ((current_value - baseline_value) / baseline_value) * 100
                        regression_results[metric_name] = regression_percent
        
        return regression_results
    
    async def _update_baseline(self, metrics: Dict[str, Any], baseline_file: str):
        """ベースラインファイルの更新"""
        with open(baseline_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)


class AutoActionExecutor:
    """自動対応アクション実行器"""
    
    def __init__(self, config: AutoActionConfig):
        self.config = config
        self.logger = logging.getLogger(f"auto_action_{config.action_type.value}")
    
    async def execute(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> bool:
        """自動対応アクションの実行
        
        Args:
            gate_result: 品質ゲート結果
            context: 実行コンテキスト
            
        Returns:
            実行成功可否
        """
        if not self.config.enabled:
            return True
        
        # トリガー条件のチェック
        if (self.config.trigger_conditions and 
            gate_result.result not in self.config.trigger_conditions):
            return True
        
        try:
            if self.config.action_type == ActionType.NOTIFICATION:
                return await self._send_notification(gate_result, context)
            elif self.config.action_type == ActionType.ROLLBACK:
                return await self._execute_rollback(gate_result, context)
            elif self.config.action_type == ActionType.BLOCK_DEPLOYMENT:
                return await self._block_deployment(gate_result, context)
            elif self.config.action_type == ActionType.CREATE_ISSUE:
                return await self._create_issue(gate_result, context)
            elif self.config.action_type == ActionType.SEND_EMAIL:
                return await self._send_email(gate_result, context)
            elif self.config.action_type == ActionType.WEBHOOK:
                return await self._send_webhook(gate_result, context)
            elif self.config.action_type == ActionType.CUSTOM_SCRIPT:
                return await self._execute_custom_script(gate_result, context)
            else:
                self.logger.warning(f"未知のアクションタイプ: {self.config.action_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"アクション実行中にエラーが発生しました: {e}")
            return False
    
    async def _send_notification(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> bool:
        """通知の送信"""
        message = self._create_notification_message(gate_result, context)
        self.logger.info(f"通知: {message}")
        return True
    
    async def _execute_rollback(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> bool:
        """ロールバックの実行"""
        rollback_command = self.config.parameters.get('rollback_command')
        if not rollback_command:
            self.logger.error("ロールバックコマンドが設定されていません")
            return False
        
        try:
            result = subprocess.run(
                rollback_command.split(),
                capture_output=True, text=True,
                timeout=self.config.timeout_seconds
            )
            
            if result.returncode == 0:
                self.logger.info("ロールバックが正常に実行されました")
                return True
            else:
                self.logger.error(f"ロールバックに失敗しました: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("ロールバックがタイムアウトしました")
            return False
    
    async def _block_deployment(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> bool:
        """デプロイメントのブロック"""
        block_file = self.config.parameters.get('block_file', '.deployment_blocked')
        
        try:
            with open(block_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'blocked_at': datetime.now().isoformat(),
                    'reason': gate_result.message,
                    'gate_type': gate_result.gate_type.value
                }, indent=2, ensure_ascii=False))
            
            self.logger.info(f"デプロイメントをブロックしました: {block_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"デプロイメントブロックに失敗しました: {e}")
            return False
    
    async def _create_issue(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> bool:
        """課題の作成"""
        # GitHub Issues API を使用した例
        github_token = self.config.parameters.get('github_token')
        repository = self.config.parameters.get('repository')
        
        if not github_token or not repository:
            self.logger.error("GitHub設定が不完全です")
            return False
        
        try:
            issue_data = {
                'title': f"品質ゲート失敗: {gate_result.gate_type.value}",
                'body': self._create_issue_body(gate_result, context),
                'labels': ['quality-gate', 'automated']
            }
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.post(
                f'https://api.github.com/repos/{repository}/issues',
                json=issue_data,
                headers=headers,
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code == 201:
                issue_url = response.json().get('html_url')
                self.logger.info(f"課題を作成しました: {issue_url}")
                return True
            else:
                self.logger.error(f"課題作成に失敗しました: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"課題作成中にエラーが発生しました: {e}")
            return False
    
    async def _send_email(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> bool:
        """メール送信"""
        smtp_server = self.config.parameters.get('smtp_server')
        smtp_port = self.config.parameters.get('smtp_port', 587)
        username = self.config.parameters.get('username')
        password = self.config.parameters.get('password')
        to_addresses = self.config.parameters.get('to_addresses', [])
        
        if not all([smtp_server, username, password, to_addresses]):
            self.logger.error("メール設定が不完全です")
            return False
        
        try:
            msg = MimeMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = f"品質ゲート失敗通知: {gate_result.gate_type.value}"
            
            body = self._create_notification_message(gate_result, context)
            msg.attach(MimeText(body, 'plain', 'utf-8'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            self.logger.info("メール通知を送信しました")
            return True
            
        except Exception as e:
            self.logger.error(f"メール送信中にエラーが発生しました: {e}")
            return False
    
    async def _send_webhook(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> bool:
        """Webhook送信"""
        webhook_url = self.config.parameters.get('webhook_url')
        if not webhook_url:
            self.logger.error("Webhook URLが設定されていません")
            return False
        
        try:
            payload = {
                'gate_type': gate_result.gate_type.value,
                'result': gate_result.result.value,
                'message': gate_result.message,
                'timestamp': gate_result.timestamp.isoformat(),
                'context': context
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code == 200:
                self.logger.info("Webhook通知を送信しました")
                return True
            else:
                self.logger.error(f"Webhook送信に失敗しました: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Webhook送信中にエラーが発生しました: {e}")
            return False
    
    async def _execute_custom_script(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> bool:
        """カスタムスクリプトの実行"""
        script_path = self.config.parameters.get('script_path')
        if not script_path or not Path(script_path).exists():
            self.logger.error("カスタムスクリプトが見つかりません")
            return False
        
        try:
            # 環境変数として情報を渡す
            env = {
                'GATE_TYPE': gate_result.gate_type.value,
                'GATE_RESULT': gate_result.result.value,
                'GATE_MESSAGE': gate_result.message,
                'GATE_TIMESTAMP': gate_result.timestamp.isoformat()
            }
            
            result = subprocess.run(
                [script_path],
                capture_output=True, text=True,
                timeout=self.config.timeout_seconds,
                env={**os.environ, **env}
            )
            
            if result.returncode == 0:
                self.logger.info("カスタムスクリプトが正常に実行されました")
                return True
            else:
                self.logger.error(f"カスタムスクリプトに失敗しました: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("カスタムスクリプトがタイムアウトしました")
            return False
    
    def _create_notification_message(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> str:
        """通知メッセージの作成"""
        status_emoji = "❌" if gate_result.result == QualityGateResult.FAILED else "⚠️"
        
        message = f"""
{status_emoji} 品質ゲート失敗通知

ゲートタイプ: {gate_result.gate_type.value}
結果: {gate_result.result.value}
メッセージ: {gate_result.message}
時刻: {gate_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        if gate_result.actual_value is not None and gate_result.expected_value is not None:
            message += f"実際の値: {gate_result.actual_value}\n"
            message += f"期待値: {gate_result.expected_value}\n"
        
        if gate_result.details:
            message += f"\n詳細:\n"
            for key, value in gate_result.details.items():
                message += f"  {key}: {value}\n"
        
        return message
    
    def _create_issue_body(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]) -> str:
        """課題本文の作成"""
        body = f"""
## 品質ゲート失敗レポート

**ゲートタイプ:** {gate_result.gate_type.value}
**結果:** {gate_result.result.value}
**時刻:** {gate_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

### 問題の詳細
{gate_result.message}
"""
        
        if gate_result.actual_value is not None and gate_result.expected_value is not None:
            body += f"""
### 測定値
- **実際の値:** {gate_result.actual_value}
- **期待値:** {gate_result.expected_value}
"""
        
        if gate_result.details:
            body += f"""
### 詳細情報
```json
{json.dumps(gate_result.details, indent=2, ensure_ascii=False)}
```
"""
        
        body += """
### 対応方法
1. 失敗の原因を調査してください
2. 必要な修正を実施してください
3. 品質ゲートを再実行してください

このissueは自動生成されました。
"""
        
        return body


class QualityGateManager:
    """品質ゲート管理システム
    
    複数の品質ゲートを管理し、チェック結果に基づいて
    自動対応アクションを実行する。
    """
    
    def __init__(self, output_dir: Path = Path("quality_gate_results")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logging()
        self.gates: Dict[QualityGateType, QualityGateChecker] = {}
        self.actions: List[AutoActionExecutor] = []
        
        # 結果の保存
        self.check_results: List[QualityGateCheckResult] = []
    
    def _setup_logging(self) -> logging.Logger:
        """ログ設定の初期化"""
        logger = logging.getLogger("quality_gate_manager")
        logger.setLevel(logging.INFO)
        
        # ログファイルハンドラー
        log_file = self.output_dir / f"quality_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    
    def add_gate(self, gate_checker: QualityGateChecker):
        """品質ゲートの追加"""
        self.gates[gate_checker.config.gate_type] = gate_checker
        self.logger.info(f"品質ゲートを追加しました: {gate_checker.config.gate_type.value}")
    
    def add_action(self, action_executor: AutoActionExecutor):
        """自動対応アクションの追加"""
        self.actions.append(action_executor)
        self.logger.info(f"自動対応アクションを追加しました: {action_executor.config.action_type.value}")
    
    async def check_all_gates(self, data: Dict[str, Any]) -> Dict[QualityGateType, QualityGateCheckResult]:
        """すべての品質ゲートのチェック
        
        Args:
            data: チェック対象データ
            
        Returns:
            ゲートタイプ別のチェック結果
        """
        self.logger.info("品質ゲートチェックを開始します")
        
        results = {}
        
        for gate_type, gate_checker in self.gates.items():
            if not gate_checker.config.enabled:
                self.logger.info(f"品質ゲート {gate_type.value} はスキップされました（無効）")
                continue
            
            try:
                self.logger.info(f"品質ゲート {gate_type.value} をチェックしています")
                result = await gate_checker.check(data)
                results[gate_type] = result
                self.check_results.append(result)
                
                self.logger.info(
                    f"品質ゲート {gate_type.value} 完了: {result.result.value} "
                    f"({result.execution_time:.2f}秒)"
                )
                
                # 自動対応アクションの実行
                if result.result in [QualityGateResult.FAILED, QualityGateResult.WARNING]:
                    await self._execute_actions(result, data)
                
            except Exception as e:
                self.logger.error(f"品質ゲート {gate_type.value} でエラーが発生しました: {e}")
                error_result = QualityGateCheckResult(
                    gate_type=gate_type,
                    result=QualityGateResult.FAILED,
                    message=f"チェック中にエラーが発生しました: {e}",
                    timestamp=datetime.now()
                )
                results[gate_type] = error_result
                self.check_results.append(error_result)
        
        # 結果の保存
        await self._save_results(results)
        
        self.logger.info("品質ゲートチェックが完了しました")
        return results
    
    async def _execute_actions(self, gate_result: QualityGateCheckResult, context: Dict[str, Any]):
        """自動対応アクションの実行"""
        self.logger.info(f"自動対応アクションを実行します: {gate_result.gate_type.value}")
        
        for action_executor in self.actions:
            try:
                success = await action_executor.execute(gate_result, context)
                if success:
                    self.logger.info(f"アクション {action_executor.config.action_type.value} が正常に実行されました")
                else:
                    self.logger.warning(f"アクション {action_executor.config.action_type.value} の実行に失敗しました")
            except Exception as e:
                self.logger.error(f"アクション {action_executor.config.action_type.value} でエラーが発生しました: {e}")
    
    async def _save_results(self, results: Dict[QualityGateType, QualityGateCheckResult]):
        """結果の保存"""
        try:
            results_data = {}
            for gate_type, result in results.items():
                results_data[gate_type.value] = asdict(result)
                # datetime オブジェクトを文字列に変換
                if results_data[gate_type.value]['timestamp']:
                    results_data[gate_type.value]['timestamp'] = result.timestamp.isoformat()
            
            results_file = self.output_dir / f"quality_gate_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"結果を保存しました: {results_file}")
            
        except Exception as e:
            self.logger.error(f"結果保存中にエラーが発生しました: {e}")
    
    def get_overall_result(self) -> QualityGateResult:
        """全体的な品質ゲート結果の取得"""
        if not self.check_results:
            return QualityGateResult.PASSED
        
        # 失敗があれば失敗
        if any(r.result == QualityGateResult.FAILED for r in self.check_results):
            return QualityGateResult.FAILED
        
        # 警告があれば警告
        if any(r.result == QualityGateResult.WARNING for r in self.check_results):
            return QualityGateResult.WARNING
        
        # ブロックがあればブロック
        if any(r.result == QualityGateResult.BLOCKED for r in self.check_results):
            return QualityGateResult.BLOCKED
        
        return QualityGateResult.PASSED


def create_default_quality_gates() -> List[QualityGateChecker]:
    """デフォルト品質ゲートの作成"""
    gates = []
    
    # テストカバレッジゲート
    coverage_config = QualityGateConfig(
        gate_type=QualityGateType.TEST_COVERAGE,
        thresholds=[
            QualityThreshold(
                name="line_coverage",
                min_value=80.0,
                warning_threshold=85.0,
                unit="%",
                description="ラインカバレッジ"
            )
        ]
    )
    gates.append(TestCoverageGate(coverage_config))
    
    # セキュリティ問題ゲート
    security_config = QualityGateConfig(
        gate_type=QualityGateType.SECURITY_ISSUES,
        thresholds=[
            QualityThreshold(
                name="critical_issues",
                max_value=0,
                description="重要なセキュリティ問題"
            ),
            QualityThreshold(
                name="high_issues",
                max_value=2,
                description="高レベルのセキュリティ問題"
            )
        ]
    )
    gates.append(SecurityIssuesGate(security_config))
    
    # パフォーマンス回帰ゲート
    performance_config = QualityGateConfig(
        gate_type=QualityGateType.PERFORMANCE_REGRESSION,
        thresholds=[
            QualityThreshold(
                name="max_regression_percent",
                max_value=10.0,
                unit="%",
                description="最大パフォーマンス回帰率"
            )
        ]
    )
    gates.append(PerformanceRegressionGate(performance_config))
    
    return gates


def create_default_actions() -> List[AutoActionExecutor]:
    """デフォルト自動対応アクションの作成"""
    actions = []
    
    # 通知アクション
    notification_config = AutoActionConfig(
        action_type=ActionType.NOTIFICATION,
        trigger_conditions=[QualityGateResult.FAILED, QualityGateResult.WARNING]
    )
    actions.append(AutoActionExecutor(notification_config))
    
    # デプロイメントブロックアクション
    block_config = AutoActionConfig(
        action_type=ActionType.BLOCK_DEPLOYMENT,
        trigger_conditions=[QualityGateResult.FAILED],
        parameters={'block_file': '.deployment_blocked'}
    )
    actions.append(AutoActionExecutor(block_config))
    
    return actions


async def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="品質ゲート管理システム")
    parser.add_argument("--coverage-file", help="カバレッジファイルパス")
    parser.add_argument("--security-report", help="セキュリティレポートファイルパス")
    parser.add_argument("--performance-metrics", help="パフォーマンスメトリクスファイルパス")
    parser.add_argument("--baseline-file", help="パフォーマンスベースラインファイルパス")
    parser.add_argument("--output-dir", default="quality_gate_results", help="出力ディレクトリ")
    
    args = parser.parse_args()
    
    # 品質ゲート管理システムの初期化
    manager = QualityGateManager(Path(args.output_dir))
    
    # デフォルト品質ゲートの追加
    for gate in create_default_quality_gates():
        manager.add_gate(gate)
    
    # デフォルト自動対応アクションの追加
    for action in create_default_actions():
        manager.add_action(action)
    
    # チェックデータの準備
    check_data = {}
    
    if args.coverage_file:
        check_data['coverage_file'] = args.coverage_file
    
    if args.security_report:
        check_data['security_report'] = args.security_report
    
    if args.performance_metrics:
        with open(args.performance_metrics, 'r', encoding='utf-8') as f:
            check_data['current_metrics'] = json.load(f)
        
        if args.baseline_file:
            check_data['baseline_file'] = args.baseline_file
    
    # 品質ゲートチェックの実行
    results = await manager.check_all_gates(check_data)
    
    # 結果の出力
    print(f"\n=== 品質ゲート結果 ===")
    for gate_type, result in results.items():
        status_emoji = "✅" if result.result == QualityGateResult.PASSED else "❌"
        print(f"{status_emoji} {gate_type.value}: {result.result.value}")
        if result.message:
            print(f"   {result.message}")
    
    overall_result = manager.get_overall_result()
    print(f"\n全体結果: {overall_result.value}")
    
    # 終了コード
    sys.exit(0 if overall_result == QualityGateResult.PASSED else 1)


if __name__ == "__main__":
    import os
    asyncio.run(main())