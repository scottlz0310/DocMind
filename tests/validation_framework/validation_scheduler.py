#!/usr/bin/env python3
"""
検証スケジュール管理システム

コミット時、日次、週次、リリース前の検証スケジュールを管理し、
自動実行とスケジューリングを提供する。
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import schedule
import threading

from .comprehensive_validation_suite import (
    ComprehensiveValidationSuite,
    ValidationConfig,
    ValidationLevel,
    ValidationResult,
    create_validation_config
)
from .ci_cd_pipeline import CICDPipeline, PipelineConfig, create_pipeline_config
from .quality_gate_manager import QualityGateManager, create_default_quality_gates, create_default_actions


class ScheduleType(Enum):
    """スケジュールタイプ"""
    COMMIT = "commit"          # コミット時
    DAILY = "daily"            # 日次
    WEEKLY = "weekly"          # 週次
    RELEASE = "release"        # リリース前
    MANUAL = "manual"          # 手動実行
    CONTINUOUS = "continuous"  # 継続的実行


class ScheduleStatus(Enum):
    """スケジュール状態"""
    PENDING = "pending"        # 実行待ち
    RUNNING = "running"        # 実行中
    COMPLETED = "completed"    # 完了
    FAILED = "failed"          # 失敗
    CANCELLED = "cancelled"    # キャンセル
    SKIPPED = "skipped"        # スキップ


@dataclass
class ScheduleConfig:
    """スケジュール設定"""
    schedule_type: ScheduleType
    enabled: bool = True
    
    # 実行タイミング設定
    cron_expression: Optional[str] = None
    daily_time: Optional[str] = None  # "HH:MM" 形式
    weekly_day: Optional[str] = None  # "monday", "tuesday", etc.
    weekly_time: Optional[str] = None
    
    # 検証設定
    validation_level: ValidationLevel = ValidationLevel.DAILY
    enable_ci_cd: bool = True
    enable_quality_gates: bool = True
    
    # 実行条件
    min_interval_hours: int = 1  # 最小実行間隔
    max_concurrent_runs: int = 1  # 最大同時実行数
    timeout_minutes: int = 120   # タイムアウト時間
    
    # Git条件
    watch_branches: List[str] = None  # 監視対象ブランチ
    skip_if_no_changes: bool = True   # 変更がない場合はスキップ
    
    # 通知設定
    notify_on_success: bool = False
    notify_on_failure: bool = True
    notification_channels: List[str] = None


@dataclass
class ScheduleExecution:
    """スケジュール実行記録"""
    execution_id: str
    schedule_type: ScheduleType
    start_time: datetime
    end_time: Optional[datetime] = None
    status: ScheduleStatus = ScheduleStatus.PENDING
    
    # 実行結果
    validation_result: Optional[ValidationResult] = None
    pipeline_result: Optional[str] = None
    quality_gate_result: Optional[str] = None
    
    # メタデータ
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    triggered_by: str = "scheduler"
    
    # ログとアーティファクト
    log_file: Optional[Path] = None
    artifacts: List[Path] = None
    error_message: Optional[str] = None


class GitWatcher:
    """Git変更監視"""
    
    def __init__(self, project_root: Path, watch_branches: List[str] = None):
        self.project_root = project_root
        self.watch_branches = watch_branches or ["main", "master", "develop"]
        self.logger = logging.getLogger("git_watcher")
        
        # 最後のコミット情報
        self.last_commits: Dict[str, str] = {}
        self._update_last_commits()
    
    def _update_last_commits(self):
        """最後のコミット情報の更新"""
        try:
            for branch in self.watch_branches:
                try:
                    result = subprocess.run(
                        ["git", "rev-parse", f"origin/{branch}"],
                        capture_output=True, text=True, cwd=self.project_root
                    )
                    if result.returncode == 0:
                        self.last_commits[branch] = result.stdout.strip()
                except subprocess.CalledProcessError:
                    # ブランチが存在しない場合はスキップ
                    continue
        except Exception as e:
            self.logger.warning(f"Git情報の取得に失敗しました: {e}")
    
    def check_for_changes(self) -> List[str]:
        """変更があったブランチのチェック
        
        Returns:
            変更があったブランチのリスト
        """
        changed_branches = []
        
        try:
            # リモートの最新情報を取得
            subprocess.run(
                ["git", "fetch", "--all"],
                capture_output=True, cwd=self.project_root
            )
            
            for branch in self.watch_branches:
                try:
                    result = subprocess.run(
                        ["git", "rev-parse", f"origin/{branch}"],
                        capture_output=True, text=True, cwd=self.project_root
                    )
                    
                    if result.returncode == 0:
                        current_commit = result.stdout.strip()
                        last_commit = self.last_commits.get(branch)
                        
                        if last_commit and current_commit != last_commit:
                            changed_branches.append(branch)
                            self.last_commits[branch] = current_commit
                            self.logger.info(f"ブランチ {branch} で変更を検出しました: {current_commit[:8]}")
                        elif not last_commit:
                            # 初回実行時
                            self.last_commits[branch] = current_commit
                            
                except subprocess.CalledProcessError:
                    continue
                    
        except Exception as e:
            self.logger.error(f"Git変更チェック中にエラーが発生しました: {e}")
        
        return changed_branches
    
    def get_current_commit_info(self) -> Dict[str, str]:
        """現在のコミット情報の取得"""
        try:
            # 現在のブランチ
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            # 現在のコミット
            commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            return {
                'branch': branch_result.stdout.strip() if branch_result.returncode == 0 else 'unknown',
                'commit': commit_result.stdout.strip() if commit_result.returncode == 0 else 'unknown'
            }
            
        except Exception as e:
            self.logger.error(f"Git情報の取得に失敗しました: {e}")
            return {'branch': 'unknown', 'commit': 'unknown'}


class ValidationScheduler:
    """検証スケジューラー
    
    様々なトリガーに基づいて検証を自動実行し、
    スケジュール管理を行う。
    """
    
    def __init__(self, project_root: Path, output_dir: Path = Path("scheduler_results")):
        self.project_root = project_root
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logging()
        self.git_watcher = GitWatcher(project_root)
        
        # スケジュール設定
        self.schedules: Dict[ScheduleType, ScheduleConfig] = {}
        self.executions: List[ScheduleExecution] = []
        self.running_executions: Dict[str, ScheduleExecution] = {}
        
        # スケジューラーの状態
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
        # 実行履歴の読み込み
        self._load_execution_history()
    
    def _setup_logging(self) -> logging.Logger:
        """ログ設定の初期化"""
        logger = logging.getLogger("validation_scheduler")
        logger.setLevel(logging.INFO)
        
        # ログファイルハンドラー
        log_file = self.output_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
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
    
    def add_schedule(self, config: ScheduleConfig):
        """スケジュールの追加"""
        self.schedules[config.schedule_type] = config
        self.logger.info(f"スケジュールを追加しました: {config.schedule_type.value}")
        
        # スケジューラーへの登録
        self._register_schedule(config)
    
    def _register_schedule(self, config: ScheduleConfig):
        """スケジューラーへの登録"""
        if not config.enabled:
            return
        
        if config.schedule_type == ScheduleType.DAILY and config.daily_time:
            schedule.every().day.at(config.daily_time).do(
                self._schedule_job, config.schedule_type
            )
            self.logger.info(f"日次スケジュールを登録しました: {config.daily_time}")
        
        elif config.schedule_type == ScheduleType.WEEKLY and config.weekly_day and config.weekly_time:
            getattr(schedule.every(), config.weekly_day.lower()).at(config.weekly_time).do(
                self._schedule_job, config.schedule_type
            )
            self.logger.info(f"週次スケジュールを登録しました: {config.weekly_day} {config.weekly_time}")
    
    def _schedule_job(self, schedule_type: ScheduleType):
        """スケジュールジョブの実行"""
        asyncio.create_task(self.execute_validation(schedule_type, "scheduler"))
    
    async def start_scheduler(self):
        """スケジューラーの開始"""
        if self.is_running:
            self.logger.warning("スケジューラーは既に実行中です")
            return
        
        self.is_running = True
        self.logger.info("検証スケジューラーを開始しました")
        
        # スケジューラースレッドの開始
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # コミット監視の開始
        if ScheduleType.COMMIT in self.schedules:
            asyncio.create_task(self._monitor_commits())
    
    def _run_scheduler(self):
        """スケジューラーの実行ループ"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1分間隔でチェック
            except Exception as e:
                self.logger.error(f"スケジューラー実行中にエラーが発生しました: {e}")
    
    async def _monitor_commits(self):
        """コミット監視"""
        commit_config = self.schedules[ScheduleType.COMMIT]
        
        while self.is_running:
            try:
                changed_branches = self.git_watcher.check_for_changes()
                
                if changed_branches:
                    # 監視対象ブランチに変更があった場合
                    watch_branches = commit_config.watch_branches or ["main", "master", "develop"]
                    
                    for branch in changed_branches:
                        if branch in watch_branches:
                            self.logger.info(f"ブランチ {branch} の変更によりコミット検証を実行します")
                            await self.execute_validation(ScheduleType.COMMIT, f"git_commit_{branch}")
                            break
                
                # 監視間隔
                await asyncio.sleep(300)  # 5分間隔
                
            except Exception as e:
                self.logger.error(f"コミット監視中にエラーが発生しました: {e}")
                await asyncio.sleep(60)
    
    async def stop_scheduler(self):
        """スケジューラーの停止"""
        self.is_running = False
        
        # 実行中のジョブの完了を待機
        if self.running_executions:
            self.logger.info("実行中のジョブの完了を待機しています...")
            while self.running_executions:
                await asyncio.sleep(5)
        
        self.logger.info("検証スケジューラーを停止しました")
    
    async def execute_validation(self, schedule_type: ScheduleType, triggered_by: str = "manual") -> ScheduleExecution:
        """検証の実行
        
        Args:
            schedule_type: スケジュールタイプ
            triggered_by: 実行トリガー
            
        Returns:
            実行記録
        """
        config = self.schedules.get(schedule_type)
        if not config or not config.enabled:
            self.logger.warning(f"スケジュール {schedule_type.value} は無効です")
            return None
        
        # 実行条件のチェック
        if not await self._check_execution_conditions(config):
            self.logger.info(f"実行条件を満たさないため、{schedule_type.value} をスキップします")
            return None
        
        # 実行記録の作成
        execution = ScheduleExecution(
            execution_id=f"{schedule_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            schedule_type=schedule_type,
            start_time=datetime.now(),
            triggered_by=triggered_by,
            status=ScheduleStatus.PENDING
        )
        
        # Git情報の取得
        git_info = self.git_watcher.get_current_commit_info()
        execution.git_branch = git_info['branch']
        execution.git_commit = git_info['commit']
        
        self.executions.append(execution)
        self.running_executions[execution.execution_id] = execution
        
        try:
            self.logger.info(f"検証を開始します: {execution.execution_id}")
            execution.status = ScheduleStatus.RUNNING
            
            # ログファイルの設定
            execution.log_file = self.output_dir / f"{execution.execution_id}.log"
            
            # 検証の実行
            await self._run_validation_pipeline(execution, config)
            
            execution.status = ScheduleStatus.COMPLETED
            execution.end_time = datetime.now()
            
            self.logger.info(f"検証が完了しました: {execution.execution_id}")
            
            # 通知の送信
            if config.notify_on_success:
                await self._send_notification(execution, config)
            
        except Exception as e:
            execution.status = ScheduleStatus.FAILED
            execution.end_time = datetime.now()
            execution.error_message = str(e)
            
            self.logger.error(f"検証に失敗しました: {execution.execution_id} - {e}")
            
            # 失敗通知の送信
            if config.notify_on_failure:
                await self._send_notification(execution, config)
        
        finally:
            # 実行記録の保存
            await self._save_execution(execution)
            
            # 実行中リストから削除
            if execution.execution_id in self.running_executions:
                del self.running_executions[execution.execution_id]
        
        return execution
    
    async def _check_execution_conditions(self, config: ScheduleConfig) -> bool:
        """実行条件のチェック"""
        # 最小実行間隔のチェック
        if config.min_interval_hours > 0:
            recent_executions = [
                e for e in self.executions
                if (e.schedule_type == config.schedule_type and
                    e.start_time > datetime.now() - timedelta(hours=config.min_interval_hours))
            ]
            
            if recent_executions:
                self.logger.info(f"最小実行間隔 {config.min_interval_hours} 時間以内に実行済みです")
                return False
        
        # 最大同時実行数のチェック
        current_runs = len([
            e for e in self.running_executions.values()
            if e.schedule_type == config.schedule_type
        ])
        
        if current_runs >= config.max_concurrent_runs:
            self.logger.info(f"最大同時実行数 {config.max_concurrent_runs} に達しています")
            return False
        
        # 変更チェック
        if config.skip_if_no_changes and config.schedule_type != ScheduleType.COMMIT:
            changed_branches = self.git_watcher.check_for_changes()
            if not changed_branches:
                self.logger.info("変更がないため実行をスキップします")
                return False
        
        return True
    
    async def _run_validation_pipeline(self, execution: ScheduleExecution, config: ScheduleConfig):
        """検証パイプラインの実行"""
        artifacts = []
        
        try:
            # 包括的検証の実行
            if config.validation_level:
                validation_config = create_validation_config(
                    level=config.validation_level,
                    output_dir=self.output_dir / execution.execution_id / "validation"
                )
                
                suite = ComprehensiveValidationSuite(validation_config)
                validation_summary = await suite.run_validation()
                
                execution.validation_result = validation_summary.overall_result
                artifacts.extend(list(validation_config.output_dir.glob("*")))
            
            # CI/CDパイプラインの実行
            if config.enable_ci_cd:
                pipeline_config = create_pipeline_config(
                    project_root=self.project_root,
                    output_dir=self.output_dir / execution.execution_id / "pipeline",
                    timeout_minutes=config.timeout_minutes
                )
                
                pipeline = CICDPipeline(pipeline_config)
                pipeline_summary = await pipeline.run_pipeline()
                
                execution.pipeline_result = pipeline_summary.overall_result.value
                artifacts.extend(pipeline_summary.artifacts)
            
            # 品質ゲートの実行
            if config.enable_quality_gates:
                quality_manager = QualityGateManager(
                    self.output_dir / execution.execution_id / "quality_gates"
                )
                
                # デフォルト品質ゲートの追加
                for gate in create_default_quality_gates():
                    quality_manager.add_gate(gate)
                
                for action in create_default_actions():
                    quality_manager.add_action(action)
                
                # 品質ゲートデータの準備
                gate_data = {}
                
                # カバレッジファイルの検索
                coverage_files = list(self.project_root.glob("coverage.xml"))
                if coverage_files:
                    gate_data['coverage_file'] = str(coverage_files[0])
                
                # セキュリティレポートの検索
                security_files = list(self.project_root.glob("security_report.json"))
                if security_files:
                    gate_data['security_report'] = str(security_files[0])
                
                gate_results = await quality_manager.check_all_gates(gate_data)
                execution.quality_gate_result = quality_manager.get_overall_result().value
                
                artifacts.extend(list(quality_manager.output_dir.glob("*")))
            
            execution.artifacts = artifacts
            
        except asyncio.TimeoutError:
            raise RuntimeError(f"検証がタイムアウトしました ({config.timeout_minutes}分)")
    
    async def _send_notification(self, execution: ScheduleExecution, config: ScheduleConfig):
        """通知の送信"""
        try:
            message = self._create_notification_message(execution)
            
            # 通知チャンネルに応じた送信
            if config.notification_channels:
                for channel in config.notification_channels:
                    if channel.startswith("webhook:"):
                        webhook_url = channel[8:]  # "webhook:" を除去
                        await self._send_webhook_notification(message, webhook_url)
                    elif channel.startswith("email:"):
                        email_address = channel[6:]  # "email:" を除去
                        await self._send_email_notification(message, email_address)
            
            self.logger.info("通知を送信しました")
            
        except Exception as e:
            self.logger.error(f"通知送信中にエラーが発生しました: {e}")
    
    def _create_notification_message(self, execution: ScheduleExecution) -> str:
        """通知メッセージの作成"""
        status_emoji = {
            ScheduleStatus.COMPLETED: "✅",
            ScheduleStatus.FAILED: "❌",
            ScheduleStatus.CANCELLED: "⚠️"
        }.get(execution.status, "ℹ️")
        
        duration = ""
        if execution.end_time and execution.start_time:
            duration_seconds = (execution.end_time - execution.start_time).total_seconds()
            duration = f" ({duration_seconds:.0f}秒)"
        
        message = f"""
{status_emoji} 検証スケジュール実行結果

実行ID: {execution.execution_id}
スケジュールタイプ: {execution.schedule_type.value}
状態: {execution.status.value}{duration}
実行者: {execution.triggered_by}

Git情報:
  ブランチ: {execution.git_branch}
  コミット: {execution.git_commit[:8] if execution.git_commit else 'N/A'}

結果:
"""
        
        if execution.validation_result:
            message += f"  検証結果: {execution.validation_result.value}\n"
        
        if execution.pipeline_result:
            message += f"  パイプライン結果: {execution.pipeline_result}\n"
        
        if execution.quality_gate_result:
            message += f"  品質ゲート結果: {execution.quality_gate_result}\n"
        
        if execution.error_message:
            message += f"\nエラー: {execution.error_message}\n"
        
        return message
    
    async def _send_webhook_notification(self, message: str, webhook_url: str):
        """Webhook通知の送信"""
        # 実装は使用するWebhookサービスに依存
        self.logger.info(f"Webhook通知を送信しました: {webhook_url}")
    
    async def _send_email_notification(self, message: str, email_address: str):
        """メール通知の送信"""
        # 実装は使用するメールサービスに依存
        self.logger.info(f"メール通知を送信しました: {email_address}")
    
    async def _save_execution(self, execution: ScheduleExecution):
        """実行記録の保存"""
        try:
            execution_data = asdict(execution)
            
            # datetime オブジェクトを文字列に変換
            if execution_data['start_time']:
                execution_data['start_time'] = execution.start_time.isoformat()
            if execution_data['end_time']:
                execution_data['end_time'] = execution.end_time.isoformat()
            
            # Path オブジェクトを文字列に変換
            if execution_data['log_file']:
                execution_data['log_file'] = str(execution.log_file)
            if execution_data['artifacts']:
                execution_data['artifacts'] = [str(p) for p in execution.artifacts]
            
            # Enum を文字列に変換
            execution_data['schedule_type'] = execution.schedule_type.value
            execution_data['status'] = execution.status.value
            if execution_data['validation_result']:
                execution_data['validation_result'] = execution.validation_result.value
            
            # 実行記録ファイルの保存
            execution_file = self.output_dir / f"{execution.execution_id}_execution.json"
            with open(execution_file, 'w', encoding='utf-8') as f:
                json.dump(execution_data, f, indent=2, ensure_ascii=False)
            
            # 履歴ファイルの更新
            await self._update_execution_history()
            
        except Exception as e:
            self.logger.error(f"実行記録保存中にエラーが発生しました: {e}")
    
    def _load_execution_history(self):
        """実行履歴の読み込み"""
        try:
            history_file = self.output_dir / "execution_history.json"
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                # 最近の実行記録のみ読み込み（過去30日）
                cutoff_date = datetime.now() - timedelta(days=30)
                
                for execution_data in history_data:
                    start_time = datetime.fromisoformat(execution_data['start_time'])
                    if start_time > cutoff_date:
                        execution = self._deserialize_execution(execution_data)
                        self.executions.append(execution)
                
                self.logger.info(f"実行履歴を読み込みました: {len(self.executions)}件")
                
        except Exception as e:
            self.logger.warning(f"実行履歴の読み込みに失敗しました: {e}")
    
    async def _update_execution_history(self):
        """実行履歴の更新"""
        try:
            history_data = []
            
            for execution in self.executions:
                execution_data = asdict(execution)
                
                # datetime オブジェクトを文字列に変換
                if execution_data['start_time']:
                    execution_data['start_time'] = execution.start_time.isoformat()
                if execution_data['end_time']:
                    execution_data['end_time'] = execution.end_time.isoformat()
                
                # その他のオブジェクトを文字列に変換
                if execution_data['log_file']:
                    execution_data['log_file'] = str(execution.log_file)
                if execution_data['artifacts']:
                    execution_data['artifacts'] = [str(p) for p in execution.artifacts]
                
                # Enum を文字列に変換
                execution_data['schedule_type'] = execution.schedule_type.value
                execution_data['status'] = execution.status.value
                if execution_data['validation_result']:
                    execution_data['validation_result'] = execution.validation_result.value
                
                history_data.append(execution_data)
            
            history_file = self.output_dir / "execution_history.json"
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"実行履歴更新中にエラーが発生しました: {e}")
    
    def _deserialize_execution(self, execution_data: Dict[str, Any]) -> ScheduleExecution:
        """実行記録のデシリアライズ"""
        execution = ScheduleExecution(
            execution_id=execution_data['execution_id'],
            schedule_type=ScheduleType(execution_data['schedule_type']),
            start_time=datetime.fromisoformat(execution_data['start_time']),
            status=ScheduleStatus(execution_data['status']),
            triggered_by=execution_data.get('triggered_by', 'unknown')
        )
        
        if execution_data.get('end_time'):
            execution.end_time = datetime.fromisoformat(execution_data['end_time'])
        
        if execution_data.get('validation_result'):
            execution.validation_result = ValidationResult(execution_data['validation_result'])
        
        execution.pipeline_result = execution_data.get('pipeline_result')
        execution.quality_gate_result = execution_data.get('quality_gate_result')
        execution.git_commit = execution_data.get('git_commit')
        execution.git_branch = execution_data.get('git_branch')
        execution.error_message = execution_data.get('error_message')
        
        if execution_data.get('log_file'):
            execution.log_file = Path(execution_data['log_file'])
        
        if execution_data.get('artifacts'):
            execution.artifacts = [Path(p) for p in execution_data['artifacts']]
        
        return execution
    
    def get_execution_status(self) -> Dict[str, Any]:
        """実行状況の取得"""
        return {
            'running_executions': len(self.running_executions),
            'total_executions': len(self.executions),
            'recent_executions': [
                {
                    'execution_id': e.execution_id,
                    'schedule_type': e.schedule_type.value,
                    'status': e.status.value,
                    'start_time': e.start_time.isoformat()
                }
                for e in sorted(self.executions, key=lambda x: x.start_time, reverse=True)[:10]
            ]
        }


