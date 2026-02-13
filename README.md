# Web Snapshot Tool

Webページのスクリーンショットをコマンドラインから簡単に取得するPythonツール。
2つの画像を比較し、差分を可視化する機能も提供します。

## 機能一覧

### スクリーンショット取得 (web_snapshot.py)

- **シンプルなCLI**: コマンドラインから直感的に操作可能
- **URLバリデーション**: 無効なURLを自動検出
- **カスタムサイズ**: 任意のウィンドウサイズでスクリーンショット取得
- **プロトコル省略対応**: `https://` の省略に対応
- **非同期処理**: Playwrightを使用した高速なページ読み込み

### 画像比較 (compare_images.py)

- **複数のハッシュアルゴリズム**: aHash, pHash, dHash, wHashをサポート
- **差分可視化**: ピクセル単位の差分を赤色で強調表示
- **類似度スコア**: 知覚画像ハッシュによる定量的な類似度判定
- **Markdownレポート**: 比較結果を構造化されたレポートとして出力
- **詳細統計**: 異なるピクセル数、最大差分値、平均差分値を表示

### AI画像差分分析 (glm_diff.py)

- **GLM-4V API使用**: 高度なAIによる意味的な差分分析
- **テキスト認識**: 追加・削除・変更されたテキストを検出
- **視覚的変化**: 色、レイアウト、UI要素の変化を分析
- **構造化JSON**: 差分情報を構造化されたJSON形式で出力
- **推奨事項**: デプロイ判断のためのAIアドバイスを提供

## 動作環境

- Python 3.7+
- Linux / macOS / Windows

## インストール

### 方法1: uvを使用（推奨）

```bash
# uvが未インストールの場合
curl -LsSf https://astral.sh/uv/install.sh | sh

# 仮想環境の作成と依存ライブラリのインストール
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# ブラウザのインストール
playwright install chromium
```

### 方法2: pipを使用

```bash
# 仮想環境の作成
python3 -m venv .venv
source .venv/bin/activate

# 依存ライブラリのインストール
pip install -r requirements.txt

# ブラウザのインストール
playwright install chromium
```

### GLM-4V AI分析を使用する場合

GLM-4V APIを使用したAI画像差分分析機能を利用するには、追加で以下のライブラリが必要です：

```bash
# 新しいSDK（推奨）
pip install zai-sdk

# または古いSDK（フォールバック用）
pip install zhipuai
```

**APIキーの取得:**
- [ZhipuAI公式サイト](https://open.bigmodel.cn/) でアカウントを作成
- APIキーを取得して環境変数に設定
```bash
export GLM_API_KEY="your_api_key_here"
```

## 使用方法

### 基本的な使い方

```bash
# URLを指定してスクリーンショットを取得
python web_snapshot.py https://example.com

# 出力ファイル名を指定
python web_snapshot.py https://example.com --output my-screenshot.png

# ウィンドウサイズを指定
python web_snapshot.py https://example.com --width 1280 --height 720

# プロトコルを省略（https://が自動的に補完されます）
python web_snapshot.py example.com
```

### コマンドラインオプション

| オプション | 省略形 | 説明 | デフォルト値 |
|-----------|--------|------|--------------|
| `url` | - | スクリーンショットを取得するURL（必須） | - |
| `--width` | - | ウィンドウの幅（ピクセル） | 1920 |
| `--height` | - | ウィンドウの高さ（ピクセル） | 1080 |
| `--output` | `-o` | 出力ファイル名 | `screenshot-{timestamp}.png` |
| `--wait` | - | ページ読み込み後の追加待機時間（ミリ秒） | なし |
| `--full-page` | - | フルページスクリーンショットを取得する | false |
| `--help` | `-h` | ヘルプを表示 | - |

### 使用例

```bash
# デフォルトサイズ（1920x1080）で取得
python web_snapshot.py https://example.com

# モバイルサイズ（375x667）で取得
python web_snapshot.py https://example.com --width 375 --height 667 --output mobile.png

# フルページスクリーンショットを取得
python web_snapshot.py https://example.com --full-page --output full-page.png

# ページ読み込み後に2秒待機してから撮影
python web_snapshot.py https://example.com --wait 2000

# 複数のサイトを連続して取得
for url in https://example.com https://example.org; do
    python web_snapshot.py "$url"
done
```

### 画像比較の使い方 (compare_images.py)

```bash
# 2つの画像を比較
python compare_images.py image1.png image2.png

# 出力ファイル名を指定
python compare_images.py image1.png image2.png --output report.md

# 差分画像も出力
python compare_images.py image1.png image2.png --diff-image diff.png

# ハッシュアルゴリズムを指定
python compare_images.py image1.png image2.png --hash-algorithm ahash

# 閾値を調整
python compare_images.py image1.png image2.png --threshold 0.90

# 差分画像を生成せずレポートのみ
python compare_images.py image1.png image2.png --no-diff
```

### 画像比較コマンドラインオプション

| オプション | 省略形 | 説明 | デフォルト値 |
|-----------|--------|------|--------------|
| `image1` | - | 比較する1つ目の画像（必須） | - |
| `image2` | - | 比較する2つ目の画像（必須） | - |
| `--output` | `-o` | 出力Markdownファイルパス | `comparison_report-{timestamp}.md` |
| `--diff-image` | `-d` | 差分画像の出力パス | `diff-{timestamp}.png` |
| `--hash-algorithm` | - | ハッシュアルゴリズム | `phash` |
| `--threshold` | - | 差分と判定する閾値（0-1） | `0.95` |
| `--no-diff` | - | 差分画像を生成しない | false |
| `--help` | `-h` | ヘルプを表示 | - |

### 画像比較の使用例

```bash
# 基本的な比較
python compare_images.py screenshot-20260213T180720.png screenshot-20260213T181017.png

# 詳細なレポートを生成
python compare_images.py image1.png image2.png --output detailed_report.md

# より厳密な比較（閾値0.98）
python compare_images.py image1.png image2.png --threshold 0.98

# aHashアルゴリズムで比較
python compare_images.py image1.png image2.png --hash-algorithm ahash

# レポートのみ生成（差分画像なし）
python compare_images.py image1.png image2.png --no-diff --output quick_report.md
```

### AI画像差分分析の使い方 (glm_diff.py)

```bash
# APIキーの設定
export GLM_API_KEY="your_api_key_here"

# 基本的なAI分析
python glm_diff.py image1.png image2.png

# URLから直接比較
python glm_diff.py https://example.com https://example.org

# JSONとサイド・バイ・サイド画像も出力
python glm_diff.py image1.png image2.png --json --side-by-side

# 出力ファイルを指定
python glm_diff.py image1.png image2.png --output ai_report.md

# モデルを指定して実行
python glm_diff.py image1.png image2.png --model glm-4v-plus
```

### AI画像差分分析コマンドラインオプション

| オプション | 省略形 | 説明 | デフォルト値 |
|-----------|--------|------|--------------|
| `image1` | - | 比較する1つ目の画像（必須） | - |
| `image2` | - | 比較する2つ目の画像（必須） | - |
| `--api-key` | `-k` | GLM APIキー | `$GLM_API_KEY` |
| `--model` | - | 使用するモデル（フォールバックあり） | `glm-4v` |
| `--output` | `-o` | 出力Markdownファイルパス | `glm_diff_report-{timestamp}.md` |
| `--json` | - | JSON形式でも出力 | - |
| `--side-by-side` | - | サイド・バイ・サイド画像を生成 | - |

#### 利用可能なモデル

- `glm-4v`（デフォルト）- 標準的な視覚理解モデル
- `glm-4v-flash` - 無料の高速モデル
- `glm-4v-plus` - 高機能モデル
- `glm-4.6v` - 最新の視覚モデル
- `glm-4.5v` - 第4.5世代モデル

**モデルのフォールバック動作:**

デフォルトの `glm-4v` を使用する場合、モデルが利用できないときは自動的に以下の順序で代替モデルを試します：

```
glm-4v → glm-4v-plus → glm-4.6v → glm-4.5v
```

エラーコード1211（モデルが存在しない）が発生した場合、自動的に次のモデルに切り替わります。

### AI分析の出力例

```json
{
  "overall_similarity": 0.95,
  "summary": "ヘッダーのテキストが変更され、CTAボタンの色が青から緑に変更されています",
  "differences": [
    {
      "type": "text",
      "description": "ヘッダーのキャッチコピーが更新されました",
      "location": "画面上部",
      "severity": "low",
      "before": "ようこそ",
      "after": "こんにちは"
    },
    {
      "type": "element",
      "description": "CTAボタンの色が変更されました",
      "location": "画面中央",
      "severity": "medium",
      "before": "青色",
      "after": "緑色"
    }
  ],
  "text_changes": {
    "added": ["新機能", "無料"],
    "removed": ["ログイン"],
    "modified": []
  },
  "recommendation": "軽微な変更なのでデプロイを推奨します"
}
```

## 出力ファイル

- デフォルトのファイル名形式: `screenshot-{timestamp}.png`
- タイムスタンプ形式: `YYYYMMDDTHHMMSS`（例: `screenshot-20250213T123045.png`）
- 出力形式: PNG（24ビットRGB）

## エラーハンドリング

ツールは以下のエラー状況に対応しています：

| エラー種別 | 説明 |
|-----------|------|
| 無効なURL | URLの形式が正しくない場合 |
| 空のURL | URLが指定されていない場合 |
| 接続エラー | サーバーに接続できない場合 |
| DNS解決エラー | ドメインが存在しない場合 |
| ファイル保存エラー | 出力先に書き込めない場合 |
| 無効なオプション値 | --width/--height に負の値を指定した場合 |
| 無効な待機時間 | --wait に負の値を指定した場合 |
| **画像読み込みエラー** | 指定された画像ファイルが存在しない場合 |
| **閾値エラー** | --threshold に0-1以外の値を指定した場合 |

## トラブルシューティング

### Playwright がインストールされていないエラー

```
エラー: Playwright がインストールされていません。
```

**解決策**:
```bash
pip install playwright
playwright install chromium
```

### ファイルの保存に失敗しました

```
エラー: ファイルの保存に失敗しました: [Errno 13] Permission denied
```

**解決策**:
- 出力先ディレクトリの書き込み権限を確認してください
- 存在するディレクトリを指定してください

### ページの読み込みに失敗しました

```
エラー: ページの読み込みに失敗しました: Page.goto: net::ERR_NAME_NOT_RESOLVED
```

**解決策**:
- URLが正しいか確認してください
- インターネット接続を確認してください
- サイトがダウンしていないか確認してください

### 画像ライブラリがインストールされていないエラー

```
エラー: Pillow がインストールされていません。
```

**解決策**:
```bash
pip install Pillow>=10.0.0 imagehash>=4.3.0
```

### ファイルが見つかりません

```
エラー: ファイルが見つかりません: image.png
```

**解決策**:
- 画像ファイルのパスが正しいか確認してください
- カレントディレクトリにファイルが存在するか確認してください

### GLM-4V API エラー

#### エラーコード1211（モデルが存在しない）

```
Error code: 400 - {'error': {'code': '1211', 'message': '模型不存在，请检查模型代码。'}}
```

**解決策**:
- 自動的にフォールバックモデルを試します
- 手動で別のモデルを指定: `--model glm-4v-plus`
- 利用可能なモデル: `glm-4v`, `glm-4v-flash`, `glm-4v-plus`, `glm-4.6v`, `glm-4.5v`

#### APIキーが設定されていない

```
エラー: APIキーが指定されていません。
--api-key オプションまたは GLM_API_KEY 環境変数を設定してください。
```

**解決策**:
```bash
export GLM_API_KEY="your_api_key_here"
```

#### zhipuai SDK がインストールされていない

```
エラー: zhipuai がインストールされていません。
```

**解決策**:
```bash
# 新しいSDK（推奨）
pip install zai-sdk

# または古いSDK
pip install zhipuai
```

## 開発情報

- **言語**: Python 3
- **スクリーンショット**: Playwright for Python, Chromium（ヘッドレスモード）
- **画像比較**: Pillow (PIL), imagehash

## ライセンス

MIT License

## 貢献

バグ報告や機能リクエストはIssueにてお願いいたします。

## GLM-4V API 詳細

### モデルフォールバック機能

ツールは以下の順序でモデルを自動的に試行します：

```
glm-4v → glm-4v-plus → glm-4.6v → glm-4.5v
```

エラーコード1211（モデルが存在しない）を受信した場合、次のモデルを自動的に試行します。

### 利用可能なモデル

| モデル名 | 説明 |
|---------|------|
| `glm-4v` | 基本のビジョンモデル（デフォルト） |
| `glm-4v-plus` | 高性能版ビジョンモデル |
| `glm-4.6v` | 最新のフラッグシップマルチモーダルモデル（2025年12月リリース） |
| `glm-4.5v` | 新世代視覚推論モデル（106Bパラメータ） |

### SDK対応

- `zai-sdk` (推奨): 最新のZhipuAI SDK
- `zhipuai` (フォールバック): 従来のSDK

## 参考資料

- [ZhipuAI 公式ドキュメント](https://docs.bigmodel.cn/)
- [GLM Cookbook](https://github.com/MetaGLM/glm-cookbook)

## ドキュメント

詳細なドキュメントは以下をご覧ください：

| ドキュメント | 説明 |
|------------|------|
| [SETUP.md](SETUP.md) | セットアップガイド - インストールから動作確認まで |
| [USAGE.md](USAGE.md) | 使用方法ガイド - 各機能の詳細な使い方と実践例 |
| [API_REFERENCE.md](API_REFERENCE.md) | APIリファレンス - GLM-4V APIとコマンドラインリファレンス |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | トラブルシューティング - よくある問題と解決方法 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 開発ガイド - 貢献方法とコーディング規約 |

## クイックリファレンス

### Web スクリーンショット

```bash
# 基本使用
web-snapshot https://example.com

# モバイルサイズ
web-snapshot https://example.com --width 375 --height 667

# フルページ
web-snapshot https://example.com --full-page
```

### 画像比較

```bash
# 基本比較
compare-images before.png after.png

# URL同士の比較
compare-images https://example.com https://example.org

# 厳密な比較
compare-images before.png after.png --threshold 0.98
```

### AI 画像差分分析

```bash
# 基本分析
glm-diff before.png after.png

# JSONとサイドバイサイド画像出力
glm-diff before.png after.png --json --side-by-side

# URL同士の分析
glm-diff https://example.com https://example.org
```

## プロジェクト情報

- **リポジトリ**: https://github.com/abem/websnapshots
- **ライセンス**: MIT License
- **Python**: 3.7+
- **主要ライブラリ**: Playwright, Pillow, imagehash, zai-sdk

## 更新履歴

- **2026-02-13**
  - .envファイルからのAPIキー読み込みに対応
  - ドキュメントを大幅に追加（SETUP, USAGE, API_REFERENCE, TROUBLESHOOTING, DEVELOPMENT）
  - GLM-4Vモデルフォールバック機能の強化

## 貢献

バグ報告や機能リクエスト、プルリクエストを歓迎します。詳細は[DEVELOPMENT.md](DEVELOPMENT.md)をご覧ください。

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルをご覧ください。

## 作者

abem - https://github.com/abem

---

**Made with ❤️ and Python**
