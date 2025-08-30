#!/usr/bin/env python3
"""
TestDatasetManager使用例

TestDatasetManagerクラスの基本的な使用方法を示すサンプルスクリプトです。
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.test_dataset_manager import TestDatasetManager


def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('dataset_manager_example.log', encoding='utf-8')
        ]
    )


def main():
    """メイン関数"""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("TestDatasetManager使用例を開始します")

    # 一時ディレクトリでテストデータセット管理システムを初期化
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"一時ディレクトリを使用します: {temp_dir}")

        # TestDatasetManagerの初期化
        manager = TestDatasetManager(base_directory=temp_dir)
        logger.info("TestDatasetManagerを初期化しました")

        try:
            # 1. 標準テストデータセットの作成
            logger.info("=== 標準テストデータセットの作成 ===")
            standard_dataset = manager.create_standard_dataset(
                name="example_standard",
                file_count=10  # 例のため小さな数値
            )

            logger.info("標準データセット作成完了:")
            logger.info(f"  - ファイル数: {standard_dataset.metrics.total_files}")
            logger.info(f"  - 総サイズ: {standard_dataset.metrics.total_size_mb:.2f}MB")
            logger.info(f"  - 生成時間: {standard_dataset.metrics.generation_time_seconds:.2f}秒")

            # 2. エッジケーステストデータセットの作成
            logger.info("=== エッジケーステストデータセットの作成 ===")
            edge_case_dataset = manager.create_edge_case_dataset(
                name="example_edge_case",
                file_count=8  # 例のため小さな数値
            )

            logger.info("エッジケースデータセット作成完了:")
            logger.info(f"  - ファイル数: {edge_case_dataset.metrics.total_files}")
            logger.info(f"  - 破損ファイル数: {edge_case_dataset.metrics.corrupted_files}")
            logger.info(f"  - 大容量ファイル数: {edge_case_dataset.metrics.large_files}")
            logger.info(f"  - 特殊文字ファイル数: {edge_case_dataset.metrics.special_char_files}")

            # 3. データセット一覧の表示
            logger.info("=== データセット一覧 ===")
            datasets = manager.list_datasets()
            for dataset in datasets:
                logger.info(f"データセット: {dataset.name}")
                logger.info(f"  - タイプ: {dataset.dataset_type}")
                logger.info(f"  - 状態: {dataset.status}")
                logger.info(f"  - パス: {dataset.path}")
                logger.info(f"  - 作成日時: {dataset.created_at}")

            # 4. データセットの検証
            logger.info("=== データセットの検証 ===")
            for dataset_name in ["example_standard", "example_edge_case"]:
                validation_result = manager.validate_dataset(dataset_name)
                logger.info(f"データセット '{dataset_name}' の検証結果:")
                logger.info(f"  - 有効: {validation_result['valid']}")
                logger.info(f"  - ファイル数: {validation_result['file_count']}")
                logger.info(f"  - 総サイズ: {validation_result['total_size_mb']:.2f}MB")

                if validation_result['errors']:
                    logger.warning(f"  - エラー: {validation_result['errors']}")
                if validation_result['warnings']:
                    logger.warning(f"  - 警告: {validation_result['warnings']}")

            # 5. データセット内のファイル一覧取得
            logger.info("=== ファイル一覧の取得 ===")
            files = manager.get_dataset_files("example_standard")
            logger.info(f"標準データセット内のファイル数: {len(files)}")

            # 最初の5ファイルを表示
            for i, file_path in enumerate(files[:5]):
                logger.info(f"  {i+1}. {os.path.basename(file_path)}")

            if len(files) > 5:
                logger.info(f"  ... 他 {len(files) - 5} ファイル")

            # 6. 生成状況の確認
            logger.info("=== 生成状況の確認 ===")
            for dataset_name in ["example_standard", "example_edge_case"]:
                status = manager.get_generation_status(dataset_name)
                logger.info(f"データセット '{dataset_name}' の状況:")
                logger.info(f"  - 状態: {status['status']}")
                logger.info(f"  - 生成中: {status['is_generating']}")

            # 7. 大規模データセットの作成（小さなサイズで実演）
            logger.info("=== 小規模な大規模データセットの作成 ===")
            small_large_dataset = manager.create_large_dataset(
                name="example_small_large",
                file_count=15  # 実際は50,000だが例のため小さく
            )

            logger.info("小規模大規模データセット作成完了:")
            logger.info(f"  - ファイル数: {small_large_dataset.metrics.total_files}")
            logger.info(f"  - 総サイズ: {small_large_dataset.metrics.total_size_mb:.2f}MB")
            logger.info("  - ファイル形式別:")
            for file_type, count in small_large_dataset.metrics.file_types.items():
                logger.info(f"    - {file_type}: {count}ファイル")

            # 8. 包括的テストスイートの生成（小規模版）
            logger.info("=== 包括的テストスイートの生成 ===")

            # 新しいマネージャーインスタンスで実演
            suite_temp_dir = os.path.join(temp_dir, "comprehensive_suite")
            suite_manager = TestDatasetManager(base_directory=suite_temp_dir)

            # 小規模版の包括的テストスイート
            logger.info("小規模版の包括的テストスイートを生成します...")

            # 個別に小さなデータセットを作成
            suite_datasets = {}

            suite_datasets['standard'] = suite_manager.create_standard_dataset(
                name="suite_standard",
                file_count=5
            )

            suite_datasets['edge_case'] = suite_manager.create_edge_case_dataset(
                name="suite_edge_case",
                file_count=5
            )

            suite_datasets['large'] = suite_manager.create_large_dataset(
                name="suite_large",
                file_count=8  # 実際は10,000だが例のため小さく
            )

            logger.info("包括的テストスイート生成完了:")
            for suite_type, dataset in suite_datasets.items():
                logger.info(f"  - {suite_type}: {dataset.metrics.total_files}ファイル, "
                          f"{dataset.metrics.total_size_mb:.2f}MB")

            # 9. データセットの削除
            logger.info("=== データセットの削除 ===")
            datasets_to_delete = ["example_standard", "example_edge_case", "example_small_large"]

            for dataset_name in datasets_to_delete:
                success = manager.delete_dataset(dataset_name)
                if success:
                    logger.info(f"データセット '{dataset_name}' を削除しました")
                else:
                    logger.error(f"データセット '{dataset_name}' の削除に失敗しました")

            # 最終的なデータセット一覧
            logger.info("=== 最終データセット一覧 ===")
            remaining_datasets = manager.list_datasets()
            logger.info(f"残りのデータセット数: {len(remaining_datasets)}")

            for dataset in remaining_datasets:
                logger.info(f"  - {dataset.name} ({dataset.dataset_type})")

        except Exception as e:
            logger.error(f"実行中にエラーが発生しました: {e}")
            raise

        finally:
            # クリーンアップ
            logger.info("=== クリーンアップ ===")
            manager.cleanup_all_datasets()
            logger.info("すべてのデータセットをクリーンアップしました")

    logger.info("TestDatasetManager使用例が完了しました")


if __name__ == "__main__":
    main()
