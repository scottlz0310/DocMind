# Phase6 GUIテスト環境整備計画書

## 📋 Phase5成果とPhase6への移行

### Phase5完了成果
- **テストコード削減**: 51,039行 → 10,247行（79.9%削減達成）
- **ユニットテスト基盤**: 8,247行の高品質ユニットテスト構築
- **統合テスト簡素化**: 2,000行の接続確認レベル統合テスト
- **実行時間短縮**: 30分 → 5分以内（目標達成）

### 残存課題（Phase6で解決）
- **QObject初期化問題**: 44テストがPySide6初期化エラーで未実行
- **GUIテスト環境**: ヘッドレス環境でのGUIテスト実行基盤未整備
- **コアロジックテスト**: DocumentProcessor、IndexManager等の重要コンポーネントテスト不足

## 🎯 Phase6 目標

### 主要目標
**「包括的品質保証体制の完成」** - GUIテスト環境整備により全テストの実行可能化

### 具体的成果指標
- **テスト実行率**: 95% → 100%（44未実行テストの解決）
- **GUIテスト環境**: ヘッドレス環境での安定実行
- **コアロジックカバレッジ**: 70% → 90%以上
- **CI/CD統合**: 自動テスト実行環境の完全構築

## 🔧 技術的課題と解決策

### 課題1: QObject初期化エラー
```
FAILED tests/unit/gui/test_main_window.py::TestMainWindow::test_initialization
E   RuntimeError: Please destroy the QApplication singleton before creating a new one.
```

**解決策**: pytest-qtとQApplication管理の整備
```python
# conftest.py
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import sys

@pytest.fixture(scope="session")
def qapp():
    """セッション全体で共有するQApplication"""
    if not QApplication.instance():
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        yield app
        app.quit()
    else:
        yield QApplication.instance()

@pytest.fixture
def qtbot(qapp, qtbot):
    """QApplicationを確実に初期化したqtbot"""
    return qtbot
```

### 課題2: ヘッドレス環境でのGUI実行
**解決策**: 仮想ディスプレイとCI環境の整備
```yaml
# .github/workflows/test.yml
- name: Setup virtual display
  run: |
    sudo apt-get update
    sudo apt-get install -y xvfb
    export DISPLAY=:99
    Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
```

### 課題3: コアロジック単体テスト不足
**解決策**: 重要コンポーネントの独立テスト強化

## 🏗️ 実装戦略

### Step1: GUIテスト環境基盤整備（3週間）

#### 1.1 pytest-qt環境構築
```python
# tests/conftest.py - 統一QApplication管理
@pytest.fixture(scope="session", autouse=True)
def setup_qt_environment():
    """Qt環境の統一セットアップ"""
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    yield app
    
    # クリーンアップ
    app.processEvents()
    QTimer.singleShot(0, app.quit)
```

#### 1.2 ヘッドレステスト環境
```python
# tests/gui/test_helpers.py
class GUITestHelper:
    """GUIテスト用ヘルパークラス"""
    
    @staticmethod
    def create_test_widget(widget_class, **kwargs):
        """テスト用ウィジェット作成"""
        widget = widget_class(**kwargs)
        widget.show()
        QApplication.processEvents()
        return widget
    
    @staticmethod
    def simulate_user_interaction(widget, action, *args):
        """ユーザー操作シミュレーション"""
        getattr(widget, action)(*args)
        QApplication.processEvents()
```

### Step2: 44未実行テストの修正（4週間）

