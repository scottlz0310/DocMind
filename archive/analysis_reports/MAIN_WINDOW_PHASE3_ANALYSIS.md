# main_window.py Phase3 分析レポート

## 📊 現在の状況

**対象ファイル**: `src/gui/main_window.py`
- **現在の行数**: 1,975行
- **現在のメソッド数**: 73メソッド
- **Phase3目標**: 800行以下 (60%削減)、30メソッド以下

## 🔍 分離対象メソッド分析

### 1. メニュー管理系(menu_manager.py)
**既に実装済み** ✅
- メニューバー作成・設定
- メニューアクション処理
- ショートカット設定

### 2. ツールバー管理系(toolbar_manager.py)
**既に実装済み** ✅
- ツールバー作成・設定
- ツールバーアクション処理
- アイコン管理

### 3. ステータス管理系(status_manager.py)
**既に実装済み** ✅
- ステータスバー管理
- 状態メッセージ表示
- システム情報表示

### 4. ウィンドウ状態管理系(window_state_manager.py)
**既に実装済み** ✅
- ウィンドウサイズ・位置管理
- 設定保存・復元
- レイアウト状態管理

### 5. 新規分離対象(Phase3で実装)

#### A. 設定・テーマ管理系 → `settings_theme_manager.py`
**分離対象メソッド**:
- `_on_settings_changed()` (line 245)
- `_apply_theme()` (line 275)
- `_apply_font_settings()` (line 285)

#### B. エラー処理・再構築管理系 → `error_rebuild_manager.py`
**分離対象メソッド**:
- `_on_rebuild_completed()` (line 1050)
- `_handle_rebuild_timeout()` (line 1080)
- `_force_stop_rebuild()` (line 1110)
- `_reset_rebuild_state()` (line 1150)
- `_update_system_info_after_rebuild()` (line 1180)
- `_update_folder_tree_after_rebuild()` (line 1220)
- `_on_rebuild_error()` (line 1250)
- `_analyze_error_type()` (line 1290)
- `_handle_file_access_error()` (line 1320)
- `_handle_permission_error()` (line 1350)
- `_handle_resource_error()` (line 1380)
- `_handle_disk_space_error()` (line 1410)
- `_handle_corruption_error()` (line 1440)
- `_handle_system_error()` (line 1470)
- `_perform_error_cleanup()` (line 1500)

#### C. 進捗・システム情報管理系 → `progress_system_manager.py`
**分離対象メソッド**:
- `_format_completion_message()` (line 400)
- `_format_detailed_completion_message()` (line 450)
- `_update_system_info_with_progress()` (line 500)
- `_format_progress_message()` (line 550)
- `_on_manager_status_changed()` (line 650)
- `_on_rebuild_progress()` (line 700)
- `_determine_rebuild_stage()` (line 800)
- `_format_rebuild_progress_message()` (line 850)
- `_update_rebuild_system_info()` (line 900)

#### D. イベント・シグナル処理系 → `event_signal_manager.py`
**分離対象メソッド**:
- `_on_folder_excluded()` (line 950)
- `_on_folder_refresh()` (line 970)
- `_on_search_result_selected()` (line 1530)
- `_on_preview_requested()` (line 1550)
- `_on_page_changed()` (line 1570)
- `_on_sort_changed()` (line 1580)
- `_on_filter_changed()` (line 1590)
- `_on_preview_zoom_changed()` (line 1600)
- `_on_preview_format_changed()` (line 1610)

## 📈 予想削減効果

### 分離予定メソッド数
- **設定・テーマ管理**: 3メソッド
- **エラー処理・再構築管理**: 15メソッド
- **進捗・システム情報管理**: 9メソッド
- **イベント・シグナル処理**: 9メソッド
- **合計**: 36メソッド

### 予想削減行数
- **設定・テーマ管理**: 約100行
- **エラー処理・再構築管理**: 約600行
- **進捗・システム情報管理**: 約400行
- **イベント・シグナル処理**: 約200行
- **合計**: 約1,300行

### Phase3完了後の予想
- **行数**: 1,975行 → 675行 (65.8%削減) ✅
- **メソッド数**: 73メソッド → 37メソッド (49.3%削減) ✅

## 🎯 実装戦略

### Week 1: 設定・エラー処理管理分離
1. **Day 1-2**: `settings_theme_manager.py` 作成・実装
2. **Day 3-4**: `error_rebuild_manager.py` 作成・実装
3. **Day 5**: 統合テスト・品質確認

### Week 2: 進捗・イベント処理管理分離
1. **Day 1-2**: `progress_system_manager.py` 作成・実装
2. **Day 3-4**: `event_signal_manager.py` 作成・実装
3. **Day 5**: 統合テスト・品質確認

### Week 3: 最終統合・品質保証
1. **Day 1-2**: 全体統合テスト
2. **Day 3-4**: パフォーマンス・メモリテスト
3. **Day 5**: ドキュメント更新・成果報告

## 🚨 注意事項

### 高リスク要素
1. **複雑なエラー処理**: 多数のエラーハンドリングメソッドの相互依存
2. **進捗管理**: UI更新とシステム情報の同期
3. **シグナル接続**: イベント処理の連携維持

### 対策
- **段階的分離**: 1つずつ慎重に分離
- **即座の検証**: 各段階で動作確認
- **ロールバック準備**: 問題発生時の即座復旧

---
**作成日**: 2025-08-28
**Phase**: Phase3 (main_window.py追加リファクタリング)
**目標**: 800行以下、30メソッド以下
**重要度**: 🔴 最高