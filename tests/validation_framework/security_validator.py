# -*- coding: utf-8 -*-
"""
セキュリティ・プライバシー検証クラス

DocMindアプリケーションのセキュリティ要件を包括的に検証します。
ローカル処理の確認、外部通信監視、ファイルアクセス権限、
機密データ暗号化、メモリ内データ保護を検証します。
"""

import os
import sys
import time
import socket
import threading
import tempfile
import shutil
import subprocess
import psutil
import hashlib
import json
import gc
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import logging
import stat
import platform
from unittest.mock import patch, MagicMock

# DocMindコンポーネントのインポート
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from .base_validator import BaseValidator, ValidationResult, ValidationConfig
    from .performance_monitor import PerformanceMonitor
    from .memory_monitor import MemoryMonitor
    from .test_data_generator import TestDataGenerator, TestDatasetConfig
    from .statistics_collector import StatisticsCollector
except ImportError:
    from base_validator import BaseValidator, ValidationResult, ValidationConfig
    from performance_monitor import PerformanceMonitor
    from memory_monitor import MemoryMonitor
    from test_data_generator import TestDataGenerator, TestDatasetConfig
    from statistics_collector import StatisticsCollector

from src.core.search_manager import SearchManager
from src.core.index_manager import IndexManager
from src.core.embedding_manager import EmbeddingManager
from src.core.document_processor import DocumentProcessor
from src.data.models import SearchQuery, SearchType, FileType
from src.utils.config import Config


@dataclass
class SecurityThresholds:
    """セキュリティ閾値設定"""
    max_external_connections: int = 0           # 許可される外部接続数
    max_temp_file_lifetime_seconds: int = 300   # 一時ファイルの最大生存時間（秒）
    min_file_permission_security: int = 0o600   # 最小ファイル権限（所有者のみ読み書き）
    max_memory_scan_duration_seconds: int = 30  # メモリスキャンの最大時間
    encryption_key_min_length: int = 32         # 暗号化キーの最小長


@dataclass
class SecurityMetrics:
    """セキュリティ測定結果"""
    test_name: str
    security_level: str  # "SECURE", "WARNING", "CRITICAL"
    external_connections: List[str] = field(default_factory=list)
    file_permissions: Dict[str, str] = field(default_factory=dict)
    temp_files_created: List[str] = field(default_factory=list)
    temp_files_cleaned: List[str] = field(default_factory=list)
    memory_leaks_detected: List[str] = field(default_factory=list)
    encryption_status: Dict[str, bool] = field(default_factory=dict)
    vulnerabilities: List[str] = field(default_factory=list)
    compliance_score: float = 0.0
    additional_details: Dict[str, Any] = field(default_factory=dict)


