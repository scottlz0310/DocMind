"""
インデックス再構築関連データモデルのテスト

RebuildStateとRebuildProgressデータクラスの動作を検証します。
"""

import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from src.data.models import RebuildProgress, RebuildState


class TestRebuildState:
    """RebuildStateデータクラスのテスト"""

    def test_初期状態(self):
        """初期状態の確認"""
        state = RebuildState()

        assert state.thread_id is None
        assert state.start_time is None
        assert state.folder_path is None
        assert state.is_active is False
        assert state.timeout_timer is None

    def test_再構築開始(self):
        """再構築開始時の状態更新"""
        state = RebuildState()

        with tempfile.TemporaryDirectory() as temp_dir:
            thread_id = "test_thread_123"

            state.start_rebuild(thread_id, temp_dir)

            assert state.thread_id == thread_id
            assert state.folder_path == temp_dir
            assert state.is_active is True
            assert state.start_time is not None
            assert isinstance(state.start_time, datetime)

    def test_再構築停止(self):
        """再構築停止時の状態更新"""
        state = RebuildState()

        with tempfile.TemporaryDirectory() as temp_dir:
            state.start_rebuild("test_thread", temp_dir)
            assert state.is_active is True

            state.stop_rebuild()

            assert state.is_active is False
            assert state.timeout_timer is None

    def test_状態リセット(self):
        """状態リセット機能"""
        state = RebuildState()

        with tempfile.TemporaryDirectory() as temp_dir:
            state.start_rebuild("test_thread", temp_dir)
            state.timeout_timer = Mock()

            state.reset()

            assert state.thread_id is None
            assert state.start_time is None
            assert state.folder_path is None
            assert state.is_active is False
            assert state.timeout_timer is None

    def test_タイムアウト判定_未開始(self):
        """未開始状態でのタイムアウト判定"""
        state = RebuildState()

        assert state.is_timeout_exceeded() is False
        assert state.is_timeout_exceeded(30) is False

    def test_タイムアウト判定_非アクティブ(self):
        """非アクティブ状態でのタイムアウト判定"""
        state = RebuildState()
        state.start_time = datetime.now() - timedelta(hours=1)
        state.is_active = False

        assert state.is_timeout_exceeded() is False

    def test_タイムアウト判定_時間内(self):
        """タイムアウト時間内での判定"""
        state = RebuildState()

        with tempfile.TemporaryDirectory() as temp_dir:
            state.start_rebuild("test_thread", temp_dir)

            # 開始直後はタイムアウトしていない
            assert state.is_timeout_exceeded(30) is False

    def test_タイムアウト判定_超過(self):
        """タイムアウト時間超過での判定"""
        state = RebuildState()

        with tempfile.TemporaryDirectory() as temp_dir:
            state.start_rebuild("test_thread", temp_dir)
            # 過去の時刻に設定してタイムアウトをシミュレート
            state.start_time = datetime.now() - timedelta(minutes=35)

            assert state.is_timeout_exceeded(30) is True

    def test_経過時間取得_未開始(self):
        """未開始状態での経過時間取得"""
        state = RebuildState()

        assert state.get_elapsed_time() is None
        assert state.get_formatted_elapsed_time() == "未開始"

    def test_経過時間取得_開始済み(self):
        """開始済み状態での経過時間取得"""
        state = RebuildState()

        with tempfile.TemporaryDirectory() as temp_dir:
            state.start_rebuild("test_thread", temp_dir)

            elapsed = state.get_elapsed_time()
            assert elapsed is not None
            assert elapsed >= 0

            formatted = state.get_formatted_elapsed_time()
            assert "秒" in formatted

    def test_経過時間フォーマット_分単位(self):
        """分単位での経過時間フォーマット"""
        state = RebuildState()
        state.start_time = datetime.now() - timedelta(minutes=2, seconds=30)

        formatted = state.get_formatted_elapsed_time()
        assert "2分30秒" == formatted

    def test_経過時間フォーマット_時間単位(self):
        """時間単位での経過時間フォーマット"""
        state = RebuildState()
        state.start_time = datetime.now() - timedelta(hours=1, minutes=30)

        formatted = state.get_formatted_elapsed_time()
        assert "1時間30分" == formatted

    def test_バリデーション_アクティブ状態でthread_id不足(self):
        """アクティブ状態でthread_idが不足している場合のバリデーション"""
        with pytest.raises(ValueError, match="アクティブな状態ではthread_idが必要です"):
            RebuildState(is_active=True, thread_id=None)

    def test_バリデーション_アクティブ状態で開始時刻不足(self):
        """アクティブ状態で開始時刻が不足している場合のバリデーション"""
        with pytest.raises(ValueError, match="アクティブな状態では開始時刻が必要です"):
            RebuildState(is_active=True, thread_id="test", start_time=None)

    def test_バリデーション_存在しないフォルダパス(self):
        """存在しないフォルダパスでのバリデーション"""
        with pytest.raises(ValueError, match="指定されたフォルダが存在しません"):
            RebuildState(folder_path="/nonexistent/path")


