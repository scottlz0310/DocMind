"""
互換性・移植性検証クラス

DocMindアプリケーションの環境互換性を包括的に検証します。
Windows 10/11環境での全機能動作、異なる画面解像度とファイルシステムでの動作、
異なる文字エンコーディングファイルの処理、限定リソース環境での動作を検証します。
"""

import gc
import locale
import logging
import os
import platform
import shutil
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import psutil

# DocMindコンポーネントのインポート
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from .base_validator import BaseValidator, ValidationConfig, ValidationResult
    from .memory_monitor import MemoryMonitor
    from .performance_monitor import PerformanceMonitor
    from .statistics_collector import StatisticsCollector
    from .test_data_generator import TestDataGenerator, TestDatasetConfig
except ImportError:
    from base_validator import BaseValidator, ValidationConfig
    from test_data_generator import TestDataGenerator

from src.core.document_processor import DocumentProcessor
from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.core.search_manager import SearchManager
from src.data.models import SearchQuery, SearchType
from src.utils.config import Config


@dataclass
class CompatibilityThresholds:
    """互換性検証の閾値設定"""
    min_windows_version: str = "10.0"                    # 最小Windows版本
    max_startup_time_seconds: float = 15.0               # 最大起動時間（秒）
    min_memory_mb: int = 512                             # 最小メモリ要件（MB）
    max_memory_usage_mb: int = 2048                      # 最大メモリ使用量（MB）
    min_disk_space_mb: int = 1024                        # 最小ディスク容量（MB）
    max_search_time_seconds: float = 10.0                # 最大検索時間（秒）
    supported_encodings: list[str] = field(default_factory=lambda: [
        'utf-8', 'shift_jis', 'euc-jp', 'iso-2022-jp', 'cp932'
    ])
    min_screen_resolution: tuple[int, int] = (1024, 768) # 最小画面解像度
    supported_filesystems: list[str] = field(default_factory=lambda: [
        'NTFS', 'FAT32', 'exFAT'
    ])


@dataclass
class CompatibilityMetrics:
    """互換性測定結果"""
    test_name: str
    compatibility_level: str  # "COMPATIBLE", "LIMITED", "INCOMPATIBLE"
    os_version: str = ""
    python_version: str = ""
    memory_available_mb: int = 0
    disk_space_available_mb: int = 0
    screen_resolution: tuple[int, int] = (0, 0)
    filesystem_type: str = ""
    encoding_support: dict[str, bool] = field(default_factory=dict)
    feature_compatibility: dict[str, bool] = field(default_factory=dict)
    performance_metrics: dict[str, float] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    additional_details: dict[str, Any] = field(default_factory=dict)


class SystemInfoCollector:
    """システム情報収集クラス"""

    def __init__(self):
        self.system_info: dict[str, Any] = {}

    def collect_system_info(self) -> dict[str, Any]:
        """システム情報の収集"""
        try:
            # OS情報
            self.system_info['os_name'] = platform.system()
            self.system_info['os_version'] = platform.version()
            self.system_info['os_release'] = platform.release()
            self.system_info['machine'] = platform.machine()
            self.system_info['processor'] = platform.processor()

            # Python情報
            self.system_info['python_version'] = platform.python_version()
            self.system_info['python_implementation'] = platform.python_implementation()

            # メモリ情報
            memory = psutil.virtual_memory()
            self.system_info['total_memory_mb'] = memory.total // (1024 * 1024)
            self.system_info['available_memory_mb'] = memory.available // (1024 * 1024)
            self.system_info['memory_percent'] = memory.percent

            # ディスク情報
            disk = psutil.disk_usage('/')
            self.system_info['total_disk_mb'] = disk.total // (1024 * 1024)
            self.system_info['free_disk_mb'] = disk.free // (1024 * 1024)
            self.system_info['disk_percent'] = (disk.used / disk.total) * 100

            # CPU情報
            self.system_info['cpu_count'] = psutil.cpu_count()
            self.system_info['cpu_count_logical'] = psutil.cpu_count(logical=True)
            self.system_info['cpu_freq'] = psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}

            # ロケール情報
            self.system_info['locale'] = locale.getdefaultlocale()
            self.system_info['encoding'] = locale.getpreferredencoding()

            return self.system_info

        except Exception as e:
            return {'error': str(e)}

    def get_windows_version(self) -> tuple[str, bool]:
        """Windows版本の取得と対応状況の確認"""
        try:
            if platform.system() != 'Windows':
                return "非Windows", False

            version = platform.version()
            release = platform.release()

            # Windows 10/11の判定
            if release == "10":
                # ビルド番号でWindows 11を判定
                build_number = int(version.split('.')[-1]) if '.' in version else 0
                if build_number >= 22000:
                    return "Windows 11", True
                else:
                    return "Windows 10", True
            elif release == "11":
                return "Windows 11", True
            else:
                return f"Windows {release}", False

        except Exception as e:
            return f"不明 ({str(e)})", False

    def get_filesystem_type(self, path: str = None) -> str:
        """ファイルシステムタイプの取得"""
        try:
            if path is None:
                path = os.getcwd()

            if platform.system() == 'Windows':
                # Windowsでのファイルシステム判定
                import ctypes
                drive = os.path.splitdrive(path)[0] + '\\'

                # GetVolumeInformation APIを使用
                volume_name_buffer = ctypes.create_unicode_buffer(1024)
                file_system_name_buffer = ctypes.create_unicode_buffer(1024)

                result = ctypes.windll.kernel32.GetVolumeInformationW(
                    ctypes.c_wchar_p(drive),
                    volume_name_buffer,
                    ctypes.sizeof(volume_name_buffer),
                    None, None, None,
                    file_system_name_buffer,
                    ctypes.sizeof(file_system_name_buffer)
                )

                if result:
                    return file_system_name_buffer.value
                else:
                    return "不明"
            else:
                # 非Windowsの場合
                return "非Windows"

        except Exception as e:
            return f"エラー: {str(e)}"


class EncodingTester:
    """文字エンコーディングテストクラス"""

    def __init__(self):
        self.test_strings = {
            'japanese_hiragana': 'これはひらがなのテストです',
            'japanese_katakana': 'コレハカタカナノテストデス',
            'japanese_kanji': '日本語漢字文字化けテスト',
            'japanese_mixed': '日本語ひらがなカタカナ漢字MIXテスト123',
            'special_chars': '①②③④⑤⑥⑦⑧⑨⑩',
            'symbols': '※◆■□○●△▲▼▽',
            'ascii': 'ASCII English Test 123',
            'unicode_emoji': '😀😃😄😁😆😅😂🤣'
        }

    def test_encoding_support(self, encodings: list[str]) -> dict[str, dict[str, bool]]:
        """エンコーディングサポートのテスト"""
        results = {}

        for encoding in encodings:
            encoding_results = {}

            for test_name, test_string in self.test_strings.items():
                try:
                    # エンコード・デコードテスト
                    encoded = test_string.encode(encoding)
                    decoded = encoded.decode(encoding)

                    # 元の文字列と一致するかチェック
                    encoding_results[test_name] = (decoded == test_string)

                except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
                    encoding_results[test_name] = False

            results[encoding] = encoding_results

        return results

    def create_test_files_with_encodings(self, base_dir: str, encodings: list[str]) -> list[str]:
        """異なるエンコーディングのテストファイルを作成"""
        test_files = []

        for encoding in encodings:
            for test_name, test_string in self.test_strings.items():
                try:
                    filename = f"test_{encoding}_{test_name}.txt"
                    filepath = os.path.join(base_dir, filename)

                    with open(filepath, 'w', encoding=encoding) as f:
                        f.write(f"エンコーディング: {encoding}\n")
                        f.write(f"テストタイプ: {test_name}\n")
                        f.write(f"内容: {test_string}\n")
                        f.write("追加テキスト: DocMind互換性テスト用ファイル\n")

                    test_files.append(filepath)

                except (UnicodeEncodeError, LookupError):
                    # サポートされていないエンコーディングはスキップ
                    continue

        return test_files


class ResourceLimiter:
    """リソース制限テストクラス"""

    def __init__(self):
        self.original_limits = {}

    def simulate_limited_memory(self, limit_mb: int) -> None:
        """メモリ制限のシミュレーション"""
        # 実際のメモリ制限は困難なため、監視ベースでシミュレート
        self.memory_limit_mb = limit_mb
        self.memory_monitor_active = True

        # メモリ監視スレッドを開始
        self.memory_thread = threading.Thread(target=self._monitor_memory_usage)
        self.memory_thread.daemon = True
        self.memory_thread.start()

    def _monitor_memory_usage(self) -> None:
        """メモリ使用量の監視"""
        while getattr(self, 'memory_monitor_active', False):
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss // (1024 * 1024)

                if memory_mb > self.memory_limit_mb:
                    # メモリ制限を超えた場合の警告
                    logging.warning(f"メモリ制限超過: {memory_mb}MB > {self.memory_limit_mb}MB")

                time.sleep(1.0)

            except Exception:
                break

    def simulate_limited_disk_space(self, temp_dir: str, limit_mb: int) -> str:
        """ディスク容量制限のシミュレーション"""
        # 制限容量に近いダミーファイルを作成してディスク容量を制限
        dummy_file = os.path.join(temp_dir, "disk_limit_dummy.dat")

        try:
            # 利用可能容量を取得
            disk_usage = shutil.disk_usage(temp_dir)
            available_mb = disk_usage.free // (1024 * 1024)

            # 制限容量を超える分のダミーファイルを作成
            if available_mb > limit_mb:
                dummy_size_mb = available_mb - limit_mb
                dummy_size_mb * 1024 * 1024

                with open(dummy_file, 'wb') as f:
                    # 1MBずつ書き込み
                    chunk_size = 1024 * 1024
                    for _ in range(dummy_size_mb):
                        f.write(b'0' * chunk_size)

                return dummy_file

        except Exception as e:
            logging.warning(f"ディスク容量制限シミュレーションに失敗: {e}")

        return ""

    def cleanup_resource_limits(self) -> None:
        """リソース制限のクリーンアップ"""
        self.memory_monitor_active = False

        if hasattr(self, 'memory_thread'):
            self.memory_thread.join(timeout=2.0)


class CompatibilityValidator(BaseValidator):
    """
    互換性・移植性検証クラス

    DocMindアプリケーションの環境互換性を包括的に検証します。
    """

    def __init__(self, config: ValidationConfig | None = None):
        """
        互換性検証クラスの初期化

        Args:
            config: 検証設定
        """
        super().__init__(config)

        # 互換性閾値の設定
        self.thresholds = CompatibilityThresholds()

        # システム情報収集・テストコンポーネント
        self.system_info_collector = SystemInfoCollector()
        self.encoding_tester = EncodingTester()
        self.resource_limiter = ResourceLimiter()

        # テストデータ生成器
        self.data_generator = TestDataGenerator()

        # 測定結果の保存
        self.compatibility_metrics: list[CompatibilityMetrics] = []

        # テスト環境
        self.test_base_dir: str | None = None
        self.test_components: dict[str, Any] = {}
        self.created_test_files: list[str] = []

        self.logger.info("CompatibilityValidatorを初期化しました")

    def setup_test_environment(self) -> None:
        """テスト環境のセットアップ"""
        self.logger.info("互換性テスト環境をセットアップします")

        # 一時ディレクトリの作成
        self.test_base_dir = tempfile.mkdtemp(prefix="docmind_compatibility_test_")
        self.logger.info(f"テストディレクトリ: {self.test_base_dir}")

        # システム情報の収集
        system_info = self.system_info_collector.collect_system_info()
        self.logger.info(f"システム情報: {system_info}")

        # DocMindコンポーネントの初期化
        self._setup_docmind_components()

        # テストデータ生成器の設定
        self.data_generator.setup_test_environment(self.test_base_dir)

        self.logger.info("互換性テスト環境のセットアップが完了しました")

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
        self.logger.info("互換性テスト環境をクリーンアップします")

        try:
            # リソース制限のクリーンアップ
            self.resource_limiter.cleanup_resource_limits()

            # 作成したテストファイルの削除
            for test_file in self.created_test_files:
                try:
                    if os.path.exists(test_file):
                        os.remove(test_file)
                except OSError:
                    pass

            # コンポーネントのクリーンアップ
            for _component_name, component in self.test_components.items():
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

        self.logger.info("互換性テスト環境のクリーンアップが完了しました")

    def test_windows_environment_compatibility(self) -> None:
        """Windows 10/11環境での全機能動作検証"""
        self.logger.info("Windows 10/11環境での全機能動作を検証します")

        # システム情報の収集
        system_info = self.system_info_collector.collect_system_info()

        # Windows版本の確認
        windows_version, is_supported = self.system_info_collector.get_windows_version()

        # 基本システム要件の確認
        memory_mb = system_info.get('available_memory_mb', 0)
        disk_mb = system_info.get('free_disk_mb', 0)

        # DocMind全機能のテスト
        feature_test_results = self._test_all_docmind_features()

        # パフォーマンステスト
        performance_results = self._test_windows_performance()

        # 互換性レベルの判定
        compatibility_issues = []

        if not is_supported:
            compatibility_issues.append(f"サポートされていないWindows版本: {windows_version}")

        if memory_mb < self.thresholds.min_memory_mb:
            compatibility_issues.append(f"メモリ不足: {memory_mb}MB < {self.thresholds.min_memory_mb}MB")

        if disk_mb < self.thresholds.min_disk_space_mb:
            compatibility_issues.append(f"ディスク容量不足: {disk_mb}MB < {self.thresholds.min_disk_space_mb}MB")

        # 機能テスト結果の評価
        failed_features = [
            feature for feature, success in feature_test_results.items()
            if not success
        ]

        if failed_features:
            compatibility_issues.extend([f"機能テスト失敗: {feature}" for feature in failed_features])

        # 互換性レベルの決定
        if len(compatibility_issues) == 0:
            compatibility_level = "COMPATIBLE"
        elif len(compatibility_issues) <= 2:
            compatibility_level = "LIMITED"
        else:
            compatibility_level = "INCOMPATIBLE"

        # 互換性メトリクスの作成
        metrics = CompatibilityMetrics(
            test_name="windows_environment_compatibility",
            compatibility_level=compatibility_level,
            os_version=windows_version,
            python_version=system_info.get('python_version', '不明'),
            memory_available_mb=memory_mb,
            disk_space_available_mb=disk_mb,
            feature_compatibility=feature_test_results,
            performance_metrics=performance_results,
            limitations=compatibility_issues,
            recommendations=self._generate_windows_recommendations(compatibility_issues),
            additional_details={
                'system_info': system_info,
                'windows_supported': is_supported,
                'total_features_tested': len(feature_test_results),
                'failed_features_count': len(failed_features)
            }
        )

        self.compatibility_metrics.append(metrics)

        # 要件の検証
        self.assert_condition(
            compatibility_level != "INCOMPATIBLE",
            f"Windows環境で互換性なし: {compatibility_issues}"
        )

        self.logger.info(f"Windows環境互換性検証完了 - レベル: {compatibility_level}")

    def test_screen_resolution_filesystem_compatibility(self) -> None:
        """異なる画面解像度とファイルシステムでの動作検証"""
        self.logger.info("画面解像度とファイルシステムでの動作を検証します")

        # 現在の画面解像度の取得（模擬）
        current_resolution = self._get_screen_resolution()

        # ファイルシステムタイプの取得
        filesystem_type = self.system_info_collector.get_filesystem_type(self.test_base_dir)

        # 解像度互換性テスト
        resolution_test_results = self._test_resolution_compatibility(current_resolution)

        # ファイルシステム互換性テスト
        filesystem_test_results = self._test_filesystem_compatibility(filesystem_type)

        # GUI表示テスト（模擬）
        gui_test_results = self._test_gui_display_compatibility()

        # 互換性問題の評価
        compatibility_issues = []

        # 解像度チェック
        min_width, min_height = self.thresholds.min_screen_resolution
        if current_resolution[0] < min_width or current_resolution[1] < min_height:
            compatibility_issues.append(
                f"画面解像度不足: {current_resolution} < {self.thresholds.min_screen_resolution}"
            )

        # ファイルシステムチェック
        if filesystem_type not in self.thresholds.supported_filesystems:
            compatibility_issues.append(f"サポートされていないファイルシステム: {filesystem_type}")

        # テスト結果の評価
        failed_tests = []
        if not resolution_test_results.get('ui_scaling', True):
            failed_tests.append("UI スケーリング")
        if not filesystem_test_results.get('file_operations', True):
            failed_tests.append("ファイル操作")
        if not gui_test_results.get('display_accuracy', True):
            failed_tests.append("GUI表示")

        if failed_tests:
            compatibility_issues.extend([f"テスト失敗: {test}" for test in failed_tests])

        # 互換性レベルの決定
        if len(compatibility_issues) == 0:
            compatibility_level = "COMPATIBLE"
        elif len(compatibility_issues) <= 2:
            compatibility_level = "LIMITED"
        else:
            compatibility_level = "INCOMPATIBLE"

        # 互換性メトリクスの作成
        metrics = CompatibilityMetrics(
            test_name="screen_resolution_filesystem_compatibility",
            compatibility_level=compatibility_level,
            screen_resolution=current_resolution,
            filesystem_type=filesystem_type,
            feature_compatibility={
                'resolution_scaling': resolution_test_results.get('ui_scaling', False),
                'filesystem_operations': filesystem_test_results.get('file_operations', False),
                'gui_display': gui_test_results.get('display_accuracy', False)
            },
            limitations=compatibility_issues,
            recommendations=self._generate_display_filesystem_recommendations(
                current_resolution, filesystem_type, compatibility_issues
            ),
            additional_details={
                'resolution_test_details': resolution_test_results,
                'filesystem_test_details': filesystem_test_results,
                'gui_test_details': gui_test_results,
                'supported_filesystems': self.thresholds.supported_filesystems,
                'min_resolution': self.thresholds.min_screen_resolution
            }
        )

        self.compatibility_metrics.append(metrics)

        # 要件の検証
        self.assert_condition(
            compatibility_level != "INCOMPATIBLE",
            f"画面解像度・ファイルシステム互換性なし: {compatibility_issues}"
        )

        self.logger.info(f"画面解像度・ファイルシステム互換性検証完了 - レベル: {compatibility_level}")

    def test_character_encoding_compatibility(self) -> None:
        """異なる文字エンコーディングファイルの処理検証"""
        self.logger.info("異なる文字エンコーディングファイルの処理を検証します")

        # エンコーディングサポートテスト
        encoding_support_results = self.encoding_tester.test_encoding_support(
            self.thresholds.supported_encodings
        )

        # 異なるエンコーディングのテストファイル作成
        test_files = self.encoding_tester.create_test_files_with_encodings(
            self.test_base_dir, self.thresholds.supported_encodings
        )
        self.created_test_files.extend(test_files)

        # DocMindでのファイル処理テスト
        processing_results = self._test_encoding_file_processing(test_files)

        # 検索機能でのエンコーディングテスト
        search_results = self._test_encoding_search_functionality(test_files)

        # エンコーディング互換性の評価
        encoding_compatibility = {}
        encoding_issues = []

        for encoding in self.thresholds.supported_encodings:
            # 基本サポート
            basic_support = encoding_support_results.get(encoding, {})
            support_rate = sum(basic_support.values()) / len(basic_support) if basic_support else 0.0

            # ファイル処理サポート
            processing_support = processing_results.get(encoding, {})
            processing_rate = sum(processing_support.values()) / len(processing_support) if processing_support else 0.0

            # 検索サポート
            search_support = search_results.get(encoding, {})
            search_rate = sum(search_support.values()) / len(search_support) if search_support else 0.0

            # 総合サポート率
            overall_rate = (support_rate + processing_rate + search_rate) / 3.0
            encoding_compatibility[encoding] = overall_rate >= 0.8

            if overall_rate < 0.8:
                encoding_issues.append(f"エンコーディング {encoding} のサポート不完全: {overall_rate:.2f}")

        # 互換性レベルの決定
        supported_encodings = sum(encoding_compatibility.values())
        total_encodings = len(encoding_compatibility)

        if supported_encodings == total_encodings:
            compatibility_level = "COMPATIBLE"
        elif supported_encodings >= total_encodings * 0.7:
            compatibility_level = "LIMITED"
        else:
            compatibility_level = "INCOMPATIBLE"

        # 互換性メトリクスの作成
        metrics = CompatibilityMetrics(
            test_name="character_encoding_compatibility",
            compatibility_level=compatibility_level,
            encoding_support=encoding_compatibility,
            feature_compatibility={
                'basic_encoding_support': sum(encoding_compatibility.values()) / len(encoding_compatibility),
                'file_processing_support': len([r for r in processing_results.values() if any(r.values())]) / len(processing_results) if processing_results else 0,
                'search_functionality_support': len([r for r in search_results.values() if any(r.values())]) / len(search_results) if search_results else 0
            },
            limitations=encoding_issues,
            recommendations=self._generate_encoding_recommendations(encoding_issues),
            additional_details={
                'encoding_support_details': encoding_support_results,
                'processing_results': processing_results,
                'search_results': search_results,
                'test_files_created': len(test_files),
                'supported_encodings_list': self.thresholds.supported_encodings
            }
        )

        self.compatibility_metrics.append(metrics)

        # 要件の検証
        self.assert_condition(
            compatibility_level != "INCOMPATIBLE",
            f"文字エンコーディング互換性なし: {encoding_issues}"
        )

        self.logger.info(f"文字エンコーディング互換性検証完了 - レベル: {compatibility_level}")

    def test_limited_resource_environment_compatibility(self) -> None:
        """限定リソース環境での動作検証"""
        self.logger.info("限定リソース環境での動作を検証します")

        # 現在のリソース状況を記録
        original_memory = psutil.virtual_memory().available // (1024 * 1024)
        original_disk = shutil.disk_usage(self.test_base_dir).free // (1024 * 1024)

        # リソース制限テストの実行
        resource_test_results = {}

        # 1. 低メモリ環境でのテスト
        self.logger.info("低メモリ環境でのテストを実行します")
        low_memory_results = self._test_low_memory_environment()
        resource_test_results['low_memory'] = low_memory_results

        # 2. 低ディスク容量環境でのテスト
        self.logger.info("低ディスク容量環境でのテストを実行します")
        low_disk_results = self._test_low_disk_environment()
        resource_test_results['low_disk'] = low_disk_results

        # 3. 低CPU環境でのテスト（模擬）
        self.logger.info("低CPU環境でのテストを実行します")
        low_cpu_results = self._test_low_cpu_environment()
        resource_test_results['low_cpu'] = low_cpu_results

        # 4. 複合制限環境でのテスト
        self.logger.info("複合制限環境でのテストを実行します")
        combined_limits_results = self._test_combined_resource_limits()
        resource_test_results['combined_limits'] = combined_limits_results

        # リソース制限互換性の評価
        resource_issues = []

        # 各テスト結果の評価
        for test_name, results in resource_test_results.items():
            if not results.get('basic_functionality', True):
                resource_issues.append(f"{test_name}: 基本機能が動作しない")

            if not results.get('acceptable_performance', True):
                resource_issues.append(f"{test_name}: パフォーマンスが許容範囲外")

            if results.get('critical_errors', []):
                resource_issues.extend([f"{test_name}: {error}" for error in results['critical_errors']])

        # 互換性レベルの決定
        if len(resource_issues) == 0:
            compatibility_level = "COMPATIBLE"
        elif len(resource_issues) <= 3:
            compatibility_level = "LIMITED"
        else:
            compatibility_level = "INCOMPATIBLE"

        # パフォーマンスメトリクスの集計
        performance_metrics = {}
        for test_name, results in resource_test_results.items():
            if 'performance_metrics' in results:
                for metric, value in results['performance_metrics'].items():
                    performance_metrics[f"{test_name}_{metric}"] = value

        # 互換性メトリクスの作成
        metrics = CompatibilityMetrics(
            test_name="limited_resource_environment_compatibility",
            compatibility_level=compatibility_level,
            memory_available_mb=original_memory,
            disk_space_available_mb=original_disk,
            feature_compatibility={
                'low_memory_operation': resource_test_results['low_memory'].get('basic_functionality', False),
                'low_disk_operation': resource_test_results['low_disk'].get('basic_functionality', False),
                'low_cpu_operation': resource_test_results['low_cpu'].get('basic_functionality', False),
                'combined_limits_operation': resource_test_results['combined_limits'].get('basic_functionality', False)
            },
            performance_metrics=performance_metrics,
            limitations=resource_issues,
            recommendations=self._generate_resource_recommendations(resource_issues, resource_test_results),
            additional_details={
                'resource_test_details': resource_test_results,
                'original_memory_mb': original_memory,
                'original_disk_mb': original_disk,
                'test_scenarios': ['low_memory', 'low_disk', 'low_cpu', 'combined_limits']
            }
        )

        self.compatibility_metrics.append(metrics)

        # 要件の検証
        self.assert_condition(
            compatibility_level != "INCOMPATIBLE",
            f"限定リソース環境で互換性なし: {resource_issues}"
        )

        self.logger.info(f"限定リソース環境互換性検証完了 - レベル: {compatibility_level}")

    def test_comprehensive_compatibility_audit(self) -> None:
        """包括的互換性監査の実行"""
        self.logger.info("包括的互換性監査を実行します")

        # 全互換性テストの統合実行
        audit_results = {
            'system_compatibility': self._audit_system_compatibility(),
            'feature_compatibility': self._audit_feature_compatibility(),
            'performance_compatibility': self._audit_performance_compatibility(),
            'resource_compatibility': self._audit_resource_compatibility(),
            'environment_compatibility': self._audit_environment_compatibility()
        }

        # 総合互換性スコアの計算
        category_scores = [result['score'] for result in audit_results.values()]
        overall_score = sum(category_scores) / len(category_scores)

        # 重大な互換性問題の集計
        critical_issues = []
        for _category, result in audit_results.items():
            critical_issues.extend(result.get('critical_issues', []))

        # 互換性レベルの判定
        if overall_score >= 0.9:
            compatibility_level = "COMPATIBLE"
        elif overall_score >= 0.7:
            compatibility_level = "LIMITED"
        else:
            compatibility_level = "INCOMPATIBLE"

        # システム情報の収集
        system_info = self.system_info_collector.collect_system_info()
        windows_version, _ = self.system_info_collector.get_windows_version()

        # 互換性メトリクスの作成
        metrics = CompatibilityMetrics(
            test_name="comprehensive_compatibility_audit",
            compatibility_level=compatibility_level,
            os_version=windows_version,
            python_version=system_info.get('python_version', '不明'),
            memory_available_mb=system_info.get('available_memory_mb', 0),
            disk_space_available_mb=system_info.get('free_disk_mb', 0),
            feature_compatibility={
                category: result['score'] >= 0.8
                for category, result in audit_results.items()
            },
            limitations=critical_issues,
            recommendations=self._generate_comprehensive_recommendations(audit_results),
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
                'overall_compatibility_score': overall_score,
                'system_info': system_info
            }
        )

        self.compatibility_metrics.append(metrics)

        # 要件の検証
        self.assert_condition(
            overall_score >= 0.7,
            f"包括的互換性監査で不合格: スコア {overall_score:.2f} < 0.7"
        )

        self.assert_condition(
            len(critical_issues) == 0,
            f"重大な互換性問題が検出されました: {critical_issues}"
        )

        self.logger.info(f"包括的互換性監査完了 - 総合スコア: {overall_score:.2f}")

    # ヘルパーメソッド

    def _test_all_docmind_features(self) -> dict[str, bool]:
        """DocMind全機能のテスト"""
        feature_results = {}

        try:
            # ドキュメント処理機能
            feature_results['document_processing'] = self._test_document_processing_feature()

            # インデックス機能
            feature_results['indexing'] = self._test_indexing_feature()

            # 検索機能
            feature_results['search'] = self._test_search_feature()

            # 埋め込み機能
            feature_results['embedding'] = self._test_embedding_feature()

            # GUI機能（模擬）
            feature_results['gui'] = self._test_gui_feature()

        except Exception as e:
            self.logger.error(f"機能テスト中にエラー: {e}")
            # エラーが発生した機能はFalseに設定
            for feature in ['document_processing', 'indexing', 'search', 'embedding', 'gui']:
                if feature not in feature_results:
                    feature_results[feature] = False

        return feature_results

    def _test_document_processing_feature(self) -> bool:
        """ドキュメント処理機能のテスト"""
        try:
            document_processor = self.test_components['document_processor']

            # テストファイルの作成
            test_file = os.path.join(self.test_base_dir, "test_document.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("これはドキュメント処理のテストファイルです。")

            # ドキュメント処理の実行
            document = document_processor.process_file(test_file)

            return document is not None and len(document.content) > 0

        except Exception as e:
            self.logger.error(f"ドキュメント処理テストエラー: {e}")
            return False

    def _test_indexing_feature(self) -> bool:
        """インデックス機能のテスト"""
        try:
            index_manager = self.test_components['index_manager']
            document_processor = self.test_components['document_processor']

            # テストドキュメントの処理とインデックス化
            test_file = os.path.join(self.test_base_dir, "test_index.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("インデックステスト用ドキュメント")

            document = document_processor.process_file(test_file)
            if document:
                index_manager.add_document(document)
                return True

            return False

        except Exception as e:
            self.logger.error(f"インデックステストエラー: {e}")
            return False

    def _test_search_feature(self) -> bool:
        """検索機能のテスト"""
        try:
            search_manager = self.test_components['search_manager']

            # 検索クエリの実行
            query = SearchQuery(
                query_text="テスト",
                search_type=SearchType.FULL_TEXT,
                limit=10
            )

            results = search_manager.search(query)
            return results is not None

        except Exception as e:
            self.logger.error(f"検索テストエラー: {e}")
            return False

    def _test_embedding_feature(self) -> bool:
        """埋め込み機能のテスト"""
        try:
            embedding_manager = self.test_components['embedding_manager']

            # 埋め込み生成のテスト
            test_text = "テスト文書"
            embedding = embedding_manager.generate_embedding(test_text)

            return embedding is not None and len(embedding) > 0

        except Exception as e:
            self.logger.error(f"埋め込みテストエラー: {e}")
            return False

    def _test_gui_feature(self) -> bool:
        """GUI機能のテスト（模擬）"""
        try:
            # 実際のGUIテストは複雑なため、模擬実装
            # 基本的なPySide6の動作確認
            from PySide6.QtWidgets import QApplication

            # アプリケーションインスタンスの確認
            app = QApplication.instance()
            if app is None:
                # テスト用の一時的なアプリケーション作成
                app = QApplication([])

            return True

        except Exception as e:
            self.logger.error(f"GUIテストエラー: {e}")
            return False

    def _test_windows_performance(self) -> dict[str, float]:
        """Windowsでのパフォーマンステスト"""
        performance_results = {}

        try:
            # 起動時間の測定（模擬）
            start_time = time.time()
            self._simulate_application_startup()
            startup_time = time.time() - start_time
            performance_results['startup_time_seconds'] = startup_time

            # 検索時間の測定
            start_time = time.time()
            self._test_search_feature()
            search_time = time.time() - start_time
            performance_results['search_time_seconds'] = search_time

            # メモリ使用量の測定
            process = psutil.Process()
            memory_mb = process.memory_info().rss // (1024 * 1024)
            performance_results['memory_usage_mb'] = memory_mb

        except Exception as e:
            self.logger.error(f"パフォーマンステストエラー: {e}")

        return performance_results

    def _simulate_application_startup(self) -> None:
        """アプリケーション起動のシミュレーション"""
        # DocMindコンポーネントの初期化をシミュレート
        time.sleep(0.1)  # 起動処理のシミュレーション

    def _get_screen_resolution(self) -> tuple[int, int]:
        """画面解像度の取得（模擬）"""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                app = QApplication([])

            screen = app.primaryScreen()
            if screen:
                size = screen.size()
                return (size.width(), size.height())
            else:
                # デフォルト解像度
                return (1920, 1080)

        except Exception:
            # エラー時はデフォルト解像度を返す
            return (1920, 1080)

    def _test_resolution_compatibility(self, resolution: tuple[int, int]) -> dict[str, Any]:
        """解像度互換性のテスト"""
        results = {
            'current_resolution': resolution,
            'ui_scaling': True,  # 模擬結果
            'text_readability': True,
            'button_accessibility': True
        }

        # 最小解像度チェック
        min_width, min_height = self.thresholds.min_screen_resolution
        if resolution[0] < min_width or resolution[1] < min_height:
            results['ui_scaling'] = False
            results['text_readability'] = False

        return results

    def _test_filesystem_compatibility(self, filesystem_type: str) -> dict[str, Any]:
        """ファイルシステム互換性のテスト"""
        results = {
            'filesystem_type': filesystem_type,
            'file_operations': True,
            'long_filename_support': True,
            'unicode_filename_support': True,
            'large_file_support': True
        }

        try:
            # ファイル操作テスト
            test_file = os.path.join(self.test_base_dir, "filesystem_test.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("ファイルシステムテスト")

            # ファイルの読み書きテスト
            with open(test_file, encoding='utf-8') as f:
                content = f.read()
                if content != "ファイルシステムテスト":
                    results['file_operations'] = False

            # Unicode ファイル名テスト
            unicode_file = os.path.join(self.test_base_dir, "日本語ファイル名テスト.txt")
            try:
                with open(unicode_file, 'w', encoding='utf-8') as f:
                    f.write("Unicode ファイル名テスト")
                self.created_test_files.append(unicode_file)
            except (OSError, UnicodeError):
                results['unicode_filename_support'] = False

            # 長いファイル名テスト
            long_filename = "a" * 200 + ".txt"
            long_file_path = os.path.join(self.test_base_dir, long_filename)
            try:
                with open(long_file_path, 'w') as f:
                    f.write("長いファイル名テスト")
                self.created_test_files.append(long_file_path)
            except OSError:
                results['long_filename_support'] = False

            self.created_test_files.append(test_file)

        except Exception as e:
            self.logger.error(f"ファイルシステムテストエラー: {e}")
            results['file_operations'] = False

        return results

    def _test_gui_display_compatibility(self) -> dict[str, Any]:
        """GUI表示互換性のテスト（模擬）"""
        results = {
            'display_accuracy': True,
            'font_rendering': True,
            'color_accuracy': True,
            'layout_integrity': True
        }

        try:
            # PySide6の基本的な動作確認
            from PySide6.QtWidgets import QApplication, QLabel, QWidget

            app = QApplication.instance()
            if app is None:
                app = QApplication([])

            # テスト用ウィジェットの作成
            widget = QWidget()
            QLabel("テスト表示", widget)

            # 基本的な表示テスト
            widget.show()
            widget.hide()  # すぐに非表示

        except Exception as e:
            self.logger.error(f"GUI表示テストエラー: {e}")
            results['display_accuracy'] = False
            results['font_rendering'] = False

        return results

    def _test_encoding_file_processing(self, test_files: list[str]) -> dict[str, dict[str, bool]]:
        """エンコーディングファイル処理のテスト"""
        processing_results = {}

        document_processor = self.test_components['document_processor']

        for file_path in test_files:
            try:
                # ファイル名からエンコーディングを抽出
                filename = os.path.basename(file_path)
                encoding = filename.split('_')[1] if '_' in filename else 'unknown'

                if encoding not in processing_results:
                    processing_results[encoding] = {}

                # ドキュメント処理の実行
                document = document_processor.process_file(file_path)

                # 処理結果の評価
                test_type = filename.split('_')[2].replace('.txt', '') if '_' in filename else 'unknown'
                processing_results[encoding][test_type] = (
                    document is not None and
                    len(document.content) > 0 and
                    'エンコーディング' in document.content
                )

            except Exception as e:
                self.logger.error(f"エンコーディングファイル処理エラー ({file_path}): {e}")
                if encoding not in processing_results:
                    processing_results[encoding] = {}
                processing_results[encoding][test_type] = False

        return processing_results

    def _test_encoding_search_functionality(self, test_files: list[str]) -> dict[str, dict[str, bool]]:
        """エンコーディング検索機能のテスト"""
        search_results = {}

        search_manager = self.test_components['search_manager']

        # まず、テストファイルをインデックスに追加
        index_manager = self.test_components['index_manager']
        document_processor = self.test_components['document_processor']

        for file_path in test_files:
            try:
                document = document_processor.process_file(file_path)
                if document:
                    index_manager.add_document(document)
            except Exception:
                continue

        # 各エンコーディングでの検索テスト
        for encoding in self.thresholds.supported_encodings:
            search_results[encoding] = {}

            # 基本検索テスト
            try:
                query = SearchQuery(
                    query_text="エンコーディング",
                    search_type=SearchType.FULL_TEXT,
                    limit=10
                )
                results = search_manager.search(query)
                search_results[encoding]['basic_search'] = results is not None and len(results) > 0

            except Exception as e:
                self.logger.error(f"エンコーディング検索テストエラー ({encoding}): {e}")
                search_results[encoding]['basic_search'] = False

            # 日本語検索テスト
            try:
                query = SearchQuery(
                    query_text="テスト",
                    search_type=SearchType.FULL_TEXT,
                    limit=10
                )
                results = search_manager.search(query)
                search_results[encoding]['japanese_search'] = results is not None

            except Exception:
                search_results[encoding]['japanese_search'] = False

        return search_results

    def _test_low_memory_environment(self) -> dict[str, Any]:
        """低メモリ環境でのテスト"""
        results = {
            'basic_functionality': True,
            'acceptable_performance': True,
            'critical_errors': [],
            'performance_metrics': {}
        }

        try:
            # メモリ制限のシミュレーション
            self.resource_limiter.simulate_limited_memory(512)  # 512MB制限

            # 基本機能テスト
            start_time = time.time()

            # ドキュメント処理テスト
            doc_test = self._test_document_processing_feature()
            if not doc_test:
                results['basic_functionality'] = False
                results['critical_errors'].append("ドキュメント処理が失敗")

            # 検索テスト
            search_test = self._test_search_feature()
            if not search_test:
                results['basic_functionality'] = False
                results['critical_errors'].append("検索機能が失敗")

            # パフォーマンス測定
            execution_time = time.time() - start_time
            results['performance_metrics']['execution_time'] = execution_time

            # メモリ使用量チェック
            process = psutil.Process()
            memory_mb = process.memory_info().rss // (1024 * 1024)
            results['performance_metrics']['memory_usage_mb'] = memory_mb

            # パフォーマンス許容範囲チェック
            if execution_time > self.thresholds.max_search_time_seconds * 2:
                results['acceptable_performance'] = False

            if memory_mb > 1024:  # 1GB超過で警告
                results['acceptable_performance'] = False

        except Exception as e:
            results['basic_functionality'] = False
            results['critical_errors'].append(f"低メモリテストエラー: {str(e)}")

        return results

    def _test_low_disk_environment(self) -> dict[str, Any]:
        """低ディスク容量環境でのテスト"""
        results = {
            'basic_functionality': True,
            'acceptable_performance': True,
            'critical_errors': [],
            'performance_metrics': {}
        }

        try:
            # ディスク容量制限のシミュレーション
            dummy_file = self.resource_limiter.simulate_limited_disk_space(
                self.test_base_dir, 100  # 100MB制限
            )

            if dummy_file:
                self.created_test_files.append(dummy_file)

            # 基本機能テスト
            start_time = time.time()

            # ファイル作成テスト
            try:
                test_file = os.path.join(self.test_base_dir, "low_disk_test.txt")
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write("低ディスク容量テスト")
                self.created_test_files.append(test_file)
            except OSError as e:
                results['basic_functionality'] = False
                results['critical_errors'].append(f"ファイル作成失敗: {str(e)}")

            # インデックス作成テスト
            index_test = self._test_indexing_feature()
            if not index_test:
                results['critical_errors'].append("インデックス作成が失敗")

            # パフォーマンス測定
            execution_time = time.time() - start_time
            results['performance_metrics']['execution_time'] = execution_time

            # ディスク使用量チェック
            disk_usage = shutil.disk_usage(self.test_base_dir)
            available_mb = disk_usage.free // (1024 * 1024)
            results['performance_metrics']['available_disk_mb'] = available_mb

        except Exception as e:
            results['basic_functionality'] = False
            results['critical_errors'].append(f"低ディスクテストエラー: {str(e)}")

        return results

    def _test_low_cpu_environment(self) -> dict[str, Any]:
        """低CPU環境でのテスト（模擬）"""
        results = {
            'basic_functionality': True,
            'acceptable_performance': True,
            'critical_errors': [],
            'performance_metrics': {}
        }

        try:
            # CPU制限のシミュレーション（実際の制限は困難なため、負荷を追加）
            start_time = time.time()

            # CPU集約的なタスクを追加して負荷をシミュレート
            def cpu_intensive_task():
                for _ in range(100000):
                    _ = sum(range(100))

            # バックグラウンドでCPU負荷を生成
            cpu_thread = threading.Thread(target=cpu_intensive_task)
            cpu_thread.daemon = True
            cpu_thread.start()

            # 基本機能テスト
            doc_test = self._test_document_processing_feature()
            search_test = self._test_search_feature()

            if not (doc_test and search_test):
                results['basic_functionality'] = False
                results['critical_errors'].append("基本機能が低CPU環境で失敗")

            # パフォーマンス測定
            execution_time = time.time() - start_time
            results['performance_metrics']['execution_time'] = execution_time

            # CPU使用率測定
            cpu_percent = psutil.cpu_percent(interval=1.0)
            results['performance_metrics']['cpu_usage_percent'] = cpu_percent

            # パフォーマンス許容範囲チェック
            if execution_time > self.thresholds.max_search_time_seconds * 3:
                results['acceptable_performance'] = False

        except Exception as e:
            results['basic_functionality'] = False
            results['critical_errors'].append(f"低CPUテストエラー: {str(e)}")

        return results

    def _test_combined_resource_limits(self) -> dict[str, Any]:
        """複合リソース制限環境でのテスト"""
        results = {
            'basic_functionality': True,
            'acceptable_performance': True,
            'critical_errors': [],
            'performance_metrics': {}
        }

        try:
            # 複合制限の適用
            self.resource_limiter.simulate_limited_memory(256)  # 256MB制限
            dummy_file = self.resource_limiter.simulate_limited_disk_space(
                self.test_base_dir, 50  # 50MB制限
            )

            if dummy_file:
                self.created_test_files.append(dummy_file)

            # 基本機能の最小限テスト
            start_time = time.time()

            # 最小限のドキュメント処理
            try:
                test_file = os.path.join(self.test_base_dir, "minimal_test.txt")
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write("最小限テスト")

                document_processor = self.test_components['document_processor']
                document = document_processor.process_file(test_file)

                if document is None:
                    results['basic_functionality'] = False
                    results['critical_errors'].append("最小限のドキュメント処理が失敗")

                self.created_test_files.append(test_file)

            except Exception as e:
                results['basic_functionality'] = False
                results['critical_errors'].append(f"複合制限環境でのテスト失敗: {str(e)}")

            # パフォーマンス測定
            execution_time = time.time() - start_time
            results['performance_metrics']['execution_time'] = execution_time

            # リソース使用量測定
            process = psutil.Process()
            memory_mb = process.memory_info().rss // (1024 * 1024)
            results['performance_metrics']['memory_usage_mb'] = memory_mb

            disk_usage = shutil.disk_usage(self.test_base_dir)
            available_mb = disk_usage.free // (1024 * 1024)
            results['performance_metrics']['available_disk_mb'] = available_mb

        except Exception as e:
            results['basic_functionality'] = False
            results['critical_errors'].append(f"複合制限テストエラー: {str(e)}")

        return results

    # 監査メソッド

    def _audit_system_compatibility(self) -> dict[str, Any]:
        """システム互換性の監査"""
        system_info = self.system_info_collector.collect_system_info()
        windows_version, is_supported = self.system_info_collector.get_windows_version()

        score = 1.0 if is_supported else 0.0
        critical_issues = [] if is_supported else [f"サポートされていないOS: {windows_version}"]

        return {
            'score': score,
            'critical_issues': critical_issues,
            'checks_performed': 1,
            'details': {
                'os_version': windows_version,
                'is_supported': is_supported,
                'system_info': system_info
            }
        }

    def _audit_feature_compatibility(self) -> dict[str, Any]:
        """機能互換性の監査"""
        feature_results = self._test_all_docmind_features()

        successful_features = sum(feature_results.values())
        total_features = len(feature_results)
        score = successful_features / total_features if total_features > 0 else 0.0

        failed_features = [
            feature for feature, success in feature_results.items()
            if not success
        ]

        critical_issues = [f"機能テスト失敗: {feature}" for feature in failed_features]

        return {
            'score': score,
            'critical_issues': critical_issues,
            'checks_performed': total_features,
            'details': {
                'feature_results': feature_results,
                'successful_features': successful_features,
                'failed_features': failed_features
            }
        }

    def _audit_performance_compatibility(self) -> dict[str, Any]:
        """パフォーマンス互換性の監査"""
        performance_results = self._test_windows_performance()

        # パフォーマンス基準のチェック
        performance_issues = []

        startup_time = performance_results.get('startup_time_seconds', 0)
        if startup_time > self.thresholds.max_startup_time_seconds:
            performance_issues.append(f"起動時間超過: {startup_time:.2f}s")

        search_time = performance_results.get('search_time_seconds', 0)
        if search_time > self.thresholds.max_search_time_seconds:
            performance_issues.append(f"検索時間超過: {search_time:.2f}s")

        memory_usage = performance_results.get('memory_usage_mb', 0)
        if memory_usage > self.thresholds.max_memory_usage_mb:
            performance_issues.append(f"メモリ使用量超過: {memory_usage}MB")

        score = 1.0 - (len(performance_issues) / 3.0)  # 3つの基準

        return {
            'score': max(0.0, score),
            'critical_issues': performance_issues,
            'checks_performed': 3,
            'details': {
                'performance_results': performance_results,
                'thresholds': {
                    'max_startup_time': self.thresholds.max_startup_time_seconds,
                    'max_search_time': self.thresholds.max_search_time_seconds,
                    'max_memory_usage': self.thresholds.max_memory_usage_mb
                }
            }
        }

    def _audit_resource_compatibility(self) -> dict[str, Any]:
        """リソース互換性の監査"""
        system_info = self.system_info_collector.collect_system_info()

        resource_issues = []

        # メモリチェック
        available_memory = system_info.get('available_memory_mb', 0)
        if available_memory < self.thresholds.min_memory_mb:
            resource_issues.append(f"メモリ不足: {available_memory}MB < {self.thresholds.min_memory_mb}MB")

        # ディスク容量チェック
        available_disk = system_info.get('free_disk_mb', 0)
        if available_disk < self.thresholds.min_disk_space_mb:
            resource_issues.append(f"ディスク容量不足: {available_disk}MB < {self.thresholds.min_disk_space_mb}MB")

        score = 1.0 - (len(resource_issues) / 2.0)  # 2つの基準

        return {
            'score': max(0.0, score),
            'critical_issues': resource_issues,
            'checks_performed': 2,
            'details': {
                'available_memory_mb': available_memory,
                'available_disk_mb': available_disk,
                'min_requirements': {
                    'memory_mb': self.thresholds.min_memory_mb,
                    'disk_mb': self.thresholds.min_disk_space_mb
                }
            }
        }

    def _audit_environment_compatibility(self) -> dict[str, Any]:
        """環境互換性の監査"""
        # 画面解像度チェック
        resolution = self._get_screen_resolution()
        min_width, min_height = self.thresholds.min_screen_resolution

        # ファイルシステムチェック
        filesystem_type = self.system_info_collector.get_filesystem_type(self.test_base_dir)

        environment_issues = []

        if resolution[0] < min_width or resolution[1] < min_height:
            environment_issues.append(f"画面解像度不足: {resolution}")

        if filesystem_type not in self.thresholds.supported_filesystems:
            environment_issues.append(f"サポートされていないファイルシステム: {filesystem_type}")

        score = 1.0 - (len(environment_issues) / 2.0)  # 2つの基準

        return {
            'score': max(0.0, score),
            'critical_issues': environment_issues,
            'checks_performed': 2,
            'details': {
                'screen_resolution': resolution,
                'filesystem_type': filesystem_type,
                'min_resolution': self.thresholds.min_screen_resolution,
                'supported_filesystems': self.thresholds.supported_filesystems
            }
        }

    # 推奨事項生成メソッド

    def _generate_windows_recommendations(self, issues: list[str]) -> list[str]:
        """Windows環境の推奨事項生成"""
        recommendations = []

        for issue in issues:
            if "Windows版本" in issue:
                recommendations.append("Windows 10 (バージョン1903以降) またはWindows 11にアップグレードしてください")
            elif "メモリ不足" in issue:
                recommendations.append("最低512MB以上の利用可能メモリを確保してください")
            elif "ディスク容量不足" in issue:
                recommendations.append("最低1GB以上の利用可能ディスク容量を確保してください")
            elif "機能テスト失敗" in issue:
                recommendations.append("必要な依存関係がインストールされているか確認してください")

        if not recommendations:
            recommendations.append("現在の環境は互換性要件を満たしています")

        return recommendations

    def _generate_display_filesystem_recommendations(
        self, resolution: tuple[int, int], filesystem: str, issues: list[str]
    ) -> list[str]:
        """表示・ファイルシステムの推奨事項生成"""
        recommendations = []

        for issue in issues:
            if "画面解像度不足" in issue:
                recommendations.append(f"最低1024x768以上の画面解像度を設定してください（現在: {resolution}）")
            elif "ファイルシステム" in issue:
                recommendations.append(f"NTFS、FAT32、またはexFATファイルシステムを使用してください（現在: {filesystem}）")
            elif "UI スケーリング" in issue:
                recommendations.append("Windowsの表示スケール設定を100%または125%に設定してください")
            elif "ファイル操作" in issue:
                recommendations.append("ファイルシステムの権限設定を確認してください")

        if not recommendations:
            recommendations.append("表示とファイルシステムの設定は適切です")

        return recommendations

    def _generate_encoding_recommendations(self, issues: list[str]) -> list[str]:
        """エンコーディングの推奨事項生成"""
        recommendations = []

        for issue in issues:
            if "shift_jis" in issue:
                recommendations.append("Shift_JISファイルはUTF-8に変換することを推奨します")
            elif "euc-jp" in issue:
                recommendations.append("EUC-JPファイルはUTF-8に変換することを推奨します")
            elif "iso-2022-jp" in issue:
                recommendations.append("ISO-2022-JPファイルはUTF-8に変換することを推奨します")
            else:
                recommendations.append("サポートされていないエンコーディングのファイルはUTF-8に変換してください")

        if not recommendations:
            recommendations.append("文字エンコーディングのサポートは良好です")

        return recommendations

    def _generate_resource_recommendations(
        self, issues: list[str], test_results: dict[str, Any]
    ) -> list[str]:
        """リソースの推奨事項生成"""
        recommendations = []

        for issue in issues:
            if "low_memory" in issue:
                recommendations.append("メモリ使用量を削減するため、他のアプリケーションを終了してください")
                recommendations.append("仮想メモリ（ページファイル）のサイズを増やすことを検討してください")
            elif "low_disk" in issue:
                recommendations.append("不要なファイルを削除してディスク容量を確保してください")
                recommendations.append("DocMindのデータディレクトリを容量の多いドライブに移動してください")
            elif "low_cpu" in issue:
                recommendations.append("CPU集約的な他のプロセスを終了してください")
                recommendations.append("DocMindの処理を小さなバッチに分割して実行してください")
            elif "combined_limits" in issue:
                recommendations.append("システムリソースが不足しています。ハードウェアのアップグレードを検討してください")

        if not recommendations:
            recommendations.append("現在のリソース環境は適切です")

        return recommendations

    def _generate_comprehensive_recommendations(self, audit_results: dict[str, Any]) -> list[str]:
        """包括的な推奨事項生成"""
        recommendations = []

        # 各カテゴリの結果を分析
        for category, result in audit_results.items():
            score = result.get('score', 0.0)
            critical_issues = result.get('critical_issues', [])

            if score < 0.7:
                recommendations.append(f"{category}の改善が必要です（スコア: {score:.2f}）")

            if critical_issues:
                recommendations.extend([f"{category}: {issue}" for issue in critical_issues[:2]])  # 最大2件

        # 全体的な推奨事項
        overall_score = sum(result['score'] for result in audit_results.values()) / len(audit_results)

        if overall_score >= 0.9:
            recommendations.append("システムは DocMind の動作に最適化されています")
        elif overall_score >= 0.7:
            recommendations.append("システムは DocMind の基本動作に適していますが、一部改善の余地があります")
        else:
            recommendations.append("システムの大幅な改善または設定変更が必要です")

        return recommendations[:10]  # 最大10件の推奨事項

    def test_comprehensive_compatibility_audit(self) -> None:
        """包括的互換性監査の実行"""
        self.logger.info("包括的互換性監査を実行します")

        # 各種互換性テストの実行
        audit_results = {}

        # システム要件監査
        system_audit = self._audit_system_requirements()
        audit_results['system_requirements'] = system_audit

        # パフォーマンス監査
        performance_audit = self._audit_performance_requirements()
        audit_results['performance'] = performance_audit

        # 機能互換性監査
        functionality_audit = self._audit_functionality_compatibility()
        audit_results['functionality'] = functionality_audit

        # セキュリティ監査
        security_audit = self._audit_security_compatibility()
        audit_results['security'] = security_audit

        # 全体スコアの計算
        overall_score = sum(result['score'] for result in audit_results.values()) / len(audit_results)

        # 互換性レベルの決定
        if overall_score >= 0.9:
            compatibility_level = "COMPATIBLE"
        elif overall_score >= 0.7:
            compatibility_level = "LIMITED"
        else:
            compatibility_level = "INCOMPATIBLE"

        # 重要な問題の抽出
        critical_issues = []
        for _category, result in audit_results.items():
            critical_issues.extend(result.get('critical_issues', []))

        # 互換性メトリクスの作成
        metrics = CompatibilityMetrics(
            test_name="comprehensive_compatibility_audit",
            compatibility_level=compatibility_level,
            feature_compatibility={
                category: result['score'] >= 0.7
                for category, result in audit_results.items()
            },
            performance_metrics={
                'overall_score': overall_score,
                'system_score': audit_results['system_requirements']['score'],
                'performance_score': audit_results['performance']['score'],
                'functionality_score': audit_results['functionality']['score'],
                'security_score': audit_results['security']['score']
            },
            limitations=critical_issues,
            recommendations=self._generate_comprehensive_recommendations(audit_results),
            additional_details={
                'audit_results': audit_results,
                'total_categories': len(audit_results),
                'passing_categories': sum(1 for result in audit_results.values() if result['score'] >= 0.7)
            }
        )

        self.compatibility_metrics.append(metrics)

        # 要件の検証
        self.assert_condition(
            compatibility_level != "INCOMPATIBLE",
            f"包括的互換性監査で重大な問題: {critical_issues}"
        )

        self.logger.info(f"包括的互換性監査完了 - 総合スコア: {overall_score:.2f}, レベル: {compatibility_level}")

    def _audit_system_requirements(self) -> dict[str, Any]:
        """システム要件の監査"""
        system_info = self.system_info_collector.collect_system_info()

        score = 1.0
        issues = []

        # OS要件チェック
        if system_info.get('os_name') != 'Windows':
            score -= 0.3
            issues.append("非Windows環境")

        # メモリ要件チェック
        memory_mb = system_info.get('available_memory_mb', 0)
        if memory_mb < self.thresholds.min_memory_mb:
            score -= 0.2
            issues.append(f"メモリ不足: {memory_mb}MB")

        # ディスク要件チェック
        disk_mb = system_info.get('free_disk_mb', 0)
        if disk_mb < self.thresholds.min_disk_space_mb:
            score -= 0.2
            issues.append(f"ディスク容量不足: {disk_mb}MB")

        # Python版本チェック
        python_version = system_info.get('python_version', '')
        if not python_version.startswith('3.'):
            score -= 0.3
            issues.append(f"Python版本不適切: {python_version}")

        return {
            'score': max(0.0, score),
            'issues': issues,
            'critical_issues': [issue for issue in issues if any(
                keyword in issue for keyword in ['メモリ不足', 'ディスク容量不足', 'Python版本']
            )],
            'details': system_info
        }

    def _audit_performance_requirements(self) -> dict[str, Any]:
        """パフォーマンス要件の監査"""
        score = 1.0
        issues = []

        try:
            # 基本的なパフォーマンステスト
            start_time = time.time()

            # CPU性能テスト
            cpu_test_time = self._measure_cpu_performance()
            if cpu_test_time > 5.0:
                score -= 0.2
                issues.append(f"CPU性能不足: {cpu_test_time:.2f}秒")

            # メモリアクセス性能テスト
            memory_test_time = self._measure_memory_performance()
            if memory_test_time > 2.0:
                score -= 0.2
                issues.append(f"メモリアクセス性能不足: {memory_test_time:.2f}秒")

            # ディスクI/O性能テスト
            disk_test_time = self._measure_disk_performance()
            if disk_test_time > 3.0:
                score -= 0.2
                issues.append(f"ディスクI/O性能不足: {disk_test_time:.2f}秒")

            total_time = time.time() - start_time

        except Exception as e:
            score = 0.0
            issues.append(f"パフォーマンステストエラー: {str(e)}")
            total_time = 0.0

        return {
            'score': max(0.0, score),
            'issues': issues,
            'critical_issues': [issue for issue in issues if '性能不足' in issue],
            'details': {
                'total_test_time': total_time,
                'cpu_test_time': cpu_test_time if 'cpu_test_time' in locals() else 0.0,
                'memory_test_time': memory_test_time if 'memory_test_time' in locals() else 0.0,
                'disk_test_time': disk_test_time if 'disk_test_time' in locals() else 0.0
            }
        }

    def _audit_functionality_compatibility(self) -> dict[str, Any]:
        """機能互換性の監査"""
        score = 1.0
        issues = []

        try:
            # DocMind機能テスト
            feature_results = self._test_all_docmind_features()

            failed_features = [
                feature for feature, success in feature_results.items()
                if not success
            ]

            if failed_features:
                score -= 0.1 * len(failed_features)
                issues.extend([f"機能テスト失敗: {feature}" for feature in failed_features])

        except Exception as e:
            score = 0.0
            issues.append(f"機能テストエラー: {str(e)}")

        return {
            'score': max(0.0, score),
            'issues': issues,
            'critical_issues': [issue for issue in issues if 'search' in issue or 'index' in issue],
            'details': {
                'feature_results': feature_results if 'feature_results' in locals() else {},
                'failed_features': failed_features if 'failed_features' in locals() else []
            }
        }

    def _audit_security_compatibility(self) -> dict[str, Any]:
        """セキュリティ互換性の監査"""
        score = 1.0
        issues = []

        try:
            # ファイル権限チェック
            if not self._check_file_permissions():
                score -= 0.3
                issues.append("ファイル権限不適切")

            # 一時ディレクトリアクセスチェック
            if not self._check_temp_directory_access():
                score -= 0.2
                issues.append("一時ディレクトリアクセス不可")

            # ネットワーク分離チェック（模擬）
            if not self._check_network_isolation():
                score -= 0.1
                issues.append("ネットワーク分離不完全")

        except Exception as e:
            score = 0.0
            issues.append(f"セキュリティテストエラー: {str(e)}")

        return {
            'score': max(0.0, score),
            'issues': issues,
            'critical_issues': [issue for issue in issues if 'ファイル権限' in issue],
            'details': {}
        }

    def _measure_cpu_performance(self) -> float:
        """CPU性能の測定"""
        start_time = time.time()

        # 簡単な計算集約的タスク
        result = 0
        for i in range(1000000):
            result += i * i

        return time.time() - start_time

    def _measure_memory_performance(self) -> float:
        """メモリアクセス性能の測定"""
        start_time = time.time()

        # メモリアクセス集約的タスク
        data = list(range(100000))
        data.sort()
        data.reverse()

        return time.time() - start_time

    def _measure_disk_performance(self) -> float:
        """ディスクI/O性能の測定"""
        start_time = time.time()

        # 一時ファイルでのI/Oテスト
        test_file = os.path.join(self.test_base_dir, "disk_performance_test.tmp")

        try:
            # 書き込みテスト
            with open(test_file, 'w') as f:
                for i in range(1000):
                    f.write(f"テストデータ行 {i}\n")

            # 読み込みテスト
            with open(test_file) as f:
                f.read()

            # ファイル削除
            os.remove(test_file)

        except Exception:
            pass

        return time.time() - start_time

    def _check_file_permissions(self) -> bool:
        """ファイル権限のチェック"""
        try:
            test_file = os.path.join(self.test_base_dir, "permission_test.tmp")

            # ファイル作成テスト
            with open(test_file, 'w') as f:
                f.write("権限テスト")

            # ファイル読み込みテスト
            with open(test_file) as f:
                f.read()

            # ファイル削除テスト
            os.remove(test_file)

            return True

        except Exception:
            return False

    def _check_temp_directory_access(self) -> bool:
        """一時ディレクトリアクセスのチェック"""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=True)
            temp_file.write(b"temp test")
            temp_file.close()
            return True
        except Exception:
            return False

    def _check_network_isolation(self) -> bool:
        """ネットワーク分離のチェック（模擬）"""
        # 実際のネットワークテストは行わず、常にTrueを返す
        return True

    def get_compatibility_summary(self) -> dict[str, Any]:
        """互換性検証結果のサマリーを取得"""
        if not self.compatibility_metrics:
            return {}

        # 互換性レベルの集計
        level_counts = {}
        for metric in self.compatibility_metrics:
            level = metric.compatibility_level
            level_counts[level] = level_counts.get(level, 0) + 1

        # 全体的な互換性レベルの決定
        if level_counts.get('INCOMPATIBLE', 0) > 0:
            overall_level = 'INCOMPATIBLE'
        elif level_counts.get('LIMITED', 0) > 0:
            overall_level = 'LIMITED'
        else:
            overall_level = 'COMPATIBLE'

        # 共通の制限事項と推奨事項
        all_limitations = []
        all_recommendations = []

        for metric in self.compatibility_metrics:
            all_limitations.extend(metric.limitations)
            all_recommendations.extend(metric.recommendations)

        # 重複を除去
        unique_limitations = list(set(all_limitations))
        unique_recommendations = list(set(all_recommendations))

        return {
            'overall_compatibility_level': overall_level,
            'test_count': len(self.compatibility_metrics),
            'level_distribution': level_counts,
            'common_limitations': unique_limitations[:10],  # 最大10件
            'key_recommendations': unique_recommendations[:10],  # 最大10件
            'detailed_metrics': [
                {
                    'test_name': metric.test_name,
                    'compatibility_level': metric.compatibility_level,
                    'limitations_count': len(metric.limitations),
                    'recommendations_count': len(metric.recommendations)
                }
                for metric in self.compatibility_metrics
            ]
        }
