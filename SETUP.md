# セットアップガイド

Web Snapshot Toolのインストールから最初の実行までの手順を詳しく説明します。

---

## 目次

1. [システム要件](#システム要件)
2. [インストール手順](#インストール手順)
3. [APIキーの設定](#apiキーの設定)
4. [動作確認](#動作確認)
5. [次のステップ](#次のステップ)

---

## システム要件

### 必須要件

| 項目 | 要件 |
|------|------|
| Python | 3.7 以上 (推奨: 3.10+) |
| OS | Linux / macOS / Windows |
| ディスク容量 | 約500MB（ブラウザ含む） |
| メモリ | 2GB 以上 |

### オプション要件

| 機能 | 追加要件 |
|------|----------|
| AI画像差分分析 | GLM APIキー（無料枠あり） |
| OCR機能 | PaddleOCR（追加1GB+） |
| オブジェクト検出 | OpenCV（追加100MB） |

---

## インストール手順

### 方法1: uvを使用（推奨）

uvは高速なPythonパッケージマネージャーです。

```bash
# 1. uvのインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. リポジトリのクローン
git clone https://github.com/abem/websnapshots.git
cd websnapshots

# 3. 仮想環境の作成
uv venv

# 4. 仮想環境の有効化
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate     # Windows

# 5. 依存ライブラリのインストール
uv pip install -r requirements.txt

# 6. Playwrightブラウザのインストール
playwright install chromium
```

### 方法2: pipを使用

```bash
# 1. リポジトリのクローン
git clone https://github.com/abem/websnapshots.git
cd websnapshots

# 2. 仮想環境の作成
python3 -m venv .venv

# 3. 仮想環境の有効化
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate     # Windows

# 4. 依存ライブラリのインストール
pip install -r requirements.txt

# 5. Playwrightブラウザのインストール
playwright install chromium
```

### 方法3: スクリプトから直接使用

git cloneせずに単一のスクリプトを使用する場合：

```bash
# 1. 必要なライブラリのインストール
pip install playwright pillow

# 2. ブラウザのインストール
playwright install chromium

# 3. スクリプトのダウンロード
curl -O https://raw.githubusercontent.com/abem/websnapshots/main/web_snapshot.py
chmod +x web_snapshot.py

# 4. 実行
python web_snapshot.py https://example.com
```

---

## APIキーの設定

### GLM-4V APIキーの取得（AI機能を使用する場合）

1. [ZhipuAI](https://open.bigmodel.cn/) にアクセス
2. アカウントを作成（無料）
3. APIキーを取得
4. `.env`ファイルを作成

```bash
# .env.example をコピー
cp .env.example .env

# エディタで編集
vim .env
```

`.env`ファイルの内容：
```
GLM_API_KEY=your_actual_api_key_here
```

### .envファイルの設置場所

ツールは以下の場所から`.env`ファイルを検索します（優先順位順）：

1. カレントディレクトリ: `./.env`
2. スクリプトディレクトリ: `<リポジトリ>/websnapshots/.env`
3. ユーザーディレクトリ: `~/.websnapshots/.env`
4. ホームディレクトリ: `~/.env`

---

## 動作確認

### 基本動作確認

```bash
# スクリーンショット機能
python web_snapshot.py https://example.com

# 画像比較機能
python compare_images.py screenshot-2024*.png screenshot-2024*.png
```

### AI機能の動作確認

```bash
# GLM-4V APIを使った画像差分分析
python glm_diff.py https://example.com https://example.org --json
```

成功していれば、以下のような出力が表示されます：

```
GLM-4V AI画像差分分析を開始: https://example.com vs https://example.org
スクリーンショットを取得中: https://example.com
スクリーンショットを取得中: https://example.org
GLM-4Vで分析中... (モデル: glm-4.6v)
類似度: 0.85
要約: [分析結果]
```

---

## 次のステップ

- [使用方法ガイド](USAGE.md) - 各機能の詳細な使い方
- [APIリファレンス](API_REFERENCE.md) - GLM-4V APIの詳細
- [トラブルシューティング](TROUBLESHOOTING.md) - 問題解決ガイド

---

## よくある質問

### Q: 既存のPython環境にインストールせずに使えますか？

A: はい、Dockerを使用することもできます：

```bash
docker build -t websnapshots .
docker run -v $(pwd)/output:/app/output websnapshots https://example.com
```

### Q: プロキシ環境下でも動作しますか？

A: はい、環境変数で設定してください：

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

### Q: 日本語以外のページでも動作しますか？

A: はい、GLM-4Vは日本語、英語、中国語、韓国語など多言語に対応しています。

---

## 更新履歴

- 2026-02-13: 初版作成
- 2026-02-13: .envファイル対応追加
