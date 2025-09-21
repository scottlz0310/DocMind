"""
テスト用サンプルファイル生成フィクスチャ

コアロジックテストで使用するサンプルファイルを生成します。
"""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_files_dir():
    """サンプルファイル用の一時ディレクトリを作成"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_text_files(sample_files_dir):
    """複数のサンプルテキストファイルを作成"""
    files = []

    # 日本語テキストファイル
    japanese_file = os.path.join(sample_files_dir, "japanese.txt")
    with open(japanese_file, "w", encoding="utf-8") as f:
        f.write(
            "これは日本語のテストファイルです。\n機械学習と自然言語処理について説明します。\nDocMindは優れた検索ツールです。"
        )
    files.append(japanese_file)

    # 英語テキストファイル
    english_file = os.path.join(sample_files_dir, "english.txt")
    with open(english_file, "w", encoding="utf-8") as f:
        f.write(
            "This is an English test file.\n"
            "It contains information about machine learning and natural language processing.\n"
            "DocMind is an excellent search tool."
        )
    files.append(english_file)

    # 混合言語ファイル
    mixed_file = os.path.join(sample_files_dir, "mixed.txt")
    with open(mixed_file, "w", encoding="utf-8") as f:
        f.write(
            "Mixed language file 混合言語ファイル\nEnglish and Japanese 英語と日本語\nSearch functionality 検索機能"
        )
    files.append(mixed_file)

    return files


@pytest.fixture
def sample_markdown_files(sample_files_dir):
    """サンプルMarkdownファイルを作成"""
    files = []

    # 基本的なMarkdownファイル
    basic_md = os.path.join(sample_files_dir, "basic.md")
    with open(basic_md, "w", encoding="utf-8") as f:
        f.write(
            """# メインタイトル

## セクション1

これは**重要な**テキストです。

### サブセクション

- リスト項目1
- リスト項目2
- リスト項目3

## セクション2

`コードサンプル`を含むテキスト。

```python
def hello_world():
    print("Hello, World!")
```

