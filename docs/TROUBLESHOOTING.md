# トラブルシューティング

よくある問題とその解決方法をまとめています。

---

## 目次

1. [インストール関連](#インストール関連)
2. [実行時エラー](#実行時エラー)
3. [API関連](#api関連)
4. [パフォーマンス](#パフォーマンス)
5. [その他](#その他)

---

## インストール関連

### Playwright がインストールできない

**エラーメッセージ:**
```
エラー: Playwright がインストールされていません。
```

**解決方法:**

```bash
# Playwrightのインストール
pip install playwright

# ブラウザのインストール
playwright install chromium
```

### 仮想環境が有効化できない

**エラーメッセージ:**
```
source .venv/bin/activate
# bash: .venv/bin/activate: そのようなファイルやディレクトリはありません
```

**解決方法:**

```bash
# 仮想環境の再作成
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### uv コマンドが見つからない

**エラーメッセージ:**
```
uv: コマンドが見つかりません
```

**解決方法:**

```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# パスの再読み込み
source ~/.bashrc  # または source ~/.zshrc
```

---

## 実行時エラー

### 「python: コマンドが見つかりません」

**エラーメッセージ:**
```
bash: python: コマンドが見つかりません
```

**解決方法:**

```bash
# python3を使用する
python3 -m websnapshot https://example.com

# またはインストール済みのコマンドを使用
web-snapshot https://example.com

# またはエイリアスを設定
alias python=python3
```

### URLからスクリーンショットが取得できない

**エラーメッセージ:**
```
エラー: ページの読み込みに失敗しました: Page.goto: net::ERR_NAME_NOT_RESOLVED
```

**解決方法:**

1. URLのスペルを確認してください
2. インターネット接続を確認してください
3. サイトがダウンしていないか確認してください

### ファイルが保存できない

**エラーメッセージ:**
```
エラー: ファイルの保存に失敗しました: [Errno 13] Permission denied
```

**解決方法:**

1. 書き込み権限を確認してください
2. 別のディレクトリを指定してください
   ```bash
   ws https://example.com --output ~/Desktop/screenshot.png
   ```

### 画像読み込みエラー

**エラーメッセージ:**
```
エラー: ファイルが見つかりません: image.png
```

**解決方法:**

1. ファイルパスが正しいか確認してください
2. 絶対パスで指定してください
   ```bash
   python compare_images.py /full/path/to/image1.png /full/path/to/image2.png
   ```

---

## API関連

### APIキーが見つからない

**エラーメッセージ:**
```
エラー: APIキーが指定されていません。
```

**解決方法:**

```bash
# .envファイルの作成
cp .env.example .env

# エディタで編集
vim .env
# GLM_API_KEY=your_actual_api_key_here
```

### 「モデルが存在しません」エラー

**エラーメッセージ:**
```
Error code: 400 - {'error': {'code': '1211', 'message': '模型不存在，请检查模型代码。'}}
```

**解決方法:**

このエラーはツールが自動的にリトライします。以下のモデルを順に試行します：

1. `glm-4v`
2. `glm-4v-plus`
3. `glm-4.6v`
4. `glm-4.5v`

すべて失敗する場合：
- APIキーが有効か確認してください
- [ZhipuAI コンソール](https://open.bigmodel.cn/)でモデル利用権限を確認してください

### コマンドが見つからない（インストール後）

**エラーメッセージ:**
```
bash: web-snapshot: コマンドが見つかりません
bash: ws: コマンドが見つかりません
```

**解決方法:**

```bash
# パッケージを編集可能モードでインストール
pip install -e .

# またはPythonモジュールとして実行
python -m websnapshot https://example.com
```

### python-dotenv がインポートできない

**エラーメッセージ:**
```
ModuleNotFoundError: No module named 'dotenv'
```

**解決方法:**

```bash
# python-dotenvのインストール
pip install python-dotenv
```

---

## パフォーマンス

### スクリーンショットが遅い

**原因:** ページの読み込みに時間がかかっている

**解決方法:**

```bash
# 待機時間を短くする
ws https://example.com --wait 1000

# またはビューポートのみ撮影
ws https://example.com --viewport
```

### メモリ不足エラー

**エラーメッセージ:**
```
MemoryError: ...
```

**解決方法:**

1. 画像サイズを小さくしてください
   ```bash
   ws https://example.com --width 1280 --height 720
   ```

2. ビューポートのみ撮影にしてください
   ```bash
   ws https://example.com --viewport
   ```

---

## その他

### 日本語が文字化けする

**解決方法:**

```bash
# UTF-8エンコーディングを指定
export PYTHONIOENCODING=utf-8
ws https://example.com
```

### プロキシ環境下で動作しない

**解決方法:**

```bash
# プロキシ設定
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

ws https://example.com
```

### 内部IPアドレスにアクセスできない

**解決方法:**

ツールは内部IPアドレスに対応しています。以下のように指定してください：

```bash
ws http://192.168.1.100:8080/
```

それでも動作しない場合：
- ファイアウォール設定を確認してください
- URLにポート番号が含まれているか確認してください

---

## デバッグモード

問題を調査する場合は、デバッグモードを有効にしてください：

```bash
# 詳細ログを出力
export DEBUG=1
python -m websnapshot https://example.com
```

---

## ログの取得

問題報告をする際は、以下の情報を含めてください：

1. Pythonバージョン: `python --version`
2. OSバージョン: `uname -a` (Linux/macOS) または `systeminfo` (Windows)
3. エラーメッセージの全文
4. 再現手順

```bash
# システム情報の収集
python --version
uname -a
pip list | grep -i playwright
```

---

## サポート

問題が解決しない場合は：

1. [既存のIssues](https://github.com/abem/websnapshots/issues)を確認してください
2. 新しいIssueを作成してください（上記の情報を含めてください）
