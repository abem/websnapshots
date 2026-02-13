# 開発ガイド

Web Snapshot Toolへの貢献方法を説明します。

---

## 目次

1. [開発環境セットアップ](#開発環境セットアップ)
2. [プロジェクト構造](#プロジェクト構造)
3. [コーディング規約](#コーディング規約)
4. [テスト](#テスト)
5. [リリース手順](#リリース手順)

---

## 開発環境セットアップ

### フォークとクローン

```bash
# GitHubでフォークした後
git clone https://github.com/YOUR_USERNAME/websnapshots.git
cd websnapshots

# upstreamリモートを追加
git remote add upstream https://github.com/abem/websnapshots.git
```

### 開発ブランチの作成

```bash
# mainブランチを最新に
git checkout main
git pull upstream main

# 機能ブランチを作成
git checkout -b feature/your-feature-name
```

### 開発用仮想環境

```bash
# 開発用依存関係をインストール
uv pip install -r requirements.txt
uv pip install pytest black flake8 mypy

# 開発ツールのインストール
playwright install chromium
```

---

## プロジェクト構造

```
websnapshots/
├── .github/
│   └── workflows/       # CI/CD設定
├── docs/                # ドキュメント
├── web_snapshot.py      # スクリーンショットツール
├── compare_images.py    # 画像比較ツール
├── glm_diff.py          # AI分析ツール
├── ai_compare.py        # AI/OCR比較ツール（プロトタイプ）
├── requirements.txt     # 依存ライブラリ
├── pyproject.toml       # プロジェクト設定
├── .env.example         # 環境変数テンプレート
└── README.md            # プロジェクト概要
```

---

## コーディング規約

### Pythonスタイル

- PEP 8に準拠してください
- 最大行長: 100文字
- インデント: 4スペース

### 型ヒント

関数には型ヒントを付けてください：

```python
from typing import Optional

def take_screenshot(
    url: str,
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    full_page: bool = True
) -> str:
    ...
```

### ドキュメント文字列

関数にはdocstringを付けてください：

```python
def take_screenshot(url: str, output_path: str) -> str:
    """
    URLからスクリーンショットを取得します。

    Args:
        url: スクリーンショットを取得するURL
        output_path: 出力ファイルパス

    Returns:
        出力ファイルパス

    Raises:
        IOError: URLからの取得に失敗した場合
    """
    ...
```

### エラーメッセージ

エラーメッセージは日本語で記述してください：

```python
raise ValueError("URLを指定してください")
```

---

## テスト

### テストの実行

```bash
# 全テスト実行
pytest

# 特定のテスト実行
pytest tests/test_web_snapshot.py

# カバレッジレポート
pytest --cov=. --cov-report=html
```

### テストの追加

新しい機能を追加する場合は、テストも作成してください：

```python
# tests/test_web_snapshot.py
import pytest
from web_snapshot import take_screenshot_from_url

def test_take_screenshot():
    """スクリーンショット取得のテスト"""
    # テストコード
    assert True
```

---

## コミット規約

### コミットメッセージの形式

```
<type>: <subject>

<body>

<footer>
```

### タイプ

- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメントのみの変更
- `style`: コードスタイルの変更
- `refactor`: リファクタリング
- `test`: テストの追加・修正
- `chore`: ビルドプロセスやツールの変更

### 例

```
feat: .envファイルからのAPIキー読み込みを追加

- python-dotenvを使用して.envファイルを読み込む
- 複数の場所から.envファイルを検索
- エラーメッセージを改善

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

## プルリクエスト

### PRの作成手順

1. 変更をコミット
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

2. ブランチをプッシュ
   ```bash
   git push origin feature/your-feature-name
   ```

3. GitHubでプルリクエストを作成

### PRのテンプレート

```markdown
## 変更内容
<!-- 何を変更しましたか -->

## 関連Issue
<!-- 関連するIssue番号 -->

## テスト方法
<!-- 変更内容を確認する手順 -->

## チェックリスト
- [ ] コードが規約に従っている
- [ ] テストが追加/更新されている
- [ ] ドキュメントが更新されている
```

---

## リリース手順

1. バージョン番号を更新
   ```bash
   # pyproject.toml
   version = "1.0.0"
   ```

2. リリースノートを作成

3. タグを作成
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

4. GitHubでリリースを作成

---

## ライセンス

このプロジェクトはMITライセンスです。貢献者は以下に同意することとします：

- コードはMITライセンスで配布されます
- 貢献者のコードがプロジェクトに含まれます

---

## 行動規範

- 尊敬と建設的なコミュニケーション
- 多様な視点を歓迎
- 建設的なフィードバック

---

## 貢献者の認識

すべての貢献者はCONTRIBUTORS.mdに記載されます。