#### 2.1 MainWindowテスト修正
```python
# tests/unit/gui/test_main_window.py
class TestMainWindow:
    def test_initialization(self, qtbot):
        """メインウィンドウ初期化テスト"""
        from src.gui.main_window import MainWindow
        
        window = MainWindow()
        qtbot.addWidget(window)
        
        # 基本的な初期化確認
        assert window.isVisible() is False  # まだshow()していない
        assert hasattr(window, 'layout_manager')
        assert hasattr(window, 'progress_manager')
    
    def test_component_managers_creation(self, qtbot):
        """コンポーネントマネージャー作成テスト"""
        window = MainWindow()
        qtbot.addWidget(window)
        
        # 15個のマネージャーが正常に作成されているか
        managers = [
            'layout_manager', 'progress_manager', 'signal_manager',
            'cleanup_manager', 'window_state_manager', 'menu_manager',
            'toolbar_manager', 'status_manager', 'thread_handler_manager',
            'error_rebuild_manager', 'settings_handler_manager',
            'search_handler_manager', 'progress_system_manager'
        ]
        
        for manager_name in managers:
            assert hasattr(window, manager_name)
            assert getattr(window, manager_name) is not None
```

#### 2.2 検索機能テスト修正
```python
# tests/unit/search/test_search_controller.py
class TestSearchController:
    @pytest.fixture
    def mock_dependencies(self):
        """検索コントローラーの依存関係モック"""
        return {
            'index_manager': Mock(),
            'search_manager': Mock(),
            'result_handler': Mock()
        }
    
    def test_execute_search_basic(self, qtbot, mock_dependencies):
        """基本検索実行テスト"""
        controller = SearchController(**mock_dependencies)
        
        # モックの戻り値設定
        mock_dependencies['search_manager'].search.return_value = [
            {'title': 'Test Doc', 'content': 'Test content'}
        ]
        
        result = controller.execute_search("test query")
        
        assert result is not None
        mock_dependencies['search_manager'].search.assert_called_once()
```

### Step3: コアロジック強化テスト（3週間）

#### 3.1 DocumentProcessorテスト
```python
# tests/unit/core/test_document_processor.py
class TestDocumentProcessor:
    def test_pdf_text_extraction(self, sample_pdf_file):
        """PDF テキスト抽出テスト"""
        processor = DocumentProcessor()
        
        result = processor.extract_text(sample_pdf_file)
        
        assert result.success is True
        assert len(result.text) > 0
        assert result.metadata['file_type'] == 'pdf'
    
    def test_word_document_processing(self, sample_docx_file):
        """Word文書処理テスト"""
        processor = DocumentProcessor()
        
        result = processor.process_document(sample_docx_file)
        
        assert result.success is True
        assert result.text_content is not None
        assert result.metadata['word_count'] > 0
```

#### 3.2 IndexManagerテスト
```python
# tests/unit/core/test_index_manager.py
class TestIndexManager:
    @pytest.fixture
    def temp_index_dir(self, tmp_path):
        """一時インデックスディレクトリ"""
        index_dir = tmp_path / "test_index"
        index_dir.mkdir()
        return str(index_dir)
    
    def test_create_index(self, temp_index_dir):
        """インデックス作成テスト"""
        manager = IndexManager(index_dir=temp_index_dir)
        
        result = manager.create_index()
        
        assert result.success is True
        assert manager.index_exists()
    
    def test_add_document_to_index(self, temp_index_dir, sample_document):
        """ドキュメント追加テスト"""
        manager = IndexManager(index_dir=temp_index_dir)
        manager.create_index()
        
        result = manager.add_document(sample_document)
        
        assert result.success is True
        assert manager.document_count() == 1
```

### Step4: CI/CD統合とパフォーマンス最適化（2週間）

#### 4.1 GitHub Actions設定
```yaml
# .github/workflows/comprehensive-test.yml
name: Comprehensive Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Setup virtual display
      run: |
        sudo apt-get update
        sudo apt-get install -y xvfb libegl1-mesa libxkbcommon-x11-0
        export DISPLAY=:99
        Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest-qt pytest-xvfb
    
    - name: Run comprehensive tests
      run: |
        export QT_QPA_PLATFORM=offscreen
        pytest tests/ -v --tb=short --maxfail=5
      env:
        DISPLAY: :99
```

