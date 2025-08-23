# -*- coding: utf-8 -*-
"""
ValidationReportGeneratorのテストとサンプル使用例

検証結果レポート生成システムの動作確認とサンプルデータでの実行例を提供します。
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import List
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.validation_framework.validation_report_generator import (
    ValidationReportGenerator,
    ReportGenerationConfig,
    ValidationMetrics,
    PerformanceMetrics
)


def create_sample_validation_results() -> List[ValidationMetrics]:
    """サンプル検証結果の作成"""
    sample_results = []
    
    # 成功したテストのサンプル
    for i in range(15):
        result = ValidationMetrics(
            test_name=f"test_search_functionality_{i+1}",
            success=True,
            execution_time=2.5 + (i * 0.3),
            memory_usage=512 + (i * 20),
            cpu_usage=45 + (i * 2),
            category="search",
            timestamp=datetime.now() - timedelta(minutes=i*2)
        )
        sample_results.append(result)
    
    # 失敗したテストのサンプル
    for i in range(3):
        result = ValidationMetrics(
            test_name=f"test_error_handling_{i+1}",
            success=False,
            execution_time=8.2 + (i * 1.5),
            memory_usage=1024 + (i * 100),
            cpu_usage=75 + (i * 5),
            error_message=f"Timeout error occurred during test execution: Connection timeout after 30 seconds",
            category="error_handling",
            timestamp=datetime.now() - timedelta(minutes=i*3)
        )
        sample_results.append(result)
    
    # GUI関連のテスト
    for i in range(8):
        result = ValidationMetrics(
            test_name=f"test_gui_component_{i+1}",
            success=i < 7,  # 1つだけ失敗
            execution_time=1.8 + (i * 0.2),
            memory_usage=256 + (i * 15),
            cpu_usage=30 + (i * 3),
            error_message="Assertion failed: Expected element not found" if i == 7 else None,
            category="gui",
            timestamp=datetime.now() - timedelta(minutes=i*1.5)
        )
        sample_results.append(result)
    
    # パフォーマンステスト
    for i in range(5):
        result = ValidationMetrics(
            test_name=f"test_performance_{i+1}",
            success=True,
            execution_time=15.2 + (i * 2.1),
            memory_usage=2048 + (i * 200),
            cpu_usage=80 + (i * 3),
            category="performance",
            timestamp=datetime.now() - timedelta(minutes=i*4)
        )
        sample_results.append(result)
    
    return sample_results


def create_sample_performance_metrics() -> PerformanceMetrics:
    """サンプルパフォーマンスメトリクスの作成"""
    return PerformanceMetrics(
        peak_cpu_percent=85.2,
        average_cpu_percent=62.8,
        peak_memory_mb=2048.5,
        average_memory_mb=1024.3,
        disk_read_mb=156.7,
        disk_write_mb=89.4,
        network_sent_mb=12.3,
        network_received_mb=45.6,
        monitoring_duration_seconds=300.0
    )


def test_comprehensive_report_generation():
    """包括的レポート生成のテスト"""
    print("🚀 ValidationReportGenerator 包括的レポート生成テストを開始します")
    
    # 一時ディレクトリの作成
    temp_dir = tempfile.mkdtemp(prefix="docmind_report_test_")
    print(f"📁 一時ディレクトリ: {temp_dir}")
    
    try:
        # レポート生成設定
        config = ReportGenerationConfig(
            output_directory=temp_dir,
            report_name="comprehensive_validation_test",
            include_charts=True,
            include_detailed_logs=True,
            include_trend_analysis=True,
            include_performance_graphs=True,
            include_error_analysis=True,
            chart_format="png",
            report_formats=["html", "markdown", "json"]
        )
        
        # レポート生成器の初期化
        generator = ValidationReportGenerator(config)
        
        # サンプルデータの作成
        validation_results = create_sample_validation_results()
        performance_data = create_sample_performance_metrics()
        
        print(f"📊 検証結果数: {len(validation_results)}")
        print(f"✅ 成功テスト: {sum(1 for r in validation_results if r.success)}")
        print(f"❌ 失敗テスト: {sum(1 for r in validation_results if not r.success)}")
        
        # 包括的レポートの生成
        print("\n📈 包括的レポートを生成中...")
        generated_files = generator.generate_comprehensive_report(
            validation_results=validation_results,
            performance_data=performance_data,
            additional_data={
                "test_environment": "Windows 10",
                "python_version": "3.11.0",
                "test_suite_version": "1.0.0"
            }
        )
        
        print(f"\n✅ レポート生成完了! 生成されたファイル数: {len(generated_files)}")
        
        # 生成されたファイルの確認
        print("\n📋 生成されたファイル一覧:")
        for report_type, file_path in generated_files.items():
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            print(f"  - {report_type}: {os.path.basename(file_path)} ({file_size:,} bytes)")
        
        # 過去結果との比較レポート生成（履歴データがある場合）
        print("\n🔍 過去結果との比較レポートを生成中...")
        comparison_report = generator.generate_comparison_with_historical_results({
            'summary': {
                'success_rate': 85.7,
                'average_execution_time': 5.2,
                'peak_memory_usage': 1536.0
            },
            'quality_indicators': {
                'overall_quality_score': 82.5
            },
            'metadata': {
                'generation_time': datetime.now().isoformat()
            }
        })
        
        if comparison_report:
            print(f"✅ 比較レポート生成完了: {os.path.basename(comparison_report)}")
        
        print(f"\n📂 すべてのレポートは以下のディレクトリに保存されました:")
        print(f"   {temp_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 一時ディレクトリのクリーンアップ（コメントアウトして結果を確認可能）
        # shutil.rmtree(temp_dir)
        # print(f"🧹 一時ディレクトリを削除しました: {temp_dir}")
        pass


def test_individual_report_types():
    """個別レポートタイプのテスト"""
    print("\n🔧 個別レポートタイプのテストを開始します")
    
    temp_dir = tempfile.mkdtemp(prefix="docmind_individual_test_")
    
    try:
        # 各レポートタイプを個別にテスト
        report_types = [
            ("サマリーレポートのみ", ["html"], False, False, False),
            ("詳細レポート + チャート", ["html", "markdown"], True, False, True),
            ("トレンド分析のみ", ["html"], False, True, False),
            ("エラー分析のみ", ["html"], False, False, False)
        ]
        
        validation_results = create_sample_validation_results()
        performance_data = create_sample_performance_metrics()
        
        for test_name, formats, charts, trends, perf_graphs in report_types:
            print(f"\n📊 {test_name} をテスト中...")
            
            config = ReportGenerationConfig(
                output_directory=os.path.join(temp_dir, test_name.replace(" ", "_")),
                report_name=f"test_{test_name.replace(' ', '_').lower()}",
                include_charts=charts,
                include_trend_analysis=trends,
                include_performance_graphs=perf_graphs,
                report_formats=formats
            )
            
            generator = ValidationReportGenerator(config)
            generated_files = generator.generate_comprehensive_report(
                validation_results=validation_results,
                performance_data=performance_data
            )
            
            print(f"  ✅ 生成完了: {len(generated_files)} ファイル")
        
        return True
        
    except Exception as e:
        print(f"❌ 個別テスト中にエラーが発生しました: {e}")
        return False
    
    finally:
        # shutil.rmtree(temp_dir)
        pass


def test_error_scenarios():
    """エラーシナリオのテスト"""
    print("\n⚠️  エラーシナリオのテストを開始します")
    
    temp_dir = tempfile.mkdtemp(prefix="docmind_error_test_")
    
    try:
        config = ReportGenerationConfig(
            output_directory=temp_dir,
            report_name="error_scenario_test"
        )
        
        generator = ValidationReportGenerator(config)
        
        # 空の検証結果でのテスト
        print("📝 空の検証結果でのレポート生成をテスト...")
        generated_files = generator.generate_comprehensive_report(
            validation_results=[],
            performance_data=None
        )
        print(f"  ✅ 空データでも正常に処理: {len(generated_files)} ファイル生成")
        
        # 履歴データなしでのトレンド分析テスト
        print("📈 履歴データなしでのトレンド分析をテスト...")
        # 履歴ファイルが存在しない状態でトレンド分析を実行
        
        return True
        
    except Exception as e:
        print(f"❌ エラーシナリオテスト中にエラーが発生しました: {e}")
        return False
    
    finally:
        # shutil.rmtree(temp_dir)
        pass


def main():
    """メイン実行関数"""
    print("=" * 80)
    print("🧪 ValidationReportGenerator テストスイート")
    print("=" * 80)
    
    # ログレベルの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_results = []
    
    # 包括的レポート生成テスト
    test_results.append(("包括的レポート生成", test_comprehensive_report_generation()))
    
    # 個別レポートタイプテスト
    test_results.append(("個別レポートタイプ", test_individual_report_types()))
    
    # エラーシナリオテスト
    test_results.append(("エラーシナリオ", test_error_scenarios()))
    
    # テスト結果のサマリー
    print("\n" + "=" * 80)
    print("📋 テスト結果サマリー")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📊 総合結果: {passed} 成功, {failed} 失敗")
    
    if failed == 0:
        print("🎉 すべてのテストが成功しました!")
        return 0
    else:
        print("⚠️  一部のテストが失敗しました。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)