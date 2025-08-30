"""
包括的テストスイート検証

テストスイート全体の動作確認と統計情報の収集
"""

import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestSuiteValidator:
    """テストスイート検証クラス"""

    def __init__(self):
        """初期化"""
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        self.src_dir = self.project_root / "src"

    def discover_test_files(self) -> list[Path]:
        """テストファイルを発見"""
        test_files = []
        for test_file in self.test_dir.rglob("test_*.py"):
            if test_file.name != "__init__.py":
                test_files.append(test_file)
        return test_files

    def analyze_test_coverage(self) -> dict[str, Any]:
        """テストカバレッジを分析"""
        test_files = self.discover_test_files()
        src_files = list(self.src_dir.rglob("*.py"))

        # 除外するファイル
        excluded_files = {"__init__.py", "__pycache__"}
        src_files = [f for f in src_files if f.name not in excluded_files]

        coverage_info = {
            "total_test_files": len(test_files),
            "total_source_files": len(src_files),
            "test_files": [str(f.relative_to(self.project_root)) for f in test_files],
            "source_files": [str(f.relative_to(self.project_root)) for f in src_files],
            "coverage_ratio": len(test_files) / len(src_files) if src_files else 0,
        }

        return coverage_info

    def validate_test_structure(self) -> dict[str, Any]:
        """テスト構造を検証"""
        validation_results = {
            "conftest_exists": (self.test_dir / "conftest.py").exists(),
            "fixtures_dir_exists": (self.test_dir / "fixtures").exists(),
            "pytest_ini_exists": (self.project_root / "pytest.ini").exists(),
            "run_tests_script_exists": (self.project_root / "run_tests.py").exists(),
            "test_data_generator_exists": (
                self.test_dir / "test_data_generator.py"
            ).exists(),
        }

        # フィクスチャファイルの確認
        fixtures_dir = self.test_dir / "fixtures"
        if fixtures_dir.exists():
            fixture_files = list(fixtures_dir.glob("*"))
            validation_results["fixture_files"] = [f.name for f in fixture_files]
            validation_results["fixture_count"] = len(fixture_files)
        else:
            validation_results["fixture_files"] = []
            validation_results["fixture_count"] = 0

        return validation_results

    def check_dependencies(self) -> dict[str, Any]:
        """テスト依存関係を確認"""
        required_packages = ["pytest", "pytest-cov", "pytest-mock", "psutil"]

        optional_packages = ["PySide6", "reportlab", "python-docx", "openpyxl"]

        dependency_status = {"required": {}, "optional": {}}

        # 必須パッケージの確認
        for package in required_packages:
            try:
                spec = importlib.util.find_spec(package.replace("-", "_"))
                dependency_status["required"][package] = spec is not None
            except ImportError:
                dependency_status["required"][package] = False

        # オプションパッケージの確認
        for package in optional_packages:
            try:
                spec = importlib.util.find_spec(package)
                dependency_status["optional"][package] = spec is not None
            except ImportError:
                dependency_status["optional"][package] = False

        return dependency_status