[リンクテキスト](https://example.com)
"""
        )
    files.append(basic_md)

    # 複雑なMarkdownファイル
    complex_md = os.path.join(sample_files_dir, "complex.md")
    with open(complex_md, "w", encoding="utf-8") as f:
        f.write(
            """# DocMind ドキュメント

## 概要

DocMindは**ローカルAI搭載**のドキュメント検索ツールです。

### 主要機能

1. 全文検索
2. セマンティック検索
3. ハイブリッド検索

#### 対応ファイル形式

- PDF
- Word (*.docx)
- Excel (*.xlsx)
- Markdown (*.md)
- テキスト (*.txt)

## 技術仕様

### アーキテクチャ

```
GUI Layer
├── Business Logic Layer
└── Data Layer
```

### 使用技術

| 技術 | 用途 |
|------|------|
| PySide6 | GUI フレームワーク |
| Whoosh | 全文検索エンジン |
| sentence-transformers | セマンティック検索 |

## インストール

```bash
pip install -r requirements.txt
python main.py
```

> **注意**: Python 3.11以上が必要です。
"""
        )
    files.append(complex_md)

    return files


@pytest.fixture
def sample_large_file(sample_files_dir):
    """大きなサンプルファイルを作成"""
    large_file = os.path.join(sample_files_dir, "large.txt")

    # 10,000行の大きなファイルを作成
    with open(large_file, "w", encoding="utf-8") as f:
        for i in range(10000):
            f.write(
                f"これは{i}行目のテストデータです。検索機能のパフォーマンステスト用。\n"
            )

    return large_file


@pytest.fixture
def sample_empty_file(sample_files_dir):
    """空のサンプルファイルを作成"""
    empty_file = os.path.join(sample_files_dir, "empty.txt")
    Path(empty_file).touch()
    return empty_file


@pytest.fixture
def sample_binary_file(sample_files_dir):
    """バイナリファイルを作成"""
    binary_file = os.path.join(sample_files_dir, "binary.bin")

    with open(binary_file, "wb") as f:
        f.write(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09")

    return binary_file


@pytest.fixture
def sample_encoding_files(sample_files_dir):
    """異なるエンコーディングのファイルを作成"""
    files = {}

    # UTF-8ファイル
    utf8_file = os.path.join(sample_files_dir, "utf8.txt")
    with open(utf8_file, "w", encoding="utf-8") as f:
        f.write("UTF-8エンコーディングのテストファイル")
    files["utf8"] = utf8_file

    # Shift_JISファイル
    try:
        sjis_file = os.path.join(sample_files_dir, "sjis.txt")
        with open(sjis_file, "w", encoding="shift_jis") as f:
            f.write("Shift_JISエンコーディングのテストファイル")
        files["sjis"] = sjis_file
    except UnicodeEncodeError:
        # Shift_JISでエンコードできない場合はスキップ
        pass

    return files


@pytest.fixture
def sample_documents_data():
    """テスト用ドキュメントデータを作成"""
    from datetime import datetime

    from src.data.models import Document, FileType

    documents = []

    # ドキュメント1: 技術文書
    doc1 = Document(
        id="tech_doc_1",
        file_path="/test/technical_document.md",
        title="機械学習入門",
        content="機械学習は人工知能の一分野です。教師あり学習、教師なし学習、強化学習の3つの主要なカテゴリがあります。",
        file_type=FileType.MARKDOWN,
        size=2048,
        created_date=datetime(2024, 1, 1),
        modified_date=datetime(2024, 1, 15),
        indexed_date=datetime.now(),
        content_hash="tech_hash_1",
    )
    documents.append(doc1)

    # ドキュメント2: ユーザーマニュアル
    doc2 = Document(
        id="manual_doc_1",
        file_path="/test/user_manual.txt",
        title="DocMind ユーザーマニュアル",
        content="DocMindの使用方法について説明します。検索機能、インデックス作成、設定方法などを含みます。",
        file_type=FileType.TEXT,
        size=1536,
        created_date=datetime(2024, 1, 5),
        modified_date=datetime(2024, 1, 20),
        indexed_date=datetime.now(),
        content_hash="manual_hash_1",
    )
    documents.append(doc2)

    # ドキュメント3: 研究論文
    doc3 = Document(
        id="paper_doc_1",
        file_path="/test/research_paper.pdf",
        title="自然言語処理における深層学習の応用",
        content="本論文では、自然言語処理タスクにおける深層学習手法の応用について述べる。BERT、GPT、T5などのモデルを比較検討する。",
        file_type=FileType.PDF,
        size=4096,
        created_date=datetime(2024, 1, 10),
        modified_date=datetime(2024, 1, 25),
        indexed_date=datetime.now(),
        content_hash="paper_hash_1",
    )
    documents.append(doc3)

    return documents


@pytest.fixture
def performance_test_documents():
    """パフォーマンステスト用の大量ドキュメントデータ"""
    from datetime import datetime, timedelta

    from src.data.models import Document, FileType

    documents = []
    base_date = datetime(2024, 1, 1)

    for i in range(1000):  # 1000個のドキュメント
        doc = Document(
            id=f"perf_doc_{i:04d}",
            file_path=f"/test/performance/doc_{i:04d}.txt",
            title=f"パフォーマンステストドキュメント {i}",
            content=f"これは{i}番目のパフォーマンステスト用ドキュメントです。"
            + "検索機能のスケーラビリティをテストします。"
            + f"キーワード: test{i % 10}, performance, document, search",
            file_type=FileType.TEXT,
            size=512 + (i % 100) * 10,
            created_date=base_date + timedelta(days=i % 365),
            modified_date=base_date + timedelta(days=i % 365, hours=i % 24),
            indexed_date=datetime.now(),
            content_hash=f"perf_hash_{i:04d}",
        )
        documents.append(doc)

    return documents
