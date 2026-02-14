# API リファレンス

Web Snapshot Tool v2.0.0 のAPIリファレンスです。

**パッケージ構成:**
- `websnapshot` パッケージ（モジュール形式）
- 従来のスクリプト（後方互換性のため維持）

---

## 目次

1. [GLM-4V API](#glm-4v-api)
2. [Python API](#python-api)
3. [コマンドラインAPI](#コマンドラインapi)

---

## GLM-4V API

### 概要

GLM-4VはZhipuAIが提供するマルチモーダルAIモデルで、画像理解・分析が可能です。

### 利用可能なモデル

| モデル名 | 説明 | パラメータ数 |
|---------|------|------------|
| `glm-4v` | 基本のビジョンモデル | - |
| `glm-4v-plus` | 高性能版ビジョンモデル | - |
| `glm-4.6v` | フラッグシップマルチモーダルモデル（2025年12月） | - |
| `glm-4.5v` | 新世代視覚推論モデル | 106B |
| `glm-4v-plus-0111` | 動画理解対応モデル | - |

### モデルフォールバック

ツールは以下の順序でモデルを自動的に試行します：

```
glm-4v → glm-4v-plus → glm-4.6v → glm-4.5v
```

エラーコード1211（モデルが存在しない）を受信した場合、次のモデルを自動的に試行します。

### APIリクエスト形式

```python
client = ZhipuAiClient(api_key="your_api_key")

response = client.chat.completions.create(
    model="glm-4v",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "この画像を説明してください"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,<base64_data>"}
                }
            ]
        }
    ],
    temperature=0.3,
    max_tokens=2000
)
```

### APIレスポンス形式

```json
{
  "choices": [
    {
      "message": {
        "content": "画像の説明テキスト..."
      }
    }
  ]
}
```

### 制限事項

| 項目 | 制限 |
|------|------|
| 画像サイズ | 最大10MB |
| 画像フォーマット | PNG, JPEG, WEBP |
| 同時リクエスト数 | APIプランによる |
| トークン数 | リクエスト: 最大128K |

---

## Python API

### websnapshot パッケージ

```python
import asyncio
from websnapshot import take_screenshot
from websnapshot.ocr import perform_ocr, generate_ocr_report
from websnapshot.utils import is_valid_url, normalize_url, generate_filename

# 非同期でスクリーンショットを取得
async def capture():
    screenshot_path, ocr_path = await take_screenshot(
        url="https://example.com",
        output_path="screenshot.png",
        width=1920,
        height=1080,
        full_page=True
    )

asyncio.run(capture())

# OCR分析を実行
ocr_result = perform_ocr(
    image_path="screenshot.png",
    api_key="your_api_key",
    languages="ja+en",
    model="glm-4v"
)

# OCRレポートを生成
report = generate_ocr_report(
    ocr_result=ocr_result,
    image_path="screenshot.png",
    url="https://example.com",
    format_type="markdown"
)
```

### compare_images.py（従来のスクリプト）

```python
from compare_images import compare_images_files, create_comparison_report

# 画像を比較
result = compare_images_files(
    image1_path="before.png",
    image2_path="after.png",
    hash_algorithm="phash",
    threshold=0.95
)

# レポートを生成
report = create_comparison_report(
    image1_path="before.png",
    image2_path="after.png",
    comparison_result=result,
    diff_image_path="diff.png"
)
```

### glm_diff.py（従来のスクリプト）

```python
from glm_diff import analyze_with_glm4v, generate_glm_comparison_report

# GLM-4Vで分析
analysis = analyze_with_glm4v(
    image1_path="before.png",
    image2_path="after.png",
    api_key="your_api_key",
    model="glm-4v"
)

# レポートを生成
report = generate_glm_comparison_report(
    image1_path="before.png",
    image2_path="after.png",
    analysis=analysis,
    diff_image_path="side_by_side.png"
)
```

---

## コマンドラインAPI

### websnapshot パッケージ

```bash
# 方法1: Pythonモジュールとして実行
python -m websnapshot <URL> [OPTIONS]

# 方法2: インストール済みコマンドを使用
web-snapshot <URL> [OPTIONS]

# 方法3: 短縮コマンドを使用
ws <URL> [OPTIONS]
```

| オプション | タイプ | 説明 | デフォルト |
|-----------|--------|------|----------|
| `url` | string | 対象URL（必須） | - |
| `--width` | int | ウィンドウ幅（px） | 1920 |
| `--height` | int | ウィンドウ高さ（px） | 1080 |
| `--output`, `-o` | string | 出力ファイルパス | 自動生成 |
| `--viewport` | flag | ビューポートのみ撮影 | false（フルページ） |
| `--wait` | int | 待機時間（ms） | なし |
| `--ocr` | flag | OCR分析を実行 | false |
| `--ocr-lang` | string | OCR対象言語（+区切り） | ja+en |
| `--ocr-output` | string | OCR出力ファイルパス | 自動生成 |
| `--ocr-format` | string | text/json/markdown | markdown |
| `--ocr-model` | string | GLMモデル名 | glm-4v |
| `--ocr-api-key` | string | GLM APIキー | 環境変数から取得 |

### compare_images.py（従来のスクリプト）

```bash
compare-images <IMAGE1> <IMAGE2> [OPTIONS]
```

| オプション | タイプ | 説明 | デフォルト |
|-----------|--------|------|----------|
| `image1` | string | 1つ目の画像（必須） | - |
| `image2` | string | 2つ目の画像（必須） | - |
| `--output`, `-o` | string | レポート出力先 | 自動生成 |
| `--diff-image`, `-d` | string | 差分画像出力先 | 自動生成 |
| `--hash-algorithm` | string | aHash, pHash, dHash, wHash | phash |
| `--threshold` | float | 類似度閾値（0.0-1.0） | 0.95 |
| `--no-diff` | flag | 差分画像を生成しない | false |

### glm_diff.py（従来のスクリプト）

```bash
glm-diff <IMAGE1> <IMAGE2> [OPTIONS]
```

| オプション | タイプ | 説明 | デフォルト |
|-----------|--------|------|----------|
| `image1` | string | 1つ目の画像（必須） | - |
| `image2` | string | 2つ目の画像（必須） | - |
| `--api-key`, `-k` | string | GLM APIキー | GLM_API_KEY環境変数 |
| `--model` | string | glm-4v, glm-4v-plus, glm-4.6v, glm-4.5v | glm-4v |
| `--output`, `-o` | string | レポート出力先 | 自動生成 |
| `--json` | flag | JSON形式でも出力 | false |
| `--side-by-side` | flag | サイドバイサイド画像生成 | false |

---

## 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `GLM_API_KEY` | GLM-4V APIキー | AI機能使用時 |

---

## SDK対応

### zai-sdk（推奨）

```python
from zai import ZhipuAiClient

client = ZhipuAiClient(api_key="your_api_key")
```

### zhipuai（フォールバック）

```python
from zhipuai import ZhipuAI

client = ZhipuAI(api_key="your_api_key")
```

---

## エラーコード

| コード | メッセージ | 原因 | 対処 |
|--------|-----------|------|------|
| 1211 | 模型不存在 | モデルが存在しない | フォールバック機能で自動リトライ |
| 401 | 認証エラー | APIキーが無効 | APIキーを確認してください |
| 429 | リクエスト過多 | レート制限 | 時間を置いて再試行してください |
| 500 | サーバーエラー | 内部エラー | 時間を置いて再試行してください |

---

## 参考リンク

- [ZhipuAI 公式ドキュメント](https://docs.bigmodel.cn/)
- [GLM Cookbook](https://github.com/MetaGLM/glm-cookbook)
- [zai-sdk GitHub](https://github.com/MetaGLM/zhipuai-sdk-python-v4)