class TestRebuildProgress:
    """RebuildProgressデータクラスのテスト"""

    def test_初期状態(self):
        """初期状態の確認"""
        progress = RebuildProgress()

        assert progress.stage == "idle"
        assert progress.current_file == ""
        assert progress.files_processed == 0
        assert progress.total_files == 0
        assert progress.percentage == 0
        assert progress.message == ""

    def test_進捗率自動計算(self):
        """進捗率の自動計算"""
        progress = RebuildProgress(files_processed=25, total_files=100)

        assert progress.percentage == 25

    def test_進捗率自動計算_完了状態(self):
        """完了状態での進捗率自動計算"""
        progress = RebuildProgress(stage="completed", total_files=0)

        assert progress.percentage == 100

    def test_進捗率自動計算_上限(self):
        """進捗率の上限確認"""
        progress = RebuildProgress(files_processed=150, total_files=100)

        assert progress.percentage == 100

    def test_表示メッセージ_idle(self):
        """idle段階の表示メッセージ"""
        progress = RebuildProgress(stage="idle")

        assert progress.get_display_message() == "待機中"

    def test_表示メッセージ_scanning(self):
        """scanning段階の表示メッセージ"""
        progress = RebuildProgress(stage="scanning", total_files=50)

        message = progress.get_display_message()
        assert "ファイルをスキャン中" in message
        assert "50個発見" in message

    def test_表示メッセージ_processing(self):
        """processing段階の表示メッセージ"""
        progress = RebuildProgress(
            stage="processing",
            current_file="/path/to/document.pdf",
            files_processed=10,
            total_files=50,
        )

        message = progress.get_display_message()
        assert "処理中: document.pdf" in message
        assert "(10/50)" in message

    def test_表示メッセージ_indexing(self):
        """indexing段階の表示メッセージ"""
        progress = RebuildProgress(stage="indexing", files_processed=45)

        message = progress.get_display_message()
        assert "インデックスを作成中" in message
        assert "45ファイル処理済み" in message

    def test_表示メッセージ_completed(self):
        """completed段階の表示メッセージ"""
        progress = RebuildProgress(stage="completed", files_processed=100)

        message = progress.get_display_message()
        assert "インデックス再構築が完了しました" in message
        assert "100ファイル処理" in message

    def test_表示メッセージ_error(self):
        """error段階の表示メッセージ"""
        progress = RebuildProgress(stage="error")

        message = progress.get_display_message()
        assert "エラーが発生しました" in message

    def test_表示メッセージ_カスタム(self):
        """カスタムメッセージの優先"""
        custom_message = "カスタムメッセージです"
        progress = RebuildProgress(stage="processing", message=custom_message)

        assert progress.get_display_message() == custom_message

    def test_進捗詳細情報取得(self):
        """進捗詳細情報の取得"""
        progress = RebuildProgress(
            stage="processing",
            current_file="test.pdf",
            files_processed=25,
            total_files=100,
        )

        details = progress.get_progress_details()

        assert details["stage"] == "processing"
        assert details["current_file"] == "test.pdf"
        assert details["files_processed"] == 25
        assert details["total_files"] == 100
        assert details["percentage"] == 25
        assert details["has_files"] is True
        assert details["is_active"] is True
        assert "message" in details

    def test_スキャン更新(self):
        """スキャン段階の更新"""
        progress = RebuildProgress()

        progress.update_scanning(files_found=75)

        assert progress.stage == "scanning"
        assert progress.total_files == 75
        assert progress.files_processed == 0
        assert progress.current_file == ""

    def test_処理更新(self):
        """処理段階の更新"""
        progress = RebuildProgress()

        progress.update_processing("document.pdf", 30, 100)

        assert progress.stage == "processing"
        assert progress.current_file == "document.pdf"
        assert progress.files_processed == 30
        assert progress.total_files == 100
        assert progress.percentage == 30

    def test_インデックス更新(self):
        """インデックス段階の更新"""
        progress = RebuildProgress()

        progress.update_indexing(80)

        assert progress.stage == "indexing"
        assert progress.files_processed == 80
        assert progress.current_file == ""

    def test_完了設定(self):
        """完了状態の設定"""
        progress = RebuildProgress()

        progress.set_completed(150)

        assert progress.stage == "completed"
        assert progress.files_processed == 150
        assert progress.total_files == 150
        assert progress.current_file == ""
        assert progress.percentage == 100

    def test_エラー設定(self):
        """エラー状態の設定"""
        progress = RebuildProgress()
        error_message = "テストエラーメッセージ"

        progress.set_error(error_message)

        assert progress.stage == "error"
        assert progress.message == error_message
        assert progress.current_file == ""

    def test_エラー設定_デフォルトメッセージ(self):
        """エラー状態の設定（デフォルトメッセージ）"""
        progress = RebuildProgress()

        progress.set_error()

        assert progress.stage == "error"
        assert progress.message == "処理中にエラーが発生しました"

    def test_リセット(self):
        """進捗情報のリセット"""
        progress = RebuildProgress(
            stage="processing",
            current_file="test.pdf",
            files_processed=50,
            total_files=100,
            message="テストメッセージ",
        )

        progress.reset()

        assert progress.stage == "idle"
        assert progress.current_file == ""
        assert progress.files_processed == 0
        assert progress.total_files == 0
        assert progress.percentage == 0
        assert progress.message == ""

    def test_バリデーション_無効な段階(self):
        """無効な段階でのバリデーション"""
        with pytest.raises(ValueError, match="無効な段階です"):
            RebuildProgress(stage="invalid_stage")

    def test_バリデーション_負の処理済みファイル数(self):
        """負の処理済みファイル数でのバリデーション"""
        with pytest.raises(
            ValueError, match="処理済みファイル数は0以上である必要があります"
        ):
            RebuildProgress(files_processed=-1)

    def test_バリデーション_負の総ファイル数(self):
        """負の総ファイル数でのバリデーション"""
        with pytest.raises(ValueError, match="総ファイル数は0以上である必要があります"):
            RebuildProgress(total_files=-1)

    def test_進捗率制限_処理済み数が総数を超過(self):
        """処理済みファイル数が総数を超過する場合の進捗率制限"""
        progress = RebuildProgress(files_processed=150, total_files=100)
        # 進捗率は100%に制限される
        assert progress.percentage == 100

    def test_バリデーション_無効な進捗率(self):
        """無効な進捗率でのバリデーション"""
        with pytest.raises(
            ValueError, match="進捗率は0から100の範囲である必要があります"
        ):
            RebuildProgress(percentage=150)
