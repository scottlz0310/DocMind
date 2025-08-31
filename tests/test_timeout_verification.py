"""
タイムアウト設定の動作確認用テスト
"""
import time
import pytest


def test_quick_operation():
    """短時間で完了するテスト"""
    time.sleep(0.1)
    assert True


@pytest.mark.timeout(5)
def test_with_custom_timeout():
    """カスタムタイムアウト設定のテスト（5秒）"""
    time.sleep(2)
    assert True


@pytest.mark.skip(reason="意図的なタイムアウトテスト")
def test_long_operation():
    """長時間実行されるテスト（デフォルトタイムアウト60秒でキャンセルされるはず）"""
    # このテストは60秒のタイムアウトでキャンセルされる
    time.sleep(70)
    assert True  # ここには到達しない