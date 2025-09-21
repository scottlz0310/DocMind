# Phase5 テスト環境再構築計画書

## 📋 プロジェクト概要

### 現状の問題
- **テストコード**: 51,039行(実装コードの1.88倍)
- **実装コード**: 27,157行
- **問題**: 神クラス時代に構築した包括的テストがPhase4リファクタリングで無効化

### 目標
**「ユニットテストで品質保証、統合テストは接続確認のみ」**の理想的なテスト構造を実現

## 🎯 Phase5 目標指標

### テストコード削減目標
- **現在**: 51,039行 → **目標**: 10,000行以下(80%削減)
- **ユニットテスト**: 8,000行(品質保証の主力)
- **統合テスト**: 2,000行(接続確認のみ)

### テストピラミッド構造
```
     統合テスト (2,000行)
    ┌─────────────────┐
   ┌┴─────────────────┴┐
  ┌┴───────────────────┴┐
 ┌┴─────────────────────┴┐
└─ ユニットテスト (8,000行) ─┘
```

## 🏗️ 実装戦略

### Step1: ユニットテスト充実(6週間)

#### 1.1 コンポーネント別ユニットテスト作成
Phase4で分離した15個のコンポーネントに対応：

**GUIマネージャー系(5コンポーネント)**
```
tests/unit/managers/
├── test_layout_manager.py          # 200行 - レイアウト管理テスト
├── test_progress_manager.py        # 150行 - 進捗管理テスト
├── test_signal_manager.py          # 180行 - シグナル管理テスト
├── test_cleanup_manager.py         # 120行 - クリーンアップテスト
└── test_window_state_manager.py    # 150行 - ウィンドウ状態テスト
```

**コントローラー系(3コンポーネント)**
```
tests/unit/controllers/
├── test_index_controller.py        # 300行 - インデックス制御テスト
├── test_search_controller.py       # 250行 - 検索制御テスト
└── test_dialog_manager.py          # 200行 - ダイアログ管理テスト
```

**検索機能系(4コンポーネント)**
```
tests/unit/search/
├── test_search_ui_manager.py       # 150行 - 検索UI管理テスト
├── test_search_api_manager.py      # 200行 - 検索API管理テスト
├── test_search_options_manager.py  # 100行 - 検索オプションテスト
└── test_shortcut_manager.py        # 80行  - ショートカットテスト
```

**フォルダツリー系(3コンポーネント)**
```
tests/unit/folder_tree/
├── test_folder_tree_widget.py      # 400行 - フォルダツリーテスト
├── test_event_handler_manager.py   # 150行 - イベント処理テスト
└── test_ui_setup_manager.py        # 120行 - UI設定テスト
```

#### 1.2 ユニットテスト設計原則

**独立性の確保**
```python
# 良い例：依存関係をモック化
def test_search_controller_search():
    mock_index_manager = Mock()
    mock_search_manager = Mock()
    
    controller = SearchController(
        index_manager=mock_index_manager,
        search_manager=mock_search_manager
    )
    
    result = controller.execute_search("test query")
    assert result.success is True
```

**単一責務のテスト**
```python
# 各メソッドを個別にテスト
class TestLayoutManager:
    def test_create_main_layout(self):
        # レイアウト作成のみテスト
        
    def test_update_layout_visibility(self):
        # 表示切替のみテスト
        
    def test_resize_layout_components(self):
        # リサイズ処理のみテスト
```

### Step2: 統合テスト簡素化(2週間)

#### 2.1 接続確認レベルの統合テスト

**メインウィンドウ統合テスト**
```python
# tests/integration/test_main_window_integration.py (500行)
class TestMainWindowIntegration:
    def test_component_initialization(self):
        """全コンポーネントが正常に初期化されるか"""
        
    def test_signal_connections(self):
        """シグナル接続が正常に動作するか"""
        
    def test_cleanup_flow(self):
        """クリーンアップが正常に実行されるか"""
```

**検索フロー統合テスト**
```python
# tests/integration/test_search_flow_integration.py (300行)
class TestSearchFlowIntegration:
    def test_search_pipeline(self):
        """検索パイプライン全体の接続確認"""
        # SearchInterface → SearchController → IndexManager
        
    def test_result_display_flow(self):
        """検索結果表示フローの接続確認"""
        # SearchController → SearchResults → PreviewWidget
```

**インデックス管理統合テスト**
```python
# tests/integration/test_index_management_integration.py (400行)
class TestIndexManagementIntegration:
    def test_index_creation_flow(self):
        """インデックス作成フロー全体の接続確認"""
        
    def test_file_monitoring_integration(self):
        """ファイル監視とインデックス更新の連携確認"""
```

#### 2.2 統合テスト設計原則

**接続確認に特化**
```python
def test_search_integration():
    # 詳細な結果検証はしない
    # エラーが発生しないことのみ確認
    try:
        result = search_flow.execute("test")
        assert not isinstance(result, Exception)
    except Exception as e:
        pytest.fail(f"Integration failed: {e}")
```

**最小限のデータ使用**
```python
# 大量のテストデータは使わない
TEST_FILES = [
    "sample1.txt",  # 基本テキスト
    "sample2.pdf",  # PDF
    "sample3.docx"  # Word
]
```

### Step3: レガシーテスト整理(2週間)

#### 3.1 削除対象テスト
- **validation_framework/**: 40,000行 → 削除
- **複雑なシナリオテスト**: 8,000行 → 削除
- **重複テスト**: 3,000行 → 統合

#### 3.2 保持対象テスト
- **基本機能テスト**: 必要最小限に簡素化
- **回帰テスト**: 既存機能保護用に維持

## 📅 実装スケジュール(10週間)

### Week 1-2: 環境準備・設計
- [ ] テスト環境のクリーンアップ
- [ ] モック・フィクスチャの設計
- [ ] テストユーティリティの作成

### Week 3-6: ユニットテスト実装
- [ ] Week 3: GUIマネージャー系テスト
- [ ] Week 4: コントローラー系テスト  
- [ ] Week 5: 検索機能系テスト
- [ ] Week 6: フォルダツリー系テスト

### Week 7-8: 統合テスト実装
- [ ] Week 7: メインウィンドウ・検索フロー統合テスト
- [ ] Week 8: インデックス管理統合テスト

### Week 9-10: レガシー整理・最適化
- [ ] Week 9: レガシーテスト削除・統合
- [ ] Week 10: パフォーマンス最適化・ドキュメント更新

## 🛠️ 技術仕様

### テストフレームワーク
- **pytest**: メインフレームワーク
- **pytest-qt**: GUI テスト用
- **pytest-mock**: モック機能
- **pytest-cov**: カバレッジ測定

### モック戦略
```python
# 依存関係の標準モック
@pytest.fixture
def mock_index_manager():
    return Mock(spec=IndexManager)

@pytest.fixture  
def mock_search_manager():
    return Mock(spec=SearchManager)
```

### テストデータ管理
```python
# 最小限のテストデータセット
@pytest.fixture
def minimal_test_data():
    return {
        "documents": ["test1.txt", "test2.pdf"],
        "queries": ["basic query", "advanced query"],
        "expected_results": [...]
    }
```

## 📊 品質指標

### カバレッジ目標
- **ユニットテスト**: 85%以上
- **統合テスト**: 接続部分100%
- **全体**: 80%以上

### パフォーマンス目標
- **テスト実行時間**: 5分以内(現在30分以上)
- **テスト起動時間**: 30秒以内
- **メモリ使用量**: 1GB以内

## 🎯 成功指標

### 定量的指標
- [ ] テストコード行数: 51,039行 → 10,000行以下
- [ ] テスト実行時間: 30分 → 5分以内
- [ ] テスト成功率: 95%以上維持

### 定性的指標
- [ ] 新機能追加時のテスト作成が容易
- [ ] リファクタリング時のテスト修正が最小限
- [ ] テストの意図が明確で理解しやすい

## 🚨 リスク管理

### 主要リスク
1. **既存機能の回帰**: レガシーテスト削除による見落とし
2. **テスト設計の複雑化**: 理想を追求しすぎる危険性
3. **スケジュール遅延**: 10週間は楽観的見積もり

### 対策
1. **段階的削除**: 一度に大量削除せず、段階的に実施
2. **シンプル設計**: 「動作確認レベル」を徹底
3. **マイルストーン管理**: 2週間ごとの進捗確認

## 📚 参考資料

### テスト設計原則
- **テストピラミッド**: Martin Fowler
- **単体テスト**: Roy Osherove
- **実用的テスト**: Kent Beck

### 実装ガイドライン
- **pytest公式ドキュメント**
- **pytest-qt使用方法**
- **Mockライブラリ活用法**

---

**Phase5完了時の理想状態**：
「各コンポーネントが独立してテストされ、統合テストは接続確認のみ。新機能追加時もテスト作成が容易で、保守コストが大幅に削減された状態」