@pytest.mark.unit
class TestComprehensiveTestSuite:
    """包括的テストスイートのテスト"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """テストセットアップ"""
        self.validator = TestSuiteValidator()
        yield

    def test_test_suite_structure(self):
        """テストスイート構造の検証"""
        structure = self.validator.validate_test_structure()

        # 必須ファイルの存在確認
        assert structure["conftest_exists"], "conftest.pyが存在しません"
        assert structure["fixtures_dir_exists"], "fixturesディレクトリが存在しません"
        assert structure["pytest_ini_exists"], "pytest.iniが存在しません"
        assert structure["run_tests_script_exists"], "run_tests.pyが存在しません"
        assert structure[
            "test_data_generator_exists"
        ], "test_data_generator.pyが存在しません"

        # フィクスチャファイルの確認
        assert structure["fixture_count"] > 0, "フィクスチャファイルが存在しません"

        print("✓ テストスイート構造検証完了:")
        print(f"  - フィクスチャファイル数: {structure['fixture_count']}")
        print(f"  - フィクスチャファイル: {', '.join(structure['fixture_files'])}")

    def test_test_coverage_analysis(self):
        """テストカバレッジ分析"""
        coverage = self.validator.analyze_test_coverage()

        # 基本的なカバレッジ要件
        assert coverage["total_test_files"] > 0, "テストファイルが存在しません"
        assert coverage["total_source_files"] > 0, "ソースファイルが存在しません"
        assert (
            coverage["coverage_ratio"] > 0.5
        ), f"テストカバレッジが低すぎます: {coverage['coverage_ratio']:.2f}"

        print("✓ テストカバレッジ分析完了:")
        print(f"  - テストファイル数: {coverage['total_test_files']}")
        print(f"  - ソースファイル数: {coverage['total_source_files']}")
        print(f"  - カバレッジ比率: {coverage['coverage_ratio']:.2f}")

    def test_dependency_availability(self):
        """依存関係の可用性テスト"""
        dependencies = self.validator.check_dependencies()

        # 必須依存関係の確認
        required_missing = [
            pkg for pkg, available in dependencies["required"].items() if not available
        ]
        assert len(required_missing) == 0, f"必須パッケージが不足: {required_missing}"

        # オプション依存関係の確認（警告のみ）
        optional_missing = [
            pkg for pkg, available in dependencies["optional"].items() if not available
        ]
        if optional_missing:
            print(f"⚠️  オプションパッケージが不足: {optional_missing}")
            print("   一部のテストがスキップされる可能性があります")

        print("✓ 依存関係確認完了:")
        print(f"  - 必須パッケージ: {len(dependencies['required'])}個すべて利用可能")
        print(
            f"  - オプションパッケージ: {len([p for p in dependencies['optional'].values() if p])}個利用可能"
        )

    def test_test_data_generator_functionality(self):
        """テストデータジェネレーター機能テスト"""
        # 一時的なテストデータジェネレーターを作成
        import tempfile

        from tests.test_data_generator import TestDataGenerator

        with tempfile.TemporaryDirectory() as temp_dir:
            generator = TestDataGenerator(temp_dir)

            # 基本的なファイル生成テスト
            text_files = generator.create_text_files(count=3)
            assert len(text_files) == 3, "テキストファイル生成に失敗"

            markdown_files = generator.create_markdown_files(count=2)
            assert len(markdown_files) == 2, "Markdownファイル生成に失敗"

            # 生成されたファイルの存在確認
            for file_path in text_files + markdown_files:
                assert (
                    file_path.exists()
                ), f"生成されたファイルが存在しません: {file_path}"
                assert (
                    file_path.stat().st_size > 0
                ), f"生成されたファイルが空です: {file_path}"

        print("✓ テストデータジェネレーター機能テスト完了")

    def test_fixture_files_accessibility(self):
        """フィクスチャファイルのアクセス可能性テスト"""
        fixtures_dir = Path(__file__).parent / "fixtures"

        # 基本フィクスチャファイルの確認
        expected_fixtures = [
            "sample_text.txt",
            "sample_markdown.md",
            "sample_json.json",
            "sample_csv.csv",
        ]

        for fixture_name in expected_fixtures:
            fixture_path = fixtures_dir / fixture_name
            assert (
                fixture_path.exists()
            ), f"フィクスチャファイルが存在しません: {fixture_name}"

            # ファイルの読み込みテスト
            try:
                content = fixture_path.read_text(encoding="utf-8")
                assert len(content) > 0, f"フィクスチャファイルが空です: {fixture_name}"
            except Exception as e:
                pytest.fail(
                    f"フィクスチャファイルの読み込みに失敗: {fixture_name} - {e}"
                )

        print(
            f"✓ フィクスチャファイルアクセス可能性テスト完了: {len(expected_fixtures)}ファイル"
        )

    def test_test_execution_performance(self):
        """テスト実行パフォーマンステスト"""
        # 簡単なテスト実行時間を測定
        start_time = time.time()

        # ダミーテストを実行
        for i in range(100):
            assert i >= 0  # 簡単なアサーション

        execution_time = time.time() - start_time

        # テスト実行が合理的な時間内に完了することを確認
        assert (
            execution_time < 1.0
        ), f"テスト実行時間が長すぎます: {execution_time:.3f}秒"

        print(f"✓ テスト実行パフォーマンステスト完了: {execution_time:.3f}秒")

    def test_comprehensive_suite_metadata(self):
        """包括的テストスイートメタデータテスト"""
        # テストスイートの統計情報を収集
        validator = TestSuiteValidator()

        metadata = {
            "test_structure": validator.validate_test_structure(),
            "coverage_analysis": validator.analyze_test_coverage(),
            "dependencies": validator.check_dependencies(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # メタデータの基本検証
        assert metadata["test_structure"][
            "conftest_exists"
        ], "conftest.pyが見つかりません"
        assert (
            metadata["coverage_analysis"]["total_test_files"] > 10
        ), "テストファイル数が不十分"
        assert all(metadata["dependencies"]["required"].values()), "必須依存関係が不足"

        # メタデータをファイルに保存（デバッグ用）
        metadata_file = (
            Path(__file__).parent.parent / "test_results" / "suite_metadata.json"
        )
        metadata_file.parent.mkdir(exist_ok=True)

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print("✓ 包括的テストスイートメタデータテスト完了")
        print(f"  - メタデータファイル: {metadata_file}")


@pytest.mark.integration
class TestTestSuiteIntegration:
    """テストスイート統合テスト"""

    def test_pytest_configuration_integration(self):
        """pytest設定統合テスト"""
        # pytest.iniファイルの存在と内容確認
        pytest_ini = Path(__file__).parent.parent / "pytest.ini"
        assert pytest_ini.exists(), "pytest.iniが存在しません"

        content = pytest_ini.read_text(encoding="utf-8")

        # 重要な設定項目の確認
        assert "testpaths = tests" in content, "testpaths設定が見つかりません"
        assert "--cov=src" in content, "カバレッジ設定が見つかりません"
        assert "markers =" in content, "マーカー設定が見つかりません"

        print("✓ pytest設定統合テスト完了")

    def test_test_runner_script_integration(self):
        """テスト実行スクリプト統合テスト"""
        run_tests_script = Path(__file__).parent.parent / "run_tests.py"
        assert run_tests_script.exists(), "run_tests.pyが存在しません"

        # スクリプトの基本的な構文チェック
        try:
            with open(run_tests_script, encoding="utf-8") as f:
                script_content = f.read()

            # 基本的な構文チェック
            compile(script_content, str(run_tests_script), "exec")

        except SyntaxError as e:
            pytest.fail(f"テスト実行スクリプトに構文エラー: {e}")

        print("✓ テスト実行スクリプト統合テスト完了")

    def test_end_to_end_test_workflow(self):
        """エンドツーエンドテストワークフロー"""
        # テストスイート全体の動作確認
        validator = TestSuiteValidator()

        # 1. 構造検証
        structure = validator.validate_test_structure()
        assert all(
            [
                structure["conftest_exists"],
                structure["fixtures_dir_exists"],
                structure["pytest_ini_exists"],
            ]
        ), "テストスイート構造に問題があります"

        # 2. 依存関係確認
        dependencies = validator.check_dependencies()
        required_available = all(dependencies["required"].values())
        assert required_available, "必須依存関係が不足しています"

        # 3. テストデータ生成確認
        import tempfile

        from tests.test_data_generator import TestDataGenerator

        with tempfile.TemporaryDirectory() as temp_dir:
            generator = TestDataGenerator(temp_dir)
            test_files = generator.create_text_files(count=2)
            assert len(test_files) == 2, "テストデータ生成に失敗"

        print("✓ エンドツーエンドテストワークフロー完了")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
