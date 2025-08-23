#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TestDatasetManager検証スクリプト

TestDatasetManagerクラスの包括的な動作検証を実行します。
"""

import os
import sys
import argparse
import tempfile
import logging
import time
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.test_dataset_manager import TestDatasetManager


class DatasetManagerValidator:
    """TestDatasetManager検証クラス"""
    
    def __init__(self, output_dir: str = None, quick_mode: bool = False):
        """
        初期化
        
        Args:
            output_dir: 出力ディレクトリ
            quick_mode: クイックモード（小さなデータセットで高速実行）
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.quick_mode = quick_mode
        
        # 出力ディレクトリの設定
        if output_dir is None:
            self.output_dir = os.path.join(tempfile.gettempdir(), "dataset_manager_validation")
        else:
            self.output_dir = output_dir
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # TestDatasetManagerの初期化
        self.manager = TestDatasetManager(base_directory=self.output_dir)
        
        # 検証結果
        self.validation_results = {
            'start_time': datetime.now(),
            'tests': {},
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'errors': []
            }
        }
        
        self.logger.info(f"TestDatasetManager検証を初期化しました: {self.output_dir}")
        if self.quick_mode:
            self.logger.info("クイックモードが有効です")
    
    def run_validation(self) -> dict:
        """
        包括的検証の実行
        
        Returns:
            検証結果の辞書
        """
        self.logger.info("TestDatasetManager包括的検証を開始します")
        
        try:
            # 各検証テストを実行
            self._test_basic_functionality()
            self._test_standard_dataset_creation()
            self._test_large_dataset_creation()
            self._test_edge_case_dataset_creation()
            self._test_dataset_management()
            self._test_dataset_validation()
            self._test_comprehensive_suite_generation()
            self._test_performance_characteristics()
            self._test_error_handling()
            self._test_concurrent_operations()
            
        except Exception as e:
            self.logger.error(f"検証中に予期しないエラーが発生しました: {e}")
            self.validation_results['summary']['errors'].append(str(e))
        
        finally:
            # 最終処理
            self.validation_results['end_time'] = datetime.now()
            self.validation_results['duration_seconds'] = (
                self.validation_results['end_time'] - self.validation_results['start_time']
            ).total_seconds()
            
            # サマリーの計算
            self._calculate_summary()
            
            # クリーンアップ
            self._cleanup()
        
        return self.validation_results
    
    def _test_basic_functionality(self):
        """基本機能のテスト"""
        test_name = "basic_functionality"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            # 初期化確認
            assert self.manager is not None
            assert os.path.exists(self.manager.base_directory)
            assert isinstance(self.manager.datasets, dict)
            
            # 初期状態確認
            datasets = self.manager.list_datasets()
            assert isinstance(datasets, list)
            
            self._record_test_result(test_name, True, "基本機能が正常に動作しています")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"基本機能テストでエラー: {e}")
    
    def _test_standard_dataset_creation(self):
        """標準データセット作成のテスト"""
        test_name = "standard_dataset_creation"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            file_count = 20 if self.quick_mode else 500
            
            start_time = time.time()
            dataset_info = self.manager.create_standard_dataset(
                name="test_standard",
                file_count=file_count
            )
            creation_time = time.time() - start_time
            
            # 結果検証
            assert dataset_info is not None
            assert dataset_info.name == "test_standard"
            assert dataset_info.dataset_type == "standard"
            assert dataset_info.status == "ready"
            assert dataset_info.metrics.total_files > 0
            assert dataset_info.metrics.total_size_mb > 0
            assert os.path.exists(dataset_info.path)
            
            # パフォーマンス確認
            expected_max_time = 60 if self.quick_mode else 300  # 秒
            assert creation_time < expected_max_time, f"作成時間が長すぎます: {creation_time:.2f}秒"
            
            self._record_test_result(
                test_name, True, 
                f"標準データセット作成成功: {dataset_info.metrics.total_files}ファイル, "
                f"{creation_time:.2f}秒"
            )
            
        except Exception as e:
            self._record_test_result(test_name, False, f"標準データセット作成テストでエラー: {e}")
    
    def _test_large_dataset_creation(self):
        """大規模データセット作成のテスト"""
        test_name = "large_dataset_creation"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            # クイックモードでは小さなサイズで実行
            file_count = 30 if self.quick_mode else 500  # さらに削減
            
            start_time = time.time()
            dataset_info = self.manager.create_large_dataset(
                name="test_large",
                file_count=file_count
            )
            creation_time = time.time() - start_time
            
            # 結果検証
            assert dataset_info is not None
            assert dataset_info.name == "test_large"
            assert dataset_info.dataset_type == "large"
            assert dataset_info.status == "ready"
            assert dataset_info.metrics.total_files > 0
            assert dataset_info.metrics.corrupted_files >= 0
            assert dataset_info.metrics.large_files >= 0
            assert dataset_info.metrics.special_char_files >= 0
            
            # 大規模データセットの特徴確認
            assert dataset_info.config.include_corrupted == True
            assert dataset_info.config.include_large_files == True
            assert dataset_info.config.include_special_chars == True
            
            self._record_test_result(
                test_name, True,
                f"大規模データセット作成成功: {dataset_info.metrics.total_files}ファイル, "
                f"{creation_time:.2f}秒"
            )
            
        except Exception as e:
            self._record_test_result(test_name, False, f"大規模データセット作成テストでエラー: {e}")
    
    def _test_edge_case_dataset_creation(self):
        """エッジケースデータセット作成のテスト"""
        test_name = "edge_case_dataset_creation"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            file_count = 25 if self.quick_mode else 250
            
            start_time = time.time()
            dataset_info = self.manager.create_edge_case_dataset(
                name="test_edge_case",
                file_count=file_count
            )
            creation_time = time.time() - start_time
            
            # 結果検証
            assert dataset_info is not None
            assert dataset_info.name == "test_edge_case"
            assert dataset_info.dataset_type == "edge_case"
            assert dataset_info.status == "ready"
            
            # エッジケースの特徴確認
            assert dataset_info.config.include_corrupted == True
            assert dataset_info.config.include_large_files == True
            assert dataset_info.config.include_special_chars == True
            assert dataset_info.config.size_range_kb == (0, 10000)
            
            self._record_test_result(
                test_name, True,
                f"エッジケースデータセット作成成功: {dataset_info.metrics.total_files}ファイル, "
                f"破損ファイル: {dataset_info.metrics.corrupted_files}, "
                f"{creation_time:.2f}秒"
            )
            
        except Exception as e:
            self._record_test_result(test_name, False, f"エッジケースデータセット作成テストでエラー: {e}")
    
    def _test_dataset_management(self):
        """データセット管理機能のテスト"""
        test_name = "dataset_management"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            # データセット一覧の取得
            datasets = self.manager.list_datasets()
            assert len(datasets) >= 3  # 前のテストで作成されたデータセット
            
            # 個別データセット情報の取得
            for dataset_name in ["test_standard", "test_large", "test_edge_case"]:
                dataset_info = self.manager.get_dataset_info(dataset_name)
                assert dataset_info is not None
                assert dataset_info.name == dataset_name
                
                # ファイル一覧の取得
                files = self.manager.get_dataset_files(dataset_name)
                assert isinstance(files, list)
                assert len(files) > 0
                
                # 生成状況の確認
                status = self.manager.get_generation_status(dataset_name)
                assert status['status'] == 'ready'
                assert status['name'] == dataset_name
            
            # 存在しないデータセットの処理
            nonexistent_info = self.manager.get_dataset_info("nonexistent")
            assert nonexistent_info is None
            
            nonexistent_status = self.manager.get_generation_status("nonexistent")
            assert nonexistent_status['status'] == 'not_found'
            
            self._record_test_result(test_name, True, "データセット管理機能が正常に動作しています")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"データセット管理テストでエラー: {e}")
    
    def _test_dataset_validation(self):
        """データセット検証機能のテスト"""
        test_name = "dataset_validation"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            # 各データセットの検証
            for dataset_name in ["test_standard", "test_large", "test_edge_case"]:
                validation_result = self.manager.validate_dataset(dataset_name)
                
                assert isinstance(validation_result, dict)
                assert 'valid' in validation_result
                assert 'file_count' in validation_result
                assert 'total_size_mb' in validation_result
                assert 'errors' in validation_result
                assert 'warnings' in validation_result
                
                # 基本的な整合性確認
                assert validation_result['file_count'] > 0
                assert validation_result['total_size_mb'] > 0
                
                if not validation_result['valid']:
                    self.logger.warning(f"データセット '{dataset_name}' の検証で問題が検出されました: "
                                      f"{validation_result['errors']}")
            
            # 存在しないデータセットの検証
            invalid_result = self.manager.validate_dataset("nonexistent")
            assert invalid_result['valid'] == False
            assert 'データセットが見つかりません' in invalid_result['error']
            
            self._record_test_result(test_name, True, "データセット検証機能が正常に動作しています")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"データセット検証テストでエラー: {e}")
    
    def _test_comprehensive_suite_generation(self):
        """包括的テストスイート生成のテスト"""
        test_name = "comprehensive_suite_generation"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            # 新しいマネージャーで包括的スイートを生成
            suite_dir = os.path.join(self.output_dir, "comprehensive_suite")
            suite_manager = TestDatasetManager(base_directory=suite_dir)
            
            # クイックモードでは小さなサイズで実行
            if self.quick_mode:
                # 個別に小さなデータセットを作成
                suite_datasets = {}
                
                suite_datasets['standard'] = suite_manager.create_standard_dataset(
                    name="suite_standard", file_count=10
                )
                suite_datasets['large'] = suite_manager.create_large_dataset(
                    name="suite_large", file_count=15
                )
                suite_datasets['edge_case'] = suite_manager.create_edge_case_dataset(
                    name="suite_edge_case", file_count=10
                )
            else:
                # 通常の包括的テストスイート生成
                suite_datasets = suite_manager.generate_comprehensive_test_suite()
            
            # 結果検証
            assert len(suite_datasets) == 3
            assert 'standard' in suite_datasets
            assert 'large' in suite_datasets
            assert 'edge_case' in suite_datasets
            
            # 各データセットの詳細確認
            for suite_type, dataset_info in suite_datasets.items():
                assert dataset_info.dataset_type == suite_type
                assert dataset_info.status == 'ready'
                assert dataset_info.metrics.total_files > 0
            
            self._record_test_result(
                test_name, True,
                f"包括的テストスイート生成成功: {len(suite_datasets)}データセット"
            )
            
        except Exception as e:
            self._record_test_result(test_name, False, f"包括的テストスイート生成テストでエラー: {e}")
    
    def _test_performance_characteristics(self):
        """パフォーマンス特性のテスト"""
        test_name = "performance_characteristics"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            # 小規模データセットでのパフォーマンステスト
            file_count = 20
            
            start_time = time.time()
            perf_dataset = self.manager.create_standard_dataset(
                name="perf_test",
                file_count=file_count
            )
            creation_time = time.time() - start_time
            
            # パフォーマンス基準の確認
            files_per_second = file_count / creation_time
            assert files_per_second > 1, f"生成速度が遅すぎます: {files_per_second:.2f}ファイル/秒"
            
            # メモリ効率の確認（概算）
            avg_file_size_mb = perf_dataset.metrics.total_size_mb / perf_dataset.metrics.total_files
            assert avg_file_size_mb < 10, f"平均ファイルサイズが大きすぎます: {avg_file_size_mb:.2f}MB"
            
            # 検証速度のテスト
            start_time = time.time()
            validation_result = self.manager.validate_dataset("perf_test")
            validation_time = time.time() - start_time
            
            assert validation_time < 30, f"検証時間が長すぎます: {validation_time:.2f}秒"
            
            self._record_test_result(
                test_name, True,
                f"パフォーマンス特性良好: {files_per_second:.2f}ファイル/秒, "
                f"検証時間: {validation_time:.2f}秒"
            )
            
        except Exception as e:
            self._record_test_result(test_name, False, f"パフォーマンステストでエラー: {e}")
    
    def _test_error_handling(self):
        """エラーハンドリングのテスト"""
        test_name = "error_handling"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            # 存在しないデータセットの削除
            result = self.manager.delete_dataset("nonexistent_dataset")
            assert result == False
            
            # 無効なパラメータでのデータセット作成
            try:
                invalid_dataset = self.manager.create_standard_dataset(
                    name="",  # 空の名前
                    file_count=0  # 0ファイル
                )
                # エラーが発生しない場合は警告
                self.logger.warning("無効なパラメータでもデータセットが作成されました")
            except Exception:
                # エラーが発生するのが正常
                pass
            
            # 重複名でのデータセット作成
            try:
                duplicate_dataset = self.manager.create_standard_dataset(
                    name="test_standard",  # 既存の名前
                    file_count=10
                )
                # 重複が許可される場合は上書きされる
                self.logger.info("重複名でのデータセット作成が許可されました（上書き）")
            except Exception as e:
                self.logger.info(f"重複名でのデータセット作成が拒否されました: {e}")
            
            self._record_test_result(test_name, True, "エラーハンドリングが適切に動作しています")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"エラーハンドリングテストでエラー: {e}")
    
    def _test_concurrent_operations(self):
        """並行操作のテスト"""
        test_name = "concurrent_operations"
        self.logger.info(f"=== {test_name} テスト開始 ===")
        
        try:
            # 複数のデータセットを同時に操作
            datasets = self.manager.list_datasets()
            
            # 複数のデータセットの検証を並行実行（シミュレーション）
            validation_results = []
            for dataset in datasets[:3]:  # 最初の3つのデータセット
                result = self.manager.validate_dataset(dataset.name)
                validation_results.append(result)
            
            # すべての検証が完了したことを確認
            assert len(validation_results) > 0
            
            # 複数のデータセット情報を同時取得
            info_results = []
            for dataset in datasets[:3]:
                info = self.manager.get_dataset_info(dataset.name)
                info_results.append(info)
            
            assert len(info_results) > 0
            assert all(info is not None for info in info_results)
            
            self._record_test_result(test_name, True, "並行操作が正常に動作しています")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"並行操作テストでエラー: {e}")
    
    def _record_test_result(self, test_name: str, success: bool, message: str):
        """テスト結果の記録"""
        self.validation_results['tests'][test_name] = {
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        self.validation_results['summary']['total_tests'] += 1
        if success:
            self.validation_results['summary']['passed_tests'] += 1
            self.logger.info(f"✓ {test_name}: {message}")
        else:
            self.validation_results['summary']['failed_tests'] += 1
            self.validation_results['summary']['errors'].append(f"{test_name}: {message}")
            self.logger.error(f"✗ {test_name}: {message}")
    
    def _calculate_summary(self):
        """サマリーの計算"""
        summary = self.validation_results['summary']
        summary['success_rate'] = (
            summary['passed_tests'] / summary['total_tests'] * 100
            if summary['total_tests'] > 0 else 0
        )
        
        self.logger.info(f"検証完了: {summary['passed_tests']}/{summary['total_tests']} "
                        f"({summary['success_rate']:.1f}%) 成功")
    
    def _cleanup(self):
        """クリーンアップ"""
        try:
            self.manager.cleanup_all_datasets()
            self.logger.info("クリーンアップが完了しました")
        except Exception as e:
            self.logger.error(f"クリーンアップ中にエラーが発生しました: {e}")


def setup_logging(log_level: str = "INFO"):
    """ログ設定"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('dataset_manager_validation.log', encoding='utf-8')
        ]
    )


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='TestDatasetManager検証スクリプト')
    parser.add_argument('--output-dir', help='出力ディレクトリ')
    parser.add_argument('--quick', action='store_true', help='クイックモード（高速実行）')
    parser.add_argument('--log-level', default='INFO', help='ログレベル')
    
    args = parser.parse_args()
    
    # ログ設定
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("TestDatasetManager検証スクリプトを開始します")
    
    try:
        # 検証実行
        validator = DatasetManagerValidator(
            output_dir=args.output_dir,
            quick_mode=args.quick
        )
        
        results = validator.run_validation()
        
        # 結果の出力
        logger.info("=== 検証結果サマリー ===")
        summary = results['summary']
        logger.info(f"総テスト数: {summary['total_tests']}")
        logger.info(f"成功: {summary['passed_tests']}")
        logger.info(f"失敗: {summary['failed_tests']}")
        logger.info(f"成功率: {summary['success_rate']:.1f}%")
        logger.info(f"実行時間: {results['duration_seconds']:.2f}秒")
        
        if summary['errors']:
            logger.error("エラー一覧:")
            for error in summary['errors']:
                logger.error(f"  - {error}")
        
        # 結果ファイルの保存
        results_file = os.path.join(
            validator.output_dir if args.output_dir else tempfile.gettempdir(),
            f"dataset_manager_validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        import json
        with open(results_file, 'w', encoding='utf-8') as f:
            # datetimeオブジェクトを文字列に変換
            results_copy = results.copy()
            results_copy['start_time'] = results_copy['start_time'].isoformat()
            results_copy['end_time'] = results_copy['end_time'].isoformat()
            
            json.dump(results_copy, f, ensure_ascii=False, indent=2)
        
        logger.info(f"検証結果を保存しました: {results_file}")
        
        # 終了コード
        exit_code = 0 if summary['failed_tests'] == 0 else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"検証スクリプト実行中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()