# -*- coding: utf-8 -*-
"""
エラー注入クラス

テスト中に意図的にエラーを発生させ、
アプリケーションのエラーハンドリングと回復機能を検証します。
"""

import os
import time
import random
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import tempfile
import shutil


@dataclass
class ErrorInjectionConfig:
    """エラー注入設定を格納するデータクラス"""
    error_type: str
    probability: float = 1.0  # エラー発生確率（0.0-1.0）
    delay_seconds: float = 0.0  # エラー発生までの遅延
    duration_seconds: float = 0.0  # エラー継続時間（0は一回限り）
    parameters: Dict[str, Any] = None


@dataclass
class InjectedError:
    """注入されたエラーの記録"""
    error_type: str
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    parameters: Dict[str, Any] = None


class ErrorInjector:
    """
    エラー注入クラス
    
    様々な種類のエラーを意図的に発生させ、
    アプリケーションの堅牢性をテストします。
    """
    
    def __init__(self):
        """エラー注入クラスの初期化"""
        self.logger = logging.getLogger(f"validation.{self.__class__.__name__}")
        
        # 注入されたエラーの履歴
        self.injected_errors: List[InjectedError] = []
        
        # アクティブなエラー注入
        self.active_injections: Dict[str, threading.Thread] = {}
        
        # 一時的に作成したファイル/ディレクトリの追跡
        self.temp_resources: List[str] = []
        
        # エラー注入メソッドのマッピング
        self.injection_methods = {
            'file_not_found': self._inject_file_not_found,
            'permission_denied': self._inject_permission_denied,
            'disk_full': self._inject_disk_full,
            'memory_error': self._inject_memory_error,
            'network_timeout': self._inject_network_timeout,
            'database_connection_error': self._inject_database_error,
            'corrupted_file': self._inject_corrupted_file,
            'process_killed': self._inject_process_killed,
            'system_overload': self._inject_system_overload,
            'encoding_error': self._inject_encoding_error
        }
        
        self.logger.debug("エラー注入クラスを初期化しました")
    
    def inject_error(self, error_type: str, **kwargs) -> bool:
        """
        エラーの注入
        
        Args:
            error_type: 注入するエラーの種類
            **kwargs: エラー注入の追加パラメータ
        
        Returns:
            エラー注入が成功した場合True
        """
        if error_type not in self.injection_methods:
            self.logger.error(f"未対応のエラータイプ: {error_type}")
            return False
        
        config = ErrorInjectionConfig(
            error_type=error_type,
            probability=kwargs.get('probability', 1.0),
            delay_seconds=kwargs.get('delay_seconds', 0.0),
            duration_seconds=kwargs.get('duration_seconds', 0.0),
            parameters=kwargs.get('parameters', {})
        )
        
        # 確率的エラー注入
        if random.random() > config.probability:
            self.logger.debug(f"エラー注入をスキップしました（確率: {config.probability}）")
            return False
        
        # 遅延実行
        if config.delay_seconds > 0:
            time.sleep(config.delay_seconds)
        
        try:
            # エラー注入メソッドの実行
            injection_method = self.injection_methods[error_type]
            injection_method(config)
            
            # 成功記録
            injected_error = InjectedError(
                error_type=error_type,
                timestamp=datetime.now(),
                success=True,
                parameters=config.parameters
            )
            self.injected_errors.append(injected_error)
            
            self.logger.info(f"エラー注入が成功しました: {error_type}")
            return True
            
        except Exception as e:
            # 失敗記録
            injected_error = InjectedError(
                error_type=error_type,
                timestamp=datetime.now(),
                success=False,
                error_message=str(e),
                parameters=config.parameters
            )
            self.injected_errors.append(injected_error)
            
            self.logger.error(f"エラー注入が失敗しました: {error_type} - {str(e)}")
            return False
    
    def _inject_file_not_found(self, config: ErrorInjectionConfig) -> None:
        """ファイル不存在エラーの注入"""
        target_file = config.parameters.get('target_file', 'nonexistent_file.txt')
        
        # 存在するファイルを一時的に移動
        if os.path.exists(target_file):
            backup_path = f"{target_file}.backup_{int(time.time())}"
            shutil.move(target_file, backup_path)
            self.temp_resources.append(backup_path)
            
            # 継続時間後に復元
            if config.duration_seconds > 0:
                def restore_file():
                    time.sleep(config.duration_seconds)
                    if os.path.exists(backup_path):
                        shutil.move(backup_path, target_file)
                        self.temp_resources.remove(backup_path)
                
                thread = threading.Thread(target=restore_file, daemon=True)
                thread.start()
                self.active_injections[f"file_restore_{target_file}"] = thread
        
        self.logger.debug(f"ファイル不存在エラーを注入しました: {target_file}")
    
    def _inject_permission_denied(self, config: ErrorInjectionConfig) -> None:
        """権限拒否エラーの注入"""
        target_path = config.parameters.get('target_path', tempfile.gettempdir())
        
        if os.path.exists(target_path):
            # 権限を変更（読み取り専用に）
            original_mode = os.stat(target_path).st_mode
            os.chmod(target_path, 0o444)  # 読み取り専用
            
            # 継続時間後に権限を復元
            if config.duration_seconds > 0:
                def restore_permissions():
                    time.sleep(config.duration_seconds)
                    if os.path.exists(target_path):
                        os.chmod(target_path, original_mode)
                
                thread = threading.Thread(target=restore_permissions, daemon=True)
                thread.start()
                self.active_injections[f"permission_restore_{target_path}"] = thread
        
        self.logger.debug(f"権限拒否エラーを注入しました: {target_path}")
    
    def _inject_disk_full(self, config: ErrorInjectionConfig) -> None:
        """ディスク容量不足エラーの注入"""
        # 大きなダミーファイルを作成してディスク容量を消費
        dummy_size_mb = config.parameters.get('size_mb', 100)
        dummy_file = tempfile.mktemp(suffix='.dummy')
        
        try:
            with open(dummy_file, 'wb') as f:
                # 指定サイズのダミーデータを書き込み
                chunk_size = 1024 * 1024  # 1MB
                for _ in range(dummy_size_mb):
                    f.write(b'0' * chunk_size)
            
            self.temp_resources.append(dummy_file)
            
            # 継続時間後にファイルを削除
            if config.duration_seconds > 0:
                def cleanup_dummy_file():
                    time.sleep(config.duration_seconds)
                    if os.path.exists(dummy_file):
                        os.remove(dummy_file)
                        self.temp_resources.remove(dummy_file)
                
                thread = threading.Thread(target=cleanup_dummy_file, daemon=True)
                thread.start()
                self.active_injections[f"disk_cleanup_{dummy_file}"] = thread
            
            self.logger.debug(f"ディスク容量不足エラーを注入しました: {dummy_size_mb}MB")
            
        except Exception as e:
            self.logger.error(f"ディスク容量不足エラーの注入に失敗しました: {e}")
    
    def _inject_memory_error(self, config: ErrorInjectionConfig) -> None:
        """メモリ不足エラーの注入"""
        # 大量のメモリを消費するオブジェクトを作成
        memory_mb = config.parameters.get('memory_mb', 100)
        
        # メモリ消費オブジェクトを作成
        memory_consumer = []
        try:
            chunk_size = 1024 * 1024  # 1MB
            for _ in range(memory_mb):
                memory_consumer.append(bytearray(chunk_size))
            
            # 継続時間後にメモリを解放
            if config.duration_seconds > 0:
                def release_memory():
                    time.sleep(config.duration_seconds)
                    memory_consumer.clear()
                
                thread = threading.Thread(target=release_memory, daemon=True)
                thread.start()
                self.active_injections[f"memory_release"] = thread
            
            self.logger.debug(f"メモリ不足エラーを注入しました: {memory_mb}MB")
            
        except MemoryError:
            self.logger.debug("メモリ不足エラーが正常に発生しました")
    
    def _inject_network_timeout(self, config: ErrorInjectionConfig) -> None:
        """ネットワークタイムアウトエラーの注入"""
        # ネットワーク遅延をシミュレート
        delay_seconds = config.parameters.get('timeout_seconds', 30.0)
        
        self.logger.debug(f"ネットワークタイムアウトエラーを注入しました: {delay_seconds}秒")
        
        # 実際の遅延を発生
        time.sleep(delay_seconds)
    
    def _inject_database_error(self, config: ErrorInjectionConfig) -> None:
        """データベース接続エラーの注入"""
        # データベースファイルを一時的に移動またはロック
        db_file = config.parameters.get('db_file', 'docmind_data/documents.db')
        
        if os.path.exists(db_file):
            backup_path = f"{db_file}.backup_{int(time.time())}"
            shutil.move(db_file, backup_path)
            self.temp_resources.append(backup_path)
            
            # 継続時間後に復元
            if config.duration_seconds > 0:
                def restore_database():
                    time.sleep(config.duration_seconds)
                    if os.path.exists(backup_path):
                        shutil.move(backup_path, db_file)
                        self.temp_resources.remove(backup_path)
                
                thread = threading.Thread(target=restore_database, daemon=True)
                thread.start()
                self.active_injections[f"db_restore_{db_file}"] = thread
        
        self.logger.debug(f"データベース接続エラーを注入しました: {db_file}")
    
    def _inject_corrupted_file(self, config: ErrorInjectionConfig) -> None:
        """ファイル破損エラーの注入"""
        target_file = config.parameters.get('target_file', 'test_corrupted.txt')
        
        # 破損ファイルを作成
        with open(target_file, 'wb') as f:
            # ランダムなバイナリデータを書き込み
            corrupted_data = bytes([random.randint(0, 255) for _ in range(1024)])
            f.write(corrupted_data)
        
        self.temp_resources.append(target_file)
        
        self.logger.debug(f"ファイル破損エラーを注入しました: {target_file}")
    
    def _inject_process_killed(self, config: ErrorInjectionConfig) -> None:
        """プロセス強制終了エラーの注入"""
        # 実際のプロセス終了は危険なので、例外を発生させる
        process_name = config.parameters.get('process_name', 'test_process')
        
        self.logger.debug(f"プロセス強制終了エラーを注入しました: {process_name}")
        
        # ProcessLookupErrorを発生
        raise ProcessLookupError(f"プロセス '{process_name}' が見つかりません")
    
    def _inject_system_overload(self, config: ErrorInjectionConfig) -> None:
        """システム過負荷エラーの注入"""
        # CPU集約的な処理を実行
        duration = config.parameters.get('duration_seconds', 5.0)
        
        def cpu_intensive_task():
            end_time = time.time() + duration
            while time.time() < end_time:
                # CPU集約的な計算
                sum(i * i for i in range(1000))
        
        # 複数スレッドでCPU負荷を生成
        threads = []
        cpu_count = config.parameters.get('thread_count', 4)
        
        for _ in range(cpu_count):
            thread = threading.Thread(target=cpu_intensive_task, daemon=True)
            thread.start()
            threads.append(thread)
        
        self.logger.debug(f"システム過負荷エラーを注入しました: {cpu_count}スレッド, {duration}秒")
    
    def _inject_encoding_error(self, config: ErrorInjectionConfig) -> None:
        """文字エンコーディングエラーの注入"""
        target_file = config.parameters.get('target_file', 'test_encoding_error.txt')
        
        # 不正なエンコーディングのファイルを作成
        with open(target_file, 'wb') as f:
            # UTF-8として不正なバイト列を書き込み
            invalid_utf8 = b'\xff\xfe\x00\x00invalid utf-8 sequence\x80\x81'
            f.write(invalid_utf8)
        
        self.temp_resources.append(target_file)
        
        self.logger.debug(f"文字エンコーディングエラーを注入しました: {target_file}")
    
    def get_injection_history(self) -> List[InjectedError]:
        """
        エラー注入履歴の取得
        
        Returns:
            注入されたエラーのリスト
        """
        return self.injected_errors.copy()
    
    def get_injection_statistics(self) -> Dict[str, Any]:
        """
        エラー注入統計の取得
        
        Returns:
            統計情報の辞書
        """
        if not self.injected_errors:
            return {}
        
        total_injections = len(self.injected_errors)
        successful_injections = sum(1 for error in self.injected_errors if error.success)
        
        error_types = {}
        for error in self.injected_errors:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
        
        return {
            'total_injections': total_injections,
            'successful_injections': successful_injections,
            'success_rate': successful_injections / total_injections if total_injections > 0 else 0.0,
            'error_types': error_types,
            'active_injections': len(self.active_injections)
        }
    
    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        self.logger.info("エラー注入のクリーンアップを開始します")
        
        # アクティブな注入スレッドの停止
        for injection_id, thread in self.active_injections.items():
            if thread.is_alive():
                self.logger.debug(f"注入スレッドの終了を待機中: {injection_id}")
                thread.join(timeout=5.0)
        
        self.active_injections.clear()
        
        # 一時リソースの削除
        for resource_path in self.temp_resources:
            try:
                if os.path.exists(resource_path):
                    if os.path.isfile(resource_path):
                        os.remove(resource_path)
                    elif os.path.isdir(resource_path):
                        shutil.rmtree(resource_path)
                    self.logger.debug(f"一時リソースを削除しました: {resource_path}")
            except Exception as e:
                self.logger.warning(f"一時リソースの削除に失敗しました: {resource_path} - {e}")
        
        self.temp_resources.clear()
        self.injected_errors.clear()
        
        self.logger.info("エラー注入のクリーンアップが完了しました")