#!/usr/bin/env python3
"""
統合テスト実行スクリプト

全ての統合テストとデバッグ機能テストを実行し、レポートを生成する
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class IntegrationTestRunner:
    """統合テスト実行クラス"""

    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else project_root / "test_reports"
        self.output_dir.mkdir(exist_ok=True)

        self.test_results = {
            'start_time': datetime.now(),
            'test_suites': {},
            'summary': {},
            'end_time': None
        }

    def run_test_suite(self, test_file, suite_name, markers=None):
        """個別のテストスイートを実行"""
        print(f"\n{'='*60}")
        print(f"テストスイート実行: {suite_name}")
        print(f"ファイル: {test_file}")
        print(f"{'='*60}")

        start_time = time.time()

        # pytestコマンドを構築
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            "--json-report",
            f"--json-report-file={self.output_dir / f'{suite_name}_report.json'}"
        ]

        # マーカーが指定されている場合は追加
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])

        try:
            # テスト実行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root
            )

            execution_time = time.time() - start_time

            # 結果を記録
            suite_result = {
                'suite_name': suite_name,
                'test_file': str(test_file),
                'execution_time': execution_time,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0,
                'timestamp': datetime.now().isoformat()
            }

            # JSON レポートファイルが存在する場合は読み込み
            json_report_file = self.output_dir / f'{suite_name}_report.json'
            if json_report_file.exists():
                try:
                    with open(json_report_file, encoding='utf-8') as f:
                        json_data = json.load(f)
                        suite_result['detailed_results'] = json_data
                except Exception as e:
                    suite_result['json_parse_error'] = str(e)

            self.test_results['test_suites'][suite_name] = suite_result

            # 結果表示
            if result.returncode == 0:
                print(f"✓ {suite_name} 成功 ({execution_time:.2f}秒)")
            else:
                print(f"✗ {suite_name} 失敗 ({execution_time:.2f}秒)")
                print(f"エラー出力:\n{result.stderr}")

            return suite_result

        except Exception as e:
            error_result = {
                'suite_name': suite_name,
                'test_file': str(test_file),
                'execution_time': time.time() - start_time,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }

            self.test_results['test_suites'][suite_name] = error_result
            print(f"✗ {suite_name} 実行エラー: {e}")

            return error_result

    def run_all_integration_tests(self, include_slow=False, include_performance=False):
        """全ての統合テストを実行"""
        print("統合テスト実行を開始します...")

        # テストスイート定義
        test_suites = [
            {
                'file': 'tests/test_indexing_worker_integration.py',
                'name': 'indexing_worker_integration',
                'markers': ['integration']
            },
            {
                'file': 'tests/test_error_cases_and_debugging.py',
                'name': 'error_cases_and_debugging',
                'markers': ['integration']
            },
            {
                'file': 'tests/test_comprehensive_integration_suite.py',
                'name': 'comprehensive_integration_suite',
                'markers': ['integration']
            },
            {
                'file': 'tests/test_end_to_end_integration.py',
                'name': 'end_to_end_integration',
                'markers': ['integration']
            }
        ]

        # パフォーマンステストを含める場合
        if include_performance:
            test_suites.append({
                'file': 'tests/test_large_scale_performance.py',
                'name': 'large_scale_performance',
                'markers': ['performance']
            })

        # 低速テストを含める場合
        if include_slow:
            for suite in test_suites:
                if 'slow' not in suite['markers']:
                    suite['markers'].append('slow')

        # 各テストスイートを実行
        for suite_config in test_suites:
            test_file = project_root / suite_config['file']

            if test_file.exists():
                self.run_test_suite(
                    test_file,
                    suite_config['name'],
                    suite_config['markers']
                )
            else:
                print(f"警告: テストファイルが見つかりません: {test_file}")

    def generate_summary_report(self):
        """サマリーレポートを生成"""
        self.test_results['end_time'] = datetime.now()

        # サマリー統計を計算
        total_suites = len(self.test_results['test_suites'])
        successful_suites = sum(
            1 for result in self.test_results['test_suites'].values()
            if result.get('success', False)
        )
        failed_suites = total_suites - successful_suites

        total_execution_time = sum(
            result.get('execution_time', 0)
            for result in self.test_results['test_suites'].values()
        )

        self.test_results['summary'] = {
            'total_suites': total_suites,
            'successful_suites': successful_suites,
            'failed_suites': failed_suites,
            'success_rate': (successful_suites / total_suites * 100) if total_suites > 0 else 0,
            'total_execution_time': total_execution_time,
            'overall_success': failed_suites == 0
        }

        # レポートファイルに保存
        report_file = self.output_dir / f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n{'='*60}")
            print("統合テスト実行完了")
            print(f"{'='*60}")
            print(f"総テストスイート数: {total_suites}")
            print(f"成功: {successful_suites}")
            print(f"失敗: {failed_suites}")
            print(f"成功率: {self.test_results['summary']['success_rate']:.1f}%")
            print(f"総実行時間: {total_execution_time:.2f}秒")
            print(f"レポートファイル: {report_file}")
            print(f"{'='*60}")

            return report_file

        except Exception as e:
            print(f"レポート生成エラー: {e}")
            return None

    def generate_html_report(self, json_report_file):
        """HTMLレポートを生成"""
        try:
            with open(json_report_file, encoding='utf-8') as f:
                data = json.load(f)

            html_content = self._create_html_report(data)

            html_file = json_report_file.with_suffix('.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"HTMLレポート生成完了: {html_file}")
            return html_file

        except Exception as e:
            print(f"HTMLレポート生成エラー: {e}")
            return None

    def _create_html_report(self, data):
        """HTMLレポートコンテンツを作成"""
        summary = data.get('summary', {})

        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocMind 統合テストレポート</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .summary {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .metric {{ background-color: #e9ecef; padding: 15px; border-radius: 8px; text-align: center; flex: 1; }}
        .metric.success {{ background-color: #d4edda; color: #155724; }}
        .metric.failure {{ background-color: #f8d7da; color: #721c24; }}
        .test-suite {{ border: 1px solid #dee2e6; border-radius: 8px; margin-bottom: 15px; }}
        .suite-header {{ background-color: #f8f9fa; padding: 15px; border-bottom: 1px solid #dee2e6; }}
        .suite-content {{ padding: 15px; }}
        .success {{ color: #28a745; }}
        .failure {{ color: #dc3545; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>DocMind 統合テストレポート</h1>
        <p class="timestamp">実行日時: {data.get('start_time', 'N/A')} - {data.get('end_time', 'N/A')}</p>
    </div>

    <div class="summary">
        <div class="metric {'success' if summary.get('overall_success') else 'failure'}">
            <h3>総合結果</h3>
            <p>{'成功' if summary.get('overall_success') else '失敗'}</p>
        </div>
        <div class="metric">
            <h3>テストスイート数</h3>
            <p>{summary.get('total_suites', 0)}</p>
        </div>
        <div class="metric success">
            <h3>成功</h3>
            <p>{summary.get('successful_suites', 0)}</p>
        </div>
        <div class="metric failure">
            <h3>失敗</h3>
            <p>{summary.get('failed_suites', 0)}</p>
        </div>
        <div class="metric">
            <h3>成功率</h3>
            <p>{summary.get('success_rate', 0):.1f}%</p>
        </div>
        <div class="metric">
            <h3>実行時間</h3>
            <p>{summary.get('total_execution_time', 0):.2f}秒</p>
        </div>
    </div>

    <h2>テストスイート詳細</h2>
"""

        # 各テストスイートの詳細
        for suite_name, suite_data in data.get('test_suites', {}).items():
            success = suite_data.get('success', False)
            status_class = 'success' if success else 'failure'
            status_text = '成功' if success else '失敗'

            html += f"""
    <div class="test-suite">
        <div class="suite-header">
            <h3>{suite_name} <span class="{status_class}">({status_text})</span></h3>
            <p>実行時間: {suite_data.get('execution_time', 0):.2f}秒</p>
        </div>
        <div class="suite-content">
            <p><strong>ファイル:</strong> {suite_data.get('test_file', 'N/A')}</p>
            <p><strong>タイムスタンプ:</strong> {suite_data.get('timestamp', 'N/A')}</p>
"""

            if not success and 'stderr' in suite_data:
                html += f"""
            <h4>エラー詳細:</h4>
            <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto;">{suite_data['stderr']}</pre>
"""

            html += """
        </div>
    </div>
"""

        html += """
</body>
</html>
"""

        return html


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='DocMind 統合テスト実行スクリプト')
    parser.add_argument('--output-dir', '-o', help='出力ディレクトリ')
    parser.add_argument('--include-slow', '-s', action='store_true', help='低速テストを含める')
    parser.add_argument('--include-performance', '-p', action='store_true', help='パフォーマンステストを含める')
    parser.add_argument('--html', action='store_true', help='HTMLレポートを生成')

    args = parser.parse_args()

    # テストランナーを作成
    runner = IntegrationTestRunner(args.output_dir)

    try:
        # 統合テストを実行
        runner.run_all_integration_tests(
            include_slow=args.include_slow,
            include_performance=args.include_performance
        )

        # レポートを生成
        json_report = runner.generate_summary_report()

        if json_report and args.html:
            runner.generate_html_report(json_report)

        # 終了コードを設定
        overall_success = runner.test_results['summary'].get('overall_success', False)
        sys.exit(0 if overall_success else 1)

    except KeyboardInterrupt:
        print("\n統合テスト実行が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"統合テスト実行中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