#### 4.2 テストパフォーマンス最適化
```python
# tests/performance/test_performance_benchmarks.py
class TestPerformanceBenchmarks:
    def test_search_performance(self, benchmark, large_index):
        """検索パフォーマンステスト"""
        search_manager = SearchManager(large_index)
        
        result = benchmark(search_manager.search, "test query")
        
        # 5秒以内での検索完了を確認
        assert benchmark.stats['mean'] < 5.0
    
    def test_index_creation_performance(self, benchmark, sample_documents):
        """インデックス作成パフォーマンステスト"""
        index_manager = IndexManager()
        
        result = benchmark(index_manager.bulk_add_documents, sample_documents)
        
        # 大量ドキュメント処理の性能確認
        assert result.success is True
```

## 📅 実装スケジュール（12週間）

### Week 1-3: GUIテスト環境基盤整備
- [ ] Week 1: pytest-qt環境構築・QApplication管理統一
- [ ] Week 2: ヘッドレステスト環境・CI設定
- [ ] Week 3: GUIテストヘルパー・ユーティリティ作成

### Week 4-7: 44未実行テスト修正
- [ ] Week 4: MainWindowテスト修正（15テスト）
- [ ] Week 5: 検索機能テスト修正（12テスト）
- [ ] Week 6: フォルダツリーテスト修正（10テスト）
- [ ] Week 7: その他GUIコンポーネントテスト修正（7テスト）

### Week 8-10: コアロジック強化テスト
- [ ] Week 8: DocumentProcessor・FileProcessor強化
- [ ] Week 9: IndexManager・SearchManager強化
- [ ] Week 10: EmbeddingManager・ConfigManager強化

### Week 11-12: 統合・最適化
- [ ] Week 11: CI/CD統合・自動テスト環境完成
- [ ] Week 12: パフォーマンス最適化・ドキュメント更新

## 📊 品質指標

### テスト実行率目標
- **現在**: 95%（44テスト未実行）
- **目標**: 100%（全テスト実行可能）

### カバレッジ目標
- **GUIコンポーネント**: 80%以上
- **コアロジック**: 90%以上
- **統合テスト**: 接続部分100%

### パフォーマンス目標
- **テスト実行時間**: 5分以内維持
- **CI実行時間**: 10分以内
- **メモリ使用量**: 1.5GB以内

## 🎯 成功指標

### 定量的指標
- [ ] テスト実行率: 95% → 100%
- [ ] 未実行テスト: 44個 → 0個
- [ ] CI成功率: 95%以上
- [ ] コアロジックカバレッジ: 70% → 90%

### 定性的指標
- [ ] ヘッドレス環境での安定したGUIテスト実行
- [ ] 新機能追加時のテスト作成が容易
- [ ] CI/CDパイプラインでの自動品質保証
- [ ] 開発者の生産性向上

## 🚨 リスク管理

### 主要リスク
1. **Qt環境の複雑性**: ヘッドレス環境でのGUI動作不安定性
2. **CI環境差異**: ローカル環境とCI環境での動作差異
3. **パフォーマンス劣化**: GUIテスト追加による実行時間増加

### 対策
1. **段階的検証**: 小さなテストから段階的に拡張
2. **環境統一**: Docker使用による環境差異の最小化
3. **並列実行**: pytest-xdistによるテスト並列化

## 📚 技術仕様

### 必要ライブラリ
```txt
pytest-qt>=4.2.0
pytest-xvfb>=3.0.0
pytest-benchmark>=4.0.0
pytest-mock>=3.10.0
pytest-cov>=4.0.0
```

### 環境変数設定
```bash
export QT_QPA_PLATFORM=offscreen
export DISPLAY=:99
export QT_LOGGING_RULES="*.debug=false"
```

---

**Phase6完了時の理想状態**：
「全テストが安定して実行され、GUIからコアロジックまで包括的な品質保証体制が確立。CI/CDパイプラインで自動的に品質が保証され、開発者が安心して機能追加・修正を行える状態」