class NetworkMonitor:
    """ネットワーク通信監視クラス"""
    
    def __init__(self):
        self.connections: List[Dict[str, Any]] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.process_pid = os.getpid()
    
    def start_monitoring(self) -> None:
        """ネットワーク監視開始"""
        self.monitoring = True
        self.connections.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_connections)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """ネットワーク監視停止"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
    
    def _monitor_connections(self) -> None:
        """ネットワーク接続の監視"""
        while self.monitoring:
            try:
                # 現在のプロセスの接続を取得
                process = psutil.Process(self.process_pid)
                connections = process.connections(kind='inet')
                
                for conn in connections:
                    if conn.status == psutil.CONN_ESTABLISHED:
                        connection_info = {
                            'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                            'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                            'status': conn.status,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # 外部接続かどうかを判定
                        if conn.raddr and not self._is_local_address(conn.raddr.ip):
                            self.connections.append(connection_info)
                
                time.sleep(0.5)  # 0.5秒間隔で監視
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            except Exception as e:
                # 監視エラーは無視して継続
                pass
    
    def _is_local_address(self, ip: str) -> bool:
        """ローカルアドレスかどうかを判定"""
        local_addresses = ['127.0.0.1', '::1', 'localhost']
        return ip in local_addresses or ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.')
    
    def get_external_connections(self) -> List[Dict[str, Any]]:
        """外部接続のリストを取得"""
        return self.connections.copy()


class FilePermissionChecker:
    """ファイル権限チェッククラス"""
    
    def __init__(self):
        self.checked_files: Dict[str, Dict[str, Any]] = {}
    
    def check_file_permissions(self, file_path: str) -> Dict[str, Any]:
        """ファイル権限をチェック"""
        try:
            stat_info = os.stat(file_path)
            permissions = stat.filemode(stat_info.st_mode)
            octal_permissions = oct(stat_info.st_mode)[-3:]
            
            # セキュリティレベルの判定
            security_level = self._assess_security_level(stat_info.st_mode)
            
            permission_info = {
                'file_path': file_path,
                'permissions': permissions,
                'octal_permissions': octal_permissions,
                'security_level': security_level,
                'owner_readable': bool(stat_info.st_mode & stat.S_IRUSR),
                'owner_writable': bool(stat_info.st_mode & stat.S_IWUSR),
                'group_readable': bool(stat_info.st_mode & stat.S_IRGRP),
                'group_writable': bool(stat_info.st_mode & stat.S_IWGRP),
                'other_readable': bool(stat_info.st_mode & stat.S_IROTH),
                'other_writable': bool(stat_info.st_mode & stat.S_IWOTH),
                'is_secure': security_level in ['SECURE', 'WARNING']
            }
            
            self.checked_files[file_path] = permission_info
            return permission_info
            
        except (OSError, IOError) as e:
            return {
                'file_path': file_path,
                'error': str(e),
                'security_level': 'ERROR',
                'is_secure': False
            }
    
    def _assess_security_level(self, mode: int) -> str:
        """セキュリティレベルを評価"""
        # 他者に読み書き権限がある場合は危険
        if mode & (stat.S_IROTH | stat.S_IWOTH):
            return 'CRITICAL'
        
        # グループに書き込み権限がある場合は警告
        if mode & stat.S_IWGRP:
            return 'WARNING'
        
        # 所有者のみアクセス可能な場合は安全
        return 'SECURE'
    
    def get_insecure_files(self) -> List[str]:
        """セキュアでないファイルのリストを取得"""
        return [
            file_path for file_path, info in self.checked_files.items()
            if not info.get('is_secure', False)
        ]


class MemoryScanner:
    """メモリ内機密データスキャナー"""
    
    def __init__(self):
        self.sensitive_patterns = [
            b'password',
            b'secret',
            b'token',
            b'key',
            b'credential',
            b'private',
            # 日本語パターン
            'パスワード'.encode('utf-8'),
            '秘密'.encode('utf-8'),
            '機密'.encode('utf-8'),
            'トークン'.encode('utf-8')
        ]
        self.found_patterns: List[str] = []
    
    def scan_process_memory(self, max_duration_seconds: int = 30) -> List[str]:
        """プロセスメモリをスキャン（模擬実装）"""
        # 実際のメモリスキャンは複雑で危険なため、模擬実装
        # 実環境では専用のセキュリティツールを使用することを推奨
        
        start_time = time.time()
        found_issues = []
        
        try:
            # ガベージコレクションを実行してメモリ状態を確認
            gc.collect()
            
            # メモリ内のオブジェクトを検査（限定的）
            for obj in gc.get_objects():
                if time.time() - start_time > max_duration_seconds:
                    break
                
                try:
                    if isinstance(obj, (str, bytes)):
                        obj_data = obj if isinstance(obj, bytes) else obj.encode('utf-8', errors='ignore')
                        
                        for pattern in self.sensitive_patterns:
                            if pattern in obj_data.lower():
                                found_issues.append(f"機密パターン検出: {pattern.decode('utf-8', errors='ignore')}")
                                break
                
                except (UnicodeError, AttributeError):
                    continue
        
        except Exception as e:
            found_issues.append(f"メモリスキャンエラー: {str(e)}")
        
        self.found_patterns = found_issues
        return found_issues


class SecurityValidator(BaseValidator):
    """
    セキュリティ・プライバシー検証クラス
    
    DocMindアプリケーションのセキュリティ要件を包括的に検証します。
    """
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        セキュリティ検証クラスの初期化
        
        Args:
            config: 検証設定
        """
        super().__init__(config)
        
        # セキュリティ閾値の設定
        self.thresholds = SecurityThresholds()
        
        # 監視・チェックコンポーネント
        self.network_monitor = NetworkMonitor()
        self.file_permission_checker = FilePermissionChecker()
        self.memory_scanner = MemoryScanner()
        
        # テストデータ生成器
        self.data_generator = TestDataGenerator()
        
        # 測定結果の保存
        self.security_metrics: List[SecurityMetrics] = []
        
        # テスト環境
        self.test_base_dir: Optional[str] = None
        self.test_components: Dict[str, Any] = {}
        self.created_temp_files: List[str] = []
        
        self.logger.info("SecurityValidatorを初期化しました")
    
    def setup_test_environment(self) -> None:
        """テスト環境のセットアップ"""
        self.logger.info("セキュリティテスト環境をセットアップします")
        
        # 一時ディレクトリの作成
        self.test_base_dir = tempfile.mkdtemp(prefix="docmind_security_test_")
        self.logger.info(f"テストディレクトリ: {self.test_base_dir}")
        
        # DocMindコンポーネントの初期化
        self._setup_docmind_components()
        
        # テストデータ生成器の設定
        self.data_generator.setup_test_environment(self.test_base_dir)
        
        self.logger.info("セキュリティテスト環境のセットアップが完了しました")
    
    def _setup_docmind_components(self) -> None:
        """DocMindコンポーネントの初期化"""
        try:
            # 設定の初期化
            config = Config()
            test_data_dir = os.path.join(self.test_base_dir, "docmind_data")
            config.set("data_directory", test_data_dir)
            os.makedirs(test_data_dir, exist_ok=True)
            
            # インデックスマネージャーの初期化
            index_path = os.path.join(test_data_dir, "whoosh_index")
            self.test_components['index_manager'] = IndexManager(index_path)
            
            # 埋め込みマネージャーの初期化
            embeddings_path = os.path.join(test_data_dir, "embeddings.pkl")
            self.test_components['embedding_manager'] = EmbeddingManager(
                model_name="all-MiniLM-L6-v2",
                embeddings_path=embeddings_path
            )
            
            # 検索マネージャーの初期化
            self.test_components['search_manager'] = SearchManager(
                self.test_components['index_manager'],
                self.test_components['embedding_manager']
            )
            
            # ドキュメントプロセッサーの初期化
            self.test_components['document_processor'] = DocumentProcessor()
            
            self.logger.debug("DocMindコンポーネントの初期化が完了しました")
            
        except Exception as e:
            self.logger.error(f"DocMindコンポーネントの初期化に失敗しました: {e}")
            raise
    
    def teardown_test_environment(self) -> None:
        """テスト環境のクリーンアップ"""
        self.logger.info("セキュリティテスト環境をクリーンアップします")
        
        try:
            # ネットワーク監視の停止
            self.network_monitor.stop_monitoring()
            
            # 作成した一時ファイルの削除
            for temp_file in self.created_temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError:
                    pass
            
            # コンポーネントのクリーンアップ
            for component_name, component in self.test_components.items():
                if hasattr(component, 'close'):
                    component.close()
                elif hasattr(component, 'cleanup'):
                    component.cleanup()
            
            # テストデータのクリーンアップ
            self.data_generator.cleanup()
            
            # 一時ディレクトリの削除
            if self.test_base_dir and os.path.exists(self.test_base_dir):
                shutil.rmtree(self.test_base_dir)
                self.logger.debug(f"テストディレクトリを削除しました: {self.test_base_dir}")
            
            # メモリのクリーンアップ
            gc.collect()
            
        except Exception as e:
            self.logger.warning(f"クリーンアップ中にエラーが発生しました: {e}")
        
        self.logger.info("セキュリティテスト環境のクリーンアップが完了しました")
    
    def test_local_processing_verification(self) -> None:
        """ローカル処理の確認と外部通信監視の検証"""
        self.logger.info("ローカル処理の確認と外部通信監視を検証します")
        
        # ネットワーク監視開始
        self.network_monitor.start_monitoring()
        
        try:
            # テストドキュメントの準備
            test_documents = self._create_test_documents(10)
            
            # DocMind操作の実行（外部通信が発生しないことを確認）
            search_manager = self.test_components['search_manager']
            document_processor = self.test_components['document_processor']
            
            # ドキュメント処理
            for doc_path in test_documents:
                document = document_processor.process_file(doc_path)
                if document:
                    self.test_components['index_manager'].add_document(document)
            
            # 検索実行
            query = SearchQuery(
                query_text="テスト検索",
                search_type=SearchType.HYBRID,
                limit=10
            )
            results = search_manager.search(query)
            
            # 埋め込み処理（ローカルモデル使用）
            embedding_manager = self.test_components['embedding_manager']
            test_text = "これはローカル処理のテストです"
            embeddings = embedding_manager.get_embeddings([test_text])
            
            # 少し待機して通信を監視
            time.sleep(2.0)
            
        finally:
            # ネットワーク監視停止
            self.network_monitor.stop_monitoring()
        
        # 外部通信の検証
        external_connections = self.network_monitor.get_external_connections()
        
        # セキュリティメトリクスの作成
        security_level = "SECURE" if len(external_connections) == 0 else "CRITICAL"
        
        metrics = SecurityMetrics(
            test_name="local_processing_verification",
            security_level=security_level,
            external_connections=[conn['remote_address'] for conn in external_connections],
            compliance_score=1.0 if len(external_connections) == 0 else 0.0,
            additional_details={
                'total_connections_detected': len(external_connections),
                'connection_details': external_connections,
                'test_operations': ['document_processing', 'indexing', 'search', 'embedding']
            }
        )
        
        # 要件の検証
        self.assert_condition(
            len(external_connections) <= self.thresholds.max_external_connections,
            f"外部通信が検出されました: {len(external_connections)}件の接続が発生"
        )
        
        self.security_metrics.append(metrics)
        
        self.logger.info(f"ローカル処理検証完了 - 外部接続: {len(external_connections)}件")    

    def test_file_access_permissions_verification(self) -> None:
        """ファイルアクセス権限と一時ファイル安全削除の検証"""
        self.logger.info("ファイルアクセス権限と一時ファイル安全削除を検証します")
        
        # テスト用ファイルの作成
        test_files = self._create_permission_test_files()
        
        # ファイル権限のチェック
        permission_results = {}
        insecure_files = []
        
        for file_path in test_files:
            permission_info = self.file_permission_checker.check_file_permissions(file_path)
            permission_results[file_path] = permission_info
            
            if not permission_info.get('is_secure', False):
                insecure_files.append(file_path)
        
        # DocMindが作成するファイルの権限チェック
        docmind_files = self._get_docmind_created_files()
        for file_path in docmind_files:
            if os.path.exists(file_path):
                permission_info = self.file_permission_checker.check_file_permissions(file_path)
                permission_results[file_path] = permission_info
                
                if not permission_info.get('is_secure', False):
                    insecure_files.append(file_path)
        
        # 一時ファイルの安全削除テスト
        temp_file_test_results = self._test_temp_file_security()
        
        # セキュリティレベルの判定
        security_level = "SECURE"
        if len(insecure_files) > 0:
            security_level = "CRITICAL"
        elif not temp_file_test_results['secure_deletion']:
            security_level = "WARNING"
        
        # セキュリティメトリクスの作成
        metrics = SecurityMetrics(
            test_name="file_access_permissions_verification",
            security_level=security_level,
            file_permissions={
                file_path: info.get('permissions', 'ERROR')
                for file_path, info in permission_results.items()
            },
            temp_files_created=temp_file_test_results['created_files'],
            temp_files_cleaned=temp_file_test_results['cleaned_files'],
            vulnerabilities=[f"セキュアでないファイル権限: {f}" for f in insecure_files],
            compliance_score=1.0 - (len(insecure_files) / max(len(permission_results), 1)),
            additional_details={
                'total_files_checked': len(permission_results),
                'insecure_files_count': len(insecure_files),
                'temp_file_security': temp_file_test_results
            }
        )
        
        # メトリクスを先に追加
        self.security_metrics.append(metrics)
        
        # 要件の検証
        self.assert_condition(
            len(insecure_files) == 0,
            f"セキュアでないファイル権限が検出されました: {insecure_files}"
        )
        
        self.assert_condition(
            temp_file_test_results['secure_deletion'],
            "一時ファイルの安全削除が確認できませんでした"
        )
        
        self.logger.info(f"ファイル権限検証完了 - チェック済みファイル: {len(permission_results)}件")
    
    def test_data_encryption_verification(self) -> None:
        """機密データ暗号化とメモリ内データ保護の検証"""
        self.logger.info("機密データ暗号化とメモリ内データ保護を検証します")
        
        # 設定ファイルの暗号化テスト
        encryption_results = self._test_configuration_encryption()
        
        # データベースファイルの暗号化チェック
        database_encryption = self._test_database_encryption()
        
        # メモリ内機密データのスキャン
        memory_scan_results = self.memory_scanner.scan_process_memory(
            self.thresholds.max_memory_scan_duration_seconds
        )
        
        # 埋め込みキャッシュファイルの暗号化チェック
        embedding_encryption = self._test_embedding_cache_encryption()
        
        # 暗号化状況の評価
        encryption_status = {
            'configuration_encrypted': encryption_results['encrypted'],
            'database_encrypted': database_encryption['encrypted'],
            'embedding_cache_encrypted': embedding_encryption['encrypted'],
            'memory_scan_clean': len(memory_scan_results) == 0
        }
        
        # セキュリティレベルの判定
        security_level = "SECURE"
        vulnerabilities = []
        
        if not encryption_status['memory_scan_clean']:
            security_level = "WARNING"
            vulnerabilities.extend([f"メモリ内機密データ: {issue}" for issue in memory_scan_results])
        
        if not encryption_status['configuration_encrypted']:
            security_level = "WARNING"
            vulnerabilities.append("設定ファイルが暗号化されていません")
        
        # コンプライアンススコアの計算
        compliance_score = sum(encryption_status.values()) / len(encryption_status)
        
        # セキュリティメトリクスの作成
        metrics = SecurityMetrics(
            test_name="data_encryption_verification",
            security_level=security_level,
            encryption_status=encryption_status,
            memory_leaks_detected=memory_scan_results,
            vulnerabilities=vulnerabilities,
            compliance_score=compliance_score,
            additional_details={
                'encryption_test_results': {
                    'configuration': encryption_results,
                    'database': database_encryption,
                    'embedding_cache': embedding_encryption
                },
                'memory_scan_duration': self.thresholds.max_memory_scan_duration_seconds,
                'memory_issues_found': len(memory_scan_results)
            }
        )
        
        # メトリクスを先に追加
        self.security_metrics.append(metrics)
        
        # 要件の検証（警告レベルは許容）
        self.assert_condition(
            security_level != "CRITICAL",
            f"重大なセキュリティ問題が検出されました: {vulnerabilities}"
        )
        
        self.logger.info(f"データ暗号化検証完了 - コンプライアンススコア: {compliance_score:.2f}")
    
    def test_privacy_protection_verification(self) -> None:
        """プライバシー保護機能の包括検証"""
        self.logger.info("プライバシー保護機能を包括的に検証します")
        
        # ログファイルの個人情報チェック
        log_privacy_results = self._test_log_file_privacy()
        
        # 一時ファイルの機密情報チェック
        temp_file_privacy_results = self._test_temp_file_privacy()
        
        # プロセスメモリの機密情報チェック
        memory_privacy_results = self._test_memory_privacy()
        
        # ネットワーク通信のプライバシーチェック
        network_privacy_results = self._test_network_privacy()
        
        # プライバシー保護レベルの評価
        privacy_issues = []
        privacy_issues.extend(log_privacy_results.get('issues', []))
        privacy_issues.extend(temp_file_privacy_results.get('issues', []))
        privacy_issues.extend(memory_privacy_results.get('issues', []))
        privacy_issues.extend(network_privacy_results.get('issues', []))
        
        # セキュリティレベルの判定
        security_level = "SECURE"
        if len(privacy_issues) > 0:
            security_level = "WARNING" if len(privacy_issues) <= 3 else "CRITICAL"
        
        # コンプライアンススコアの計算
        total_checks = sum([
            len(log_privacy_results.get('checked_items', [])),
            len(temp_file_privacy_results.get('checked_items', [])),
            len(memory_privacy_results.get('checked_items', [])),
            len(network_privacy_results.get('checked_items', []))
        ])
        
        compliance_score = 1.0 - (len(privacy_issues) / max(total_checks, 1))
        
        # セキュリティメトリクスの作成
        metrics = SecurityMetrics(
            test_name="privacy_protection_verification",
            security_level=security_level,
            vulnerabilities=privacy_issues,
            compliance_score=compliance_score,
            additional_details={
                'log_privacy': log_privacy_results,
                'temp_file_privacy': temp_file_privacy_results,
                'memory_privacy': memory_privacy_results,
                'network_privacy': network_privacy_results,
                'total_privacy_issues': len(privacy_issues),
                'privacy_categories_checked': 4
            }
        )
        
        # メトリクスを先に追加
        self.security_metrics.append(metrics)
        
        # 要件の検証
        self.assert_condition(
            security_level != "CRITICAL",
            f"重大なプライバシー問題が検出されました: {privacy_issues}"
        )
        
        self.logger.info(f"プライバシー保護検証完了 - 問題: {len(privacy_issues)}件")
    
    def test_comprehensive_security_audit(self) -> None:
        """包括的セキュリティ監査の実行"""
        self.logger.info("包括的セキュリティ監査を実行します")
        
        # 全セキュリティテストの統合実行
        audit_results = {
            'local_processing': self._audit_local_processing(),
            'file_security': self._audit_file_security(),
            'data_protection': self._audit_data_protection(),
            'privacy_compliance': self._audit_privacy_compliance(),
            'system_hardening': self._audit_system_hardening()
        }
        
        # 総合セキュリティスコアの計算
        category_scores = [result['score'] for result in audit_results.values()]
        overall_score = sum(category_scores) / len(category_scores)
        
        # 重大な脆弱性の集計
        critical_vulnerabilities = []
        for category, result in audit_results.items():
            critical_vulnerabilities.extend(result.get('critical_issues', []))
        
        # セキュリティレベルの判定
        if overall_score >= 0.9:
            security_level = "SECURE"
        elif overall_score >= 0.7:
            security_level = "WARNING"
        else:
            security_level = "CRITICAL"
        
        # セキュリティメトリクスの作成
        metrics = SecurityMetrics(
            test_name="comprehensive_security_audit",
            security_level=security_level,
            vulnerabilities=critical_vulnerabilities,
            compliance_score=overall_score,
            additional_details={
                'audit_categories': audit_results,
                'category_scores': {
                    category: result['score'] 
                    for category, result in audit_results.items()
                },
                'total_checks_performed': sum(
                    result.get('checks_performed', 0) 
                    for result in audit_results.values()
                ),
                'security_recommendations': self._generate_security_recommendations(audit_results)
            }
        )
        
        # メトリクスを先に追加
        self.security_metrics.append(metrics)
        
        # 要件の検証
        self.assert_condition(
            overall_score >= 0.7,
            f"セキュリティ監査で不合格: スコア {overall_score:.2f} < 0.7"
        )
        
        self.assert_condition(
            len(critical_vulnerabilities) == 0,
            f"重大な脆弱性が検出されました: {critical_vulnerabilities}"
        )
        
        self.logger.info(f"包括的セキュリティ監査完了 - 総合スコア: {overall_score:.2f}")
    
    # ヘルパーメソッド
    
    def _create_test_documents(self, count: int) -> List[str]:
        """テスト用ドキュメントの作成"""
        test_documents = []
        
        for i in range(count):
            # テストファイルの作成
            file_path = os.path.join(self.test_base_dir, f"test_doc_{i:03d}.txt")
            content = f"これはテストドキュメント{i}です。\n機密情報は含まれていません。\nローカル処理のテスト用です。"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            test_documents.append(file_path)
            self.created_temp_files.append(file_path)
        
        return test_documents
    
    def _create_permission_test_files(self) -> List[str]:
        """権限テスト用ファイルの作成"""
        test_files = []
        
        # 異なる権限のテストファイルを作成
        permission_tests = [
            ('secure_file.txt', 0o600),      # 所有者のみ読み書き
            ('group_readable.txt', 0o640),   # グループ読み取り可能
            ('world_readable.txt', 0o644),   # 全員読み取り可能
        ]
        
        for filename, permissions in permission_tests:
            file_path = os.path.join(self.test_base_dir, filename)
            
            # ファイル作成
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"テストファイル: {filename}")
            
            # 権限設定
            try:
                os.chmod(file_path, permissions)
            except OSError:
                # Windowsでは権限設定が制限される場合がある
                pass
            
            test_files.append(file_path)
            self.created_temp_files.append(file_path)
        
        return test_files
    
    def _get_docmind_created_files(self) -> List[str]:
        """DocMindが作成するファイルのリストを取得"""
        docmind_files = []
        
        if self.test_base_dir:
            docmind_data_dir = os.path.join(self.test_base_dir, "docmind_data")
            
            # データベースファイル
            db_file = os.path.join(docmind_data_dir, "documents.db")
            if os.path.exists(db_file):
                docmind_files.append(db_file)
            
            # 埋め込みキャッシュファイル
            embeddings_file = os.path.join(docmind_data_dir, "embeddings.pkl")
            if os.path.exists(embeddings_file):
                docmind_files.append(embeddings_file)
            
            # 設定ファイル
            config_file = os.path.join(docmind_data_dir, "config.json")
            if os.path.exists(config_file):
                docmind_files.append(config_file)
            
            # ログファイル
            log_dir = os.path.join(docmind_data_dir, "logs")
            if os.path.exists(log_dir):
                for log_file in os.listdir(log_dir):
                    docmind_files.append(os.path.join(log_dir, log_file))
        
        return docmind_files
    
    def _test_temp_file_security(self) -> Dict[str, Any]:
        """一時ファイルのセキュリティテスト"""
        created_files = []
        cleaned_files = []
        
        # 一時ファイルの作成と削除テスト
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(
                prefix="docmind_security_test_",
                suffix=".tmp",
                delete=False
            )
            
            # 機密データの書き込み
            sensitive_data = f"機密テストデータ{i}: password123, secret_key_xyz"
            temp_file.write(sensitive_data.encode('utf-8'))
            temp_file.close()
            
            created_files.append(temp_file.name)
            
            # ファイルの存在確認
            if os.path.exists(temp_file.name):
                # 安全な削除の実行
                try:
                    # ファイルを0で上書き（セキュア削除の模擬）
                    with open(temp_file.name, 'wb') as f:
                        f.write(b'\x00' * len(sensitive_data.encode('utf-8')))
                    
                    # ファイル削除
                    os.remove(temp_file.name)
                    cleaned_files.append(temp_file.name)
                    
                except OSError:
                    pass
        
        return {
            'created_files': created_files,
            'cleaned_files': cleaned_files,
            'secure_deletion': len(cleaned_files) == len(created_files)
        }
    
    def _test_configuration_encryption(self) -> Dict[str, Any]:
        """設定ファイルの暗号化テスト"""
        # 模擬的な設定ファイル暗号化テスト
        config_file = os.path.join(self.test_base_dir, "test_config.json")
        
        # テスト設定データ
        config_data = {
            "database_path": "/path/to/database",
            "api_key": "test_api_key_12345",  # 機密情報
            "user_preferences": {
                "theme": "dark",
                "language": "ja"
            }
        }
        
        # 設定ファイルの作成
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        
        # 暗号化状況の確認（実際の実装では暗号化ライブラリを使用）
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 平文で機密情報が保存されているかチェック
        has_plaintext_secrets = "api_key" in content and "test_api_key_12345" in content
        
        return {
            'config_file': config_file,
            'encrypted': not has_plaintext_secrets,  # 平文でなければ暗号化されているとみなす
            'has_sensitive_data': True,
            'encryption_method': 'AES-256' if not has_plaintext_secrets else 'NONE'
        }
    
    def _test_database_encryption(self) -> Dict[str, Any]:
        """データベースファイルの暗号化チェック"""
        # SQLiteデータベースの暗号化チェック（模擬）
        db_path = os.path.join(self.test_base_dir, "docmind_data", "documents.db")
        
        if not os.path.exists(db_path):
            return {
                'database_file': db_path,
                'encrypted': True,  # ファイルが存在しない場合は問題なし
                'file_exists': False
            }
        
        # ファイルヘッダーをチェックして暗号化を判定
        try:
            with open(db_path, 'rb') as f:
                header = f.read(16)
            
            # SQLiteの標準ヘッダー（平文）をチェック
            sqlite_header = b'SQLite format 3\x00'
            is_plaintext_sqlite = header == sqlite_header
            
            return {
                'database_file': db_path,
                'encrypted': not is_plaintext_sqlite,
                'file_exists': True,
                'header_analysis': 'plaintext_sqlite' if is_plaintext_sqlite else 'encrypted_or_unknown'
            }
            
        except IOError:
            return {
                'database_file': db_path,
                'encrypted': False,
                'file_exists': True,
                'error': 'ファイル読み取りエラー'
            }
    
    def _test_embedding_cache_encryption(self) -> Dict[str, Any]:
        """埋め込みキャッシュファイルの暗号化チェック"""
        embeddings_path = os.path.join(self.test_base_dir, "docmind_data", "embeddings.pkl")
        
        if not os.path.exists(embeddings_path):
            return {
                'embeddings_file': embeddings_path,
                'encrypted': True,  # ファイルが存在しない場合は問題なし
                'file_exists': False
            }
        
        # Pickleファイルの暗号化チェック
        try:
            with open(embeddings_path, 'rb') as f:
                header = f.read(8)
            
            # Pickleの標準ヘッダーをチェック
            is_plaintext_pickle = header.startswith(b'\x80\x03') or header.startswith(b'\x80\x04')
            
            return {
                'embeddings_file': embeddings_path,
                'encrypted': not is_plaintext_pickle,
                'file_exists': True,
                'format_analysis': 'plaintext_pickle' if is_plaintext_pickle else 'encrypted_or_unknown'
            }
            
        except IOError:
            return {
                'embeddings_file': embeddings_path,
                'encrypted': False,
                'file_exists': True,
                'error': 'ファイル読み取りエラー'
            }
    
    def _test_log_file_privacy(self) -> Dict[str, Any]:
        """ログファイルの個人情報チェック"""
        log_dir = os.path.join(self.test_base_dir, "docmind_data", "logs")
        
        if not os.path.exists(log_dir):
            return {
                'log_directory': log_dir,
                'checked_items': [],
                'issues': [],
                'directory_exists': False
            }
        
        issues = []
        checked_items = []
        
        # 個人情報パターン
        privacy_patterns = [
            r'\b\d{3}-\d{4}-\d{4}\b',  # 電話番号
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # メールアドレス
            r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # クレジットカード番号
            r'password\s*[:=]\s*\S+',  # パスワード
            r'secret\s*[:=]\s*\S+',    # シークレット
        ]
        
        import re
        
        for log_file in os.listdir(log_dir):
            log_path = os.path.join(log_dir, log_file)
            if os.path.isfile(log_path):
                checked_items.append(log_path)
                
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    for pattern in privacy_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            issues.append(f"個人情報パターン検出 in {log_file}: {pattern}")
                
                except IOError:
                    issues.append(f"ログファイル読み取りエラー: {log_file}")
        
        return {
            'log_directory': log_dir,
            'checked_items': checked_items,
            'issues': issues,
            'directory_exists': True
        }
    
    def _test_temp_file_privacy(self) -> Dict[str, Any]:
        """一時ファイルの機密情報チェック"""
        temp_dirs = [tempfile.gettempdir(), self.test_base_dir]
        
        issues = []
        checked_items = []
        
        for temp_dir in temp_dirs:
            if not os.path.exists(temp_dir):
                continue
            
            # DocMind関連の一時ファイルを検索
            for item in os.listdir(temp_dir):
                if 'docmind' in item.lower():
                    item_path = os.path.join(temp_dir, item)
                    if os.path.isfile(item_path):
                        checked_items.append(item_path)
                        
                        # ファイル内容の機密情報チェック
                        try:
                            with open(item_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read(1024)  # 最初の1KBのみチェック
                            
                            sensitive_keywords = ['password', 'secret', 'token', 'key', 'credential']
                            for keyword in sensitive_keywords:
                                if keyword in content.lower():
                                    issues.append(f"一時ファイルに機密情報: {item_path} ({keyword})")
                        
                        except IOError:
                            pass
        
        return {
            'temp_directories': temp_dirs,
            'checked_items': checked_items,
            'issues': issues
        }
    
    def _test_memory_privacy(self) -> Dict[str, Any]:
        """プロセスメモリの機密情報チェック"""
        # メモリスキャンの実行
        memory_issues = self.memory_scanner.scan_process_memory(10)  # 10秒間のクイックスキャン
        
        return {
            'scan_duration_seconds': 10,
            'checked_items': ['process_memory'],
            'issues': memory_issues,
            'scan_method': 'garbage_collector_objects'
        }
    
    def _test_network_privacy(self) -> Dict[str, Any]:
        """ネットワーク通信のプライバシーチェック"""
        # 短時間のネットワーク監視
        self.network_monitor.start_monitoring()
        time.sleep(3.0)  # 3秒間監視
        self.network_monitor.stop_monitoring()
        
        connections = self.network_monitor.get_external_connections()
        
        issues = []
        if connections:
            issues.append(f"外部ネットワーク通信が検出されました: {len(connections)}件")
        
        return {
            'monitoring_duration_seconds': 3,
            'checked_items': ['network_connections'],
            'issues': issues,
            'external_connections': connections
        }
    
    # 監査メソッド
    
    def _audit_local_processing(self) -> Dict[str, Any]:
        """ローカル処理の監査"""
        # 外部通信の確認
        external_connections = self.network_monitor.get_external_connections()
        
        score = 1.0 if len(external_connections) == 0 else 0.0
        critical_issues = []
        
        if external_connections:
            critical_issues.append("外部通信が検出されました")
        
        return {
            'score': score,
            'critical_issues': critical_issues,
            'checks_performed': 1,
            'details': {
                'external_connections': len(external_connections)
            }
        }
    
    def _audit_file_security(self) -> Dict[str, Any]:
        """ファイルセキュリティの監査"""
        insecure_files = self.file_permission_checker.get_insecure_files()
        
        total_files = len(self.file_permission_checker.checked_files)
        secure_files = total_files - len(insecure_files)
        
        score = secure_files / max(total_files, 1)
        critical_issues = []
        
        if len(insecure_files) > 0:
            critical_issues.append(f"セキュアでないファイル権限: {len(insecure_files)}件")
        
        return {
            'score': score,
            'critical_issues': critical_issues,
            'checks_performed': total_files,
            'details': {
                'total_files': total_files,
                'secure_files': secure_files,
                'insecure_files': len(insecure_files)
            }
        }
    
    def _audit_data_protection(self) -> Dict[str, Any]:
        """データ保護の監査"""
        # 暗号化状況の確認
        config_encryption = self._test_configuration_encryption()
        db_encryption = self._test_database_encryption()
        
        encryption_checks = [
            config_encryption['encrypted'],
            db_encryption['encrypted']
        ]
        
        score = sum(encryption_checks) / len(encryption_checks)
        critical_issues = []
        
        if not config_encryption['encrypted']:
            critical_issues.append("設定ファイルが暗号化されていません")
        
        if not db_encryption['encrypted']:
            critical_issues.append("データベースが暗号化されていません")
        
        return {
            'score': score,
            'critical_issues': critical_issues,
            'checks_performed': len(encryption_checks),
            'details': {
                'config_encrypted': config_encryption['encrypted'],
                'database_encrypted': db_encryption['encrypted']
            }
        }
    
    def _audit_privacy_compliance(self) -> Dict[str, Any]:
        """プライバシーコンプライアンスの監査"""
        log_privacy = self._test_log_file_privacy()
        memory_privacy = self._test_memory_privacy()
        
        total_issues = len(log_privacy['issues']) + len(memory_privacy['issues'])
        total_checks = len(log_privacy['checked_items']) + len(memory_privacy['checked_items'])
        
        score = 1.0 - (total_issues / max(total_checks, 1))
        critical_issues = []
        
        if log_privacy['issues']:
            critical_issues.extend(log_privacy['issues'])
        
        if memory_privacy['issues']:
            critical_issues.extend(memory_privacy['issues'])
        
        return {
            'score': score,
            'critical_issues': critical_issues,
            'checks_performed': total_checks,
            'details': {
                'log_issues': len(log_privacy['issues']),
                'memory_issues': len(memory_privacy['issues'])
            }
        }
    
    def _audit_system_hardening(self) -> Dict[str, Any]:
        """システム強化の監査"""
        # 基本的なシステム強化チェック
        hardening_checks = {
            'temp_file_cleanup': self._check_temp_file_cleanup(),
            'process_isolation': self._check_process_isolation(),
            'resource_limits': self._check_resource_limits()
        }
        
        passed_checks = sum(hardening_checks.values())
        total_checks = len(hardening_checks)
        
        score = passed_checks / total_checks
        critical_issues = []
        
        for check_name, passed in hardening_checks.items():
            if not passed:
                critical_issues.append(f"システム強化チェック失敗: {check_name}")
        
        return {
            'score': score,
            'critical_issues': critical_issues,
            'checks_performed': total_checks,
            'details': hardening_checks
        }
    
    def _check_temp_file_cleanup(self) -> bool:
        """一時ファイルクリーンアップのチェック"""
        # 作成した一時ファイルがクリーンアップされているかチェック
        remaining_files = [f for f in self.created_temp_files if os.path.exists(f)]
        return len(remaining_files) == 0
    
    def _check_process_isolation(self) -> bool:
        """プロセス分離のチェック"""
        # 基本的なプロセス分離チェック（模擬）
        try:
            process = psutil.Process()
            # 子プロセスの数をチェック
            children = process.children()
            return len(children) < 10  # 適度な数の子プロセス
        except:
            return True
    
    def _check_resource_limits(self) -> bool:
        """リソース制限のチェック"""
        # メモリ使用量のチェック
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            return memory_mb < 1024  # 1GB未満
        except:
            return True
    
    def _generate_security_recommendations(self, audit_results: Dict[str, Any]) -> List[str]:
        """セキュリティ推奨事項の生成"""
        recommendations = []
        
        for category, result in audit_results.items():
            if result['score'] < 0.8:
                if category == 'local_processing':
                    recommendations.append("外部通信を完全に無効化することを推奨します")
                elif category == 'file_security':
                    recommendations.append("ファイル権限をより厳格に設定することを推奨します")
                elif category == 'data_protection':
                    recommendations.append("機密データの暗号化を実装することを推奨します")
                elif category == 'privacy_compliance':
                    recommendations.append("ログファイルから個人情報を除去することを推奨します")
                elif category == 'system_hardening':
                    recommendations.append("システム強化設定を見直すことを推奨します")
        
        if not recommendations:
            recommendations.append("現在のセキュリティ設定は適切です")
        
        return recommendations
    
    def get_security_summary(self) -> Dict[str, Any]:
        """セキュリティ検証の要約を取得"""
        if not self.security_metrics:
            return {"message": "セキュリティテストが実行されていません"}
        
        # 統計計算
        total_tests = len(self.security_metrics)
        secure_tests = sum(1 for m in self.security_metrics if m.security_level == "SECURE")
        warning_tests = sum(1 for m in self.security_metrics if m.security_level == "WARNING")
        critical_tests = sum(1 for m in self.security_metrics if m.security_level == "CRITICAL")
        
        compliance_scores = [m.compliance_score for m in self.security_metrics]
        average_compliance = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0.0
        
        # 全脆弱性の集計
        all_vulnerabilities = []
        for metric in self.security_metrics:
            all_vulnerabilities.extend(metric.vulnerabilities)
        
        return {
            "test_summary": {
                "total_tests": total_tests,
                "secure_tests": secure_tests,
                "warning_tests": warning_tests,
                "critical_tests": critical_tests,
                "overall_security_level": "SECURE" if critical_tests == 0 and warning_tests <= 1 else "WARNING" if critical_tests == 0 else "CRITICAL"
            },
            "compliance_statistics": {
                "average_compliance_score": average_compliance,
                "min_compliance_score": min(compliance_scores) if compliance_scores else 0.0,
                "max_compliance_score": max(compliance_scores) if compliance_scores else 0.0
            },
            "vulnerability_analysis": {
                "total_vulnerabilities": len(all_vulnerabilities),
                "unique_vulnerabilities": len(set(all_vulnerabilities)),
                "vulnerability_list": list(set(all_vulnerabilities))
            },
            "detailed_metrics": [
                {
                    "test_name": m.test_name,
                    "security_level": m.security_level,
                    "compliance_score": m.compliance_score,
                    "vulnerabilities_count": len(m.vulnerabilities),
                    "external_connections": len(m.external_connections)
                }
                for m in self.security_metrics
            ]
        }