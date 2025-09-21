# DocMind

DocMindは、ローカルPC上に保存された様々なドキュメント形式(PDF、Word、Excel、Markdown、テキストファイル)に対する包括的な検索機能を持つローカルAI搭載デスクトップアプリケーションです。従来の全文検索とローカルAIモデルを使用したセマンティック検索を組み合わせ、外部API依存なしに完全なオフライン機能を保証します。

## 🚀 クイックスタート

### 前提条件
- Python 3.11以上
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー

### インストール

```bash
# uvのインストール(未インストールの場合)
curl -LsSf https://astral.sh/uv/install.sh | sh

# プロジェクトのクローン
git clone https://github.com/docmind/docmind.git
cd docmind

# 開発環境のセットアップ
make bootstrap

# アプリケーションの実行
make run
```

## 📋 開発コマンド

### セットアップ
```bash
make sync        # 依存関係の同期
make dev         # 開発依存関係のインストール
make bootstrap   # 完全な開発環境セットアップ
```

### テスト
```bash
make test        # 全テスト実行
make test-unit   # ユニットテストのみ
make test-int    # 統合テストのみ
make test-cov    # カバレッジ付きテスト
make test-fast   # 高速テスト(fail-fast)
```

### コード品質
```bash
make format      # コードフォーマット
make lint        # リント実行
make type-check  # 型チェック
make security    # セキュリティチェック
```

### ワークフロー
```bash
make check       # 全品質チェック
make fix         # 自動修正
make ci          # CI相当の実行
```

### パッケージ管理
```bash
make add PACKAGE=requests          # パッケージ追加
make add-dev PACKAGE=pytest       # 開発依存関係追加
make remove PACKAGE=requests      # パッケージ削除
```

## 🏗️ アーキテクチャ

### 技術スタック
- **パッケージ管理**: [uv](https://docs.astral.sh/uv/) - 高速なPythonパッケージマネージャー
- **ビルドシステム**: [Hatchling](https://hatch.pypa.io/) - モダンなPythonビルドバックエンド
- **GUI**: PySide6 - クロスプラットフォームデスクトップUI
- **検索**: Whoosh + sentence-transformers - ハイブリッド検索
- **コード品質**: Ruff + MyPy - 高速リント・型チェック

### プロジェクト構造
```
DocMind/
├── src/                    # ソースコード
│   ├── core/              # コアロジック
│   ├── gui/               # GUI コンポーネント
│   ├── data/              # データ層
│   └── utils/             # ユーティリティ
├── tests/                 # テストコード
│   ├── unit/              # ユニットテスト
│   ├── integration/       # 統合テスト
│   └── performance/       # パフォーマンステスト
├── pyproject.toml         # プロジェクト設定
├── uv.lock               # 依存関係ロック
└── Makefile              # 開発コマンド
```

## 🔧 開発環境

### uv を使った開発
このプロジェクトは[uv](https://docs.astral.sh/uv/)を使用してパッケージ管理を行います。

```bash
# 仮想環境の作成と依存関係インストール
uv sync

# 開発依存関係を含むインストール
uv sync --extra dev

# パッケージの追加
uv add requests

# 開発依存関係の追加
uv add --dev pytest

# スクリプトの実行
uv run python main.py
uv run pytest
```

### 設定ファイル
- `pyproject.toml`: プロジェクト設定、依存関係、ツール設定
- `uv.lock`: 依存関係のロックファイル
- `.uvignore`: uvが無視するファイル・ディレクトリ

## 🧪 テスト

### テスト実行
```bash
# 全テスト
make test

# 特定のテストマーカー
uv run pytest -m unit        # ユニットテストのみ
uv run pytest -m integration # 統合テストのみ
uv run pytest -m "not slow"  # 高速テストのみ
```

### カバレッジ
```bash
make test-cov
# または
uv run pytest --cov=src --cov-report=html
```

## 📦 ビルドとリリース

### パッケージビルド
```bash
make build
# または
uv build
```

### リリース
GitHubでタグを作成すると、自動的にリリースが作成されます：
```bash
git tag v1.0.0
git push origin v1.0.0
```

## 🤝 貢献

1. フォークを作成
2. フィーチャーブランチを作成: `git checkout -b feature/amazing-feature`
3. 変更をコミット: `git commit -m 'Add amazing feature'`
4. ブランチにプッシュ: `git push origin feature/amazing-feature`
5. プルリクエストを作成

### 開発ガイドライン
- コードは`make check`を通すこと
- テストは`make test`を通すこと
- コミット前に`make fix`で自動修正を実行

## 📄 ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🆘 サポート

- **Issue報告**: [GitHub Issues](https://github.com/docmind/docmind/issues)
- **ディスカッション**: [GitHub Discussions](https://github.com/docmind/docmind/discussions)
- **ドキュメント**: [Wiki](https://github.com/docmind/docmind/wiki)