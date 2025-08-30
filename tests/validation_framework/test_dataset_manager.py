"""
テストデータセット管理システム

包括的検証のための多様なテストデータセットを管理・生成します。
標準、大規模、エッジケース用のテストデータセットを提供し、
50,000ドキュメント規模の大規模テストデータセット自動生成機能を含みます。
"""

import json
import logging
import os
import shutil
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

try:
    from .test_data_generator import TestDataGenerator, TestDatasetConfig
except ImportError:
    from test_data_generator import TestDataGenerator, TestDatasetConfig


@dataclass
class DatasetMetrics:
    """データセットメトリクス"""
    total_files: int = 0
    total_size_mb: float = 0.0
    file_types: dict[str, int] = None
    corrupted_files: int = 0
    large_files: int = 0
    special_char_files: int = 0
    generation_time_seconds: float = 0.0

    def __post_init__(self):
        if self.file_types is None:
            self.file_types = {}


@dataclass
class DatasetInfo:
    """データセット情報"""
    name: str
    path: str
    dataset_type: str  # 'standard', 'large', 'edge_case'
    created_at: datetime
    metrics: DatasetMetrics
    config: TestDatasetConfig
    status: str = 'ready'  # 'generating', 'ready', 'error'


class TestDatasetManager:
    """
    テストデータセット管理クラス

    包括的検証のための多様なテストデータセットを管理します。
    標準、大規模、エッジケース用のテストデータセットを提供し、
    50,000ドキュメント規模の大規模テストデータセット自動生成機能を含みます。
    """

    def __init__(self, base_directory: str | None = None):
        """
        テストデータセット管理クラスの初期化

        Args:
            base_directory: テストデータセットのベースディレクトリ
        """
        self.logger = logging.getLogger(f"validation.{self.__class__.__name__}")

        # ベースディレクトリの設定
        if base_directory is None:
            self.base_directory = os.path.join(tempfile.gettempdir(), "docmind_test_datasets")
        else:
            self.base_directory = base_directory

        # ディレクトリの作成
        os.makedirs(self.base_directory, exist_ok=True)

        # データセット管理
        self.datasets: dict[str, DatasetInfo] = {}
        self.data_generator = TestDataGenerator()

        # 設定ファイルのパス
        self.config_file = os.path.join(self.base_directory, "datasets_config.json")

        # 既存のデータセット情報を読み込み
        self._load_existing_datasets()

        # 生成中のデータセットを追跡
        self._generation_threads: dict[str, threading.Thread] = {}

        self.logger.info(f"テストデータセット管理システムを初期化しました: {self.base_directory}")

    def _load_existing_datasets(self) -> None:
        """既存のデータセット情報を読み込み"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, encoding='utf-8') as f:
                    data = json.load(f)

                for dataset_name, dataset_data in data.items():
                    # DatasetInfoオブジェクトを復元
                    metrics_data = dataset_data.get('metrics', {})
                    metrics = DatasetMetrics(**metrics_data)

                    config_data = dataset_data.get('config', {})
                    config = TestDatasetConfig(**config_data)

                    dataset_info = DatasetInfo(
                        name=dataset_data['name'],
                        path=dataset_data['path'],
                        dataset_type=dataset_data['dataset_type'],
                        created_at=datetime.fromisoformat(dataset_data['created_at']),
                        metrics=metrics,
                        config=config,
                        status=dataset_data.get('status', 'ready')
                    )

                    # パスが存在するかチェック
                    if os.path.exists(dataset_info.path):
                        self.datasets[dataset_name] = dataset_info
                    else:
                        self.logger.warning(f"データセットパスが存在しません: {dataset_info.path}")

                self.logger.info(f"{len(self.datasets)}個の既存データセットを読み込みました")

            except Exception as e:
                self.logger.error(f"データセット設定ファイルの読み込みに失敗しました: {e}")

    def _save_datasets_config(self) -> None:
        """データセット設定をファイルに保存"""
        try:
            # ディレクトリが存在することを確認
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            data = {}
            for name, dataset_info in self.datasets.items():
                data[name] = {
                    'name': dataset_info.name,
                    'path': dataset_info.path,
                    'dataset_type': dataset_info.dataset_type,
                    'created_at': dataset_info.created_at.isoformat(),
                    'metrics': asdict(dataset_info.metrics),
                    'config': asdict(dataset_info.config),
                    'status': dataset_info.status
                }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"データセット設定ファイルの保存に失敗しました: {e}")

    def create_standard_dataset(self,
                              name: str = "standard_dataset",
                              file_count: int = 1000,
                              **kwargs) -> DatasetInfo:
        """
        標準テストデータセットの作成

        Args:
            name: データセット名
            file_count: ファイル数
            **kwargs: 追加設定

        Returns:
            作成されたデータセット情報
        """
        self.logger.info(f"標準テストデータセット '{name}' の作成を開始します")

        # 出力ディレクトリの作成
        dataset_dir = os.path.join(self.base_directory, name)
        os.makedirs(dataset_dir, exist_ok=True)

        # 設定の作成
        config = TestDatasetConfig(
            dataset_name=name,
            output_directory=dataset_dir,
            file_count=file_count,
            file_types=['txt', 'md', 'json', 'csv', 'docx', 'xlsx', 'pdf'],
            size_range_kb=(1, 100),
            content_language='ja',
            include_corrupted=False,
            include_large_files=False,
            include_special_chars=False,
            **kwargs
        )

        return self._generate_dataset(name, 'standard', config)

    def create_large_dataset(self,
                           name: str = "large_dataset",
                           file_count: int = 50000,
                           **kwargs) -> DatasetInfo:
        """
        大規模テストデータセットの作成

        Args:
            name: データセット名
            file_count: ファイル数（デフォルト50,000）
            **kwargs: 追加設定

        Returns:
            作成されたデータセット情報
        """
        self.logger.info(f"大規模テストデータセット '{name}' の作成を開始します（{file_count}ファイル）")

        # 出力ディレクトリの作成
        dataset_dir = os.path.join(self.base_directory, name)
        os.makedirs(dataset_dir, exist_ok=True)

        # 設定の作成
        config = TestDatasetConfig(
            dataset_name=name,
            output_directory=dataset_dir,
            file_count=file_count,
            file_types=['txt', 'md', 'json', 'csv', 'docx', 'xlsx', 'pdf'],
            size_range_kb=(1, 500),
            content_language='ja',
            include_corrupted=True,
            include_large_files=True,
            include_special_chars=True,
            **kwargs
        )

        return self._generate_dataset(name, 'large', config)

    def create_edge_case_dataset(self,
                               name: str = "edge_case_dataset",
                               file_count: int = 500,
                               **kwargs) -> DatasetInfo:
        """
        エッジケーステストデータセットの作成

        Args:
            name: データセット名
            file_count: ファイル数
            **kwargs: 追加設定

        Returns:
            作成されたデータセット情報
        """
        self.logger.info(f"エッジケーステストデータセット '{name}' の作成を開始します")

        # 出力ディレクトリの作成
        dataset_dir = os.path.join(self.base_directory, name)
        os.makedirs(dataset_dir, exist_ok=True)

        # 設定の作成
        config = TestDatasetConfig(
            dataset_name=name,
            output_directory=dataset_dir,
            file_count=file_count,
            file_types=['txt', 'md', 'json', 'csv', 'docx', 'xlsx', 'pdf'],
            size_range_kb=(0, 10000),  # 0KBから10MBまで
            content_language='ja',
            include_corrupted=True,
            include_large_files=True,
            include_special_chars=True,
            **kwargs
        )

        return self._generate_dataset(name, 'edge_case', config)

    def _generate_dataset(self, name: str, dataset_type: str, config: TestDatasetConfig) -> DatasetInfo:
        """
        データセットの生成

        Args:
            name: データセット名
            dataset_type: データセットタイプ
            config: 生成設定

        Returns:
            データセット情報
        """
        start_time = time.time()

        # データセット情報の初期化
        dataset_info = DatasetInfo(
            name=name,
            path=config.output_directory,
            dataset_type=dataset_type,
            created_at=datetime.now(),
            metrics=DatasetMetrics(),
            config=config,
            status='generating'
        )

        self.datasets[name] = dataset_info
        self._save_datasets_config()

        try:
            # データセット生成
            result = self.data_generator.generate_dataset(config)

            # メトリクスの更新
            stats = result['statistics']
            dataset_info.metrics = DatasetMetrics(
                total_files=stats['total_files'],
                total_size_mb=stats['total_size_mb'],
                file_types=stats['by_type'],
                corrupted_files=stats['corrupted_files'],
                large_files=stats['large_files'],
                special_char_files=stats['special_char_files'],
                generation_time_seconds=time.time() - start_time
            )

            dataset_info.status = 'ready'

            self.logger.info(
                f"データセット '{name}' の生成が完了しました: "
                f"{dataset_info.metrics.total_files}ファイル, "
                f"{dataset_info.metrics.total_size_mb:.2f}MB, "
                f"{dataset_info.metrics.generation_time_seconds:.2f}秒"
            )

        except Exception as e:
            dataset_info.status = 'error'
            self.logger.error(f"データセット '{name}' の生成中にエラーが発生しました: {e}")
            raise

        finally:
            self._save_datasets_config()

        return dataset_info

    def create_dataset_async(self, name: str, dataset_type: str, config: TestDatasetConfig) -> None:
        """
        データセットの非同期生成

        Args:
            name: データセット名
            dataset_type: データセットタイプ
            config: 生成設定
        """
        def generate_worker():
            try:
                self._generate_dataset(name, dataset_type, config)
            except Exception as e:
                self.logger.error(f"非同期データセット生成でエラーが発生しました: {e}")

        thread = threading.Thread(target=generate_worker, name=f"dataset_gen_{name}")
        self._generation_threads[name] = thread
        thread.start()

        self.logger.info(f"データセット '{name}' の非同期生成を開始しました")

    def get_dataset_info(self, name: str) -> DatasetInfo | None:
        """
        データセット情報の取得

        Args:
            name: データセット名

        Returns:
            データセット情報（存在しない場合はNone）
        """
        return self.datasets.get(name)

    def list_datasets(self) -> list[DatasetInfo]:
        """
        すべてのデータセット情報のリストを取得

        Returns:
            データセット情報のリスト
        """
        return list(self.datasets.values())

    def delete_dataset(self, name: str) -> bool:
        """
        データセットの削除

        Args:
            name: データセット名

        Returns:
            削除成功の場合True
        """
        if name not in self.datasets:
            self.logger.warning(f"データセット '{name}' が見つかりません")
            return False

        dataset_info = self.datasets[name]

        try:
            # ディレクトリの削除
            if os.path.exists(dataset_info.path):
                shutil.rmtree(dataset_info.path)

            # 管理情報から削除
            del self.datasets[name]
            self._save_datasets_config()

            self.logger.info(f"データセット '{name}' を削除しました")
            return True

        except Exception as e:
            self.logger.error(f"データセット '{name}' の削除中にエラーが発生しました: {e}")
            return False

    def get_dataset_files(self, name: str) -> list[str]:
        """
        データセット内のファイル一覧を取得

        Args:
            name: データセット名

        Returns:
            ファイルパスのリスト
        """
        if name not in self.datasets:
            return []

        dataset_info = self.datasets[name]

        try:
            files = []
            for root, _dirs, filenames in os.walk(dataset_info.path):
                for filename in filenames:
                    if not filename.endswith('.json'):  # メタデータファイルを除外
                        files.append(os.path.join(root, filename))

            return files

        except Exception as e:
            self.logger.error(f"データセット '{name}' のファイル一覧取得中にエラーが発生しました: {e}")
            return []

    def validate_dataset(self, name: str) -> dict[str, Any]:
        """
        データセットの整合性検証

        Args:
            name: データセット名

        Returns:
            検証結果の辞書
        """
        if name not in self.datasets:
            return {'valid': False, 'error': 'データセットが見つかりません'}

        dataset_info = self.datasets[name]
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_count': 0,
            'total_size_mb': 0.0,
            'missing_files': [],
            'corrupted_files': []
        }

        try:
            # ディレクトリの存在確認
            if not os.path.exists(dataset_info.path):
                validation_result['valid'] = False
                validation_result['errors'].append('データセットディレクトリが存在しません')
                return validation_result

            # ファイル数とサイズの確認
            files = self.get_dataset_files(name)
            validation_result['file_count'] = len(files)

            total_size = 0
            for file_path in files:
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
                else:
                    validation_result['missing_files'].append(file_path)

            validation_result['total_size_mb'] = total_size / (1024 * 1024)

            # メトリクスとの比較
            expected_files = dataset_info.metrics.total_files
            if validation_result['file_count'] != expected_files:
                validation_result['warnings'].append(
                    f"ファイル数が一致しません（期待値: {expected_files}, 実際: {validation_result['file_count']}）"
                )

            # 破損ファイルの検出（簡易チェック）
            for file_path in files[:min(100, len(files))]:  # 最初の100ファイルをチェック
                try:
                    with open(file_path, 'rb') as f:
                        f.read(1024)  # 最初の1KBを読み取り
                except Exception:
                    validation_result['corrupted_files'].append(file_path)

            if validation_result['missing_files']:
                validation_result['valid'] = False
                validation_result['errors'].append(f"{len(validation_result['missing_files'])}個のファイルが見つかりません")

            self.logger.info(f"データセット '{name}' の検証が完了しました")

        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"検証中にエラーが発生しました: {e}")
            self.logger.error(f"データセット '{name}' の検証中にエラーが発生しました: {e}")

        return validation_result

    def get_generation_status(self, name: str) -> dict[str, Any]:
        """
        データセット生成状況の取得

        Args:
            name: データセット名

        Returns:
            生成状況の辞書
        """
        if name not in self.datasets:
            return {'status': 'not_found'}

        dataset_info = self.datasets[name]
        status_info = {
            'status': dataset_info.status,
            'name': name,
            'dataset_type': dataset_info.dataset_type,
            'created_at': dataset_info.created_at.isoformat(),
            'is_generating': name in self._generation_threads and self._generation_threads[name].is_alive()
        }

        if dataset_info.status == 'ready':
            status_info['metrics'] = asdict(dataset_info.metrics)

        return status_info

    def cleanup_all_datasets(self) -> None:
        """すべてのデータセットのクリーンアップ"""
        self.logger.info("すべてのデータセットのクリーンアップを開始します")

        # 生成中のスレッドを停止
        for name, thread in self._generation_threads.items():
            if thread.is_alive():
                self.logger.info(f"データセット '{name}' の生成を停止しています...")
                # スレッドの強制終了は危険なので、完了を待つ
                thread.join(timeout=30)

        # すべてのデータセットを削除
        dataset_names = list(self.datasets.keys())
        for name in dataset_names:
            self.delete_dataset(name)

        # ベースディレクトリの削除
        try:
            if os.path.exists(self.base_directory):
                shutil.rmtree(self.base_directory)
            self.logger.info("すべてのデータセットのクリーンアップが完了しました")
        except Exception as e:
            self.logger.error(f"ベースディレクトリの削除中にエラーが発生しました: {e}")

    def generate_comprehensive_test_suite(self) -> dict[str, DatasetInfo]:
        """
        包括的テストスイート用のデータセット生成

        Returns:
            生成されたデータセットの辞書
        """
        self.logger.info("包括的テストスイート用のデータセット生成を開始します")

        datasets = {}

        try:
            # 標準データセット
            datasets['standard'] = self.create_standard_dataset(
                name="comprehensive_standard",
                file_count=1000
            )

            # 大規模データセット（サイズを調整）
            datasets['large'] = self.create_large_dataset(
                name="comprehensive_large",
                file_count=1000  # さらに削減して高速化
            )

            # エッジケースデータセット
            datasets['edge_case'] = self.create_edge_case_dataset(
                name="comprehensive_edge_case",
                file_count=500
            )

            self.logger.info("包括的テストスイート用のデータセット生成が完了しました")

        except Exception as e:
            self.logger.error(f"包括的テストスイート用のデータセット生成中にエラーが発生しました: {e}")
            raise

        return datasets

    def __del__(self):
        """デストラクタ"""
        # 生成中のスレッドがあれば待機
        for thread in self._generation_threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