def create_default_schedules() -> List[ScheduleConfig]:
    """デフォルトスケジュールの作成"""
    schedules = []
    
    # コミット時検証
    commit_config = ScheduleConfig(
        schedule_type=ScheduleType.COMMIT,
        validation_level=ValidationLevel.COMMIT,
        min_interval_hours=0,  # コミット毎に実行
        timeout_minutes=30,
        watch_branches=["main", "master", "develop"],
        notify_on_failure=True
    )
    schedules.append(commit_config)
    
    # 日次検証
    daily_config = ScheduleConfig(
        schedule_type=ScheduleType.DAILY,
        validation_level=ValidationLevel.DAILY,
        daily_time="02:00",  # 午前2時
        timeout_minutes=60,
        notify_on_failure=True
    )
    schedules.append(daily_config)
    
    # 週次検証
    weekly_config = ScheduleConfig(
        schedule_type=ScheduleType.WEEKLY,
        validation_level=ValidationLevel.WEEKLY,
        weekly_day="sunday",
        weekly_time="01:00",  # 日曜日午前1時
        timeout_minutes=120,
        notify_on_success=True,
        notify_on_failure=True
    )
    schedules.append(weekly_config)
    
    return schedules


async def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="検証スケジューラー")
    parser.add_argument("--project-root", default=".", help="プロジェクトルートディレクトリ")
    parser.add_argument("--output-dir", default="scheduler_results", help="出力ディレクトリ")
    parser.add_argument("--daemon", action="store_true", help="デーモンモードで実行")
    parser.add_argument("--execute", choices=[t.value for t in ScheduleType], help="指定されたスケジュールを即座に実行")
    parser.add_argument("--status", action="store_true", help="実行状況を表示")
    
    args = parser.parse_args()
    
    # スケジューラーの初期化
    scheduler = ValidationScheduler(
        project_root=Path(args.project_root),
        output_dir=Path(args.output_dir)
    )
    
    # デフォルトスケジュールの追加
    for schedule_config in create_default_schedules():
        scheduler.add_schedule(schedule_config)
    
    if args.status:
        # 実行状況の表示
        status = scheduler.get_execution_status()
        print(f"実行中: {status['running_executions']}")
        print(f"総実行数: {status['total_executions']}")
        print("\n最近の実行:")
        for execution in status['recent_executions']:
            print(f"  {execution['execution_id']}: {execution['status']} ({execution['start_time']})")
        return
    
    if args.execute:
        # 指定されたスケジュールの即座実行
        schedule_type = ScheduleType(args.execute)
        execution = await scheduler.execute_validation(schedule_type, "manual")
        
        if execution:
            print(f"実行完了: {execution.execution_id}")
            print(f"状態: {execution.status.value}")
            if execution.error_message:
                print(f"エラー: {execution.error_message}")
        else:
            print("実行条件を満たさないため、実行されませんでした")
        return
    
    if args.daemon:
        # デーモンモードで実行
        print("検証スケジューラーをデーモンモードで開始します...")
        await scheduler.start_scheduler()
        
        try:
            # 無限ループで実行継続
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            print("\n検証スケジューラーを停止しています...")
            await scheduler.stop_scheduler()
    else:
        print("使用方法: --daemon でデーモン実行、--execute でスケジュール実行、--status で状況確認")


if __name__ == "__main__":
    asyncio.run(main())