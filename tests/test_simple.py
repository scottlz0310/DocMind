"""
簡単なテスト - Phase5テスト環境の動作確認用
"""

import pytest


def test_basic_math():
    """基本的な数学テスト"""
    assert 1 + 1 == 2
    assert 2 * 3 == 6


def test_string_operations():
    """文字列操作テスト"""
    text = "Hello, World!"
    assert len(text) == 13
    assert text.lower() == "hello, world!"


def test_list_operations():
    """リスト操作テスト"""
    items = [1, 2, 3, 4, 5]
    assert len(items) == 5
    assert sum(items) == 15


@pytest.mark.unit
def test_with_marker():
    """マーカー付きテスト"""
    assert True


def test_mock_usage():
    """モック使用テスト"""
    from unittest.mock import Mock
    
    mock_obj = Mock()
    mock_obj.method.return_value = "test_result"
    
    result = mock_obj.method()
    assert result == "test_result"
    mock_obj.method.assert_called_once()