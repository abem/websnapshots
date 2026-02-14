# GLM-4V API モデル名問題調査報告

**調査日:** 2026-02-13
**調査者:** investigator (glm-fix-team)
**タスク:** エラーコード1211の原因究明と正しいモデル名の特定

---

## 1. エラー内容

```
Error code: 400 - {'error': {'code': '1211', 'message': '模型不存在，请检查模型代码。'}}
```

**日本語訳:** モデルが存在しません。モデルコードを確認してください。

---

## 2. エラーコード1211の意味

[公式エラーコードドキュメント](https://docs.bigmodel.cn/cn/api/api-code)によると：

| エラー分類 | エラーコード | エラーメッセージ |
|-----------|------------|-----------------|
| API呼び出しエラー | 1211 | **モデルが存在しません。モデルコードを確認してください。** |

**原因:**
- 指定したモデルコードが存在しない
- モデル名のタイプミス
- 廃止された（非推奨の）モデルを使用している

---

## 3. 正しいGLM-4Vシリーズのモデル名

### 3.1 現在有効なビジョンモデル

| モデル名 | 説明 | 用途 |
|---------|------|------|
| `glm-4v` | 基本のビジョンモデル | 汎用画像認識・分析 |
| `glm-4v-plus` | 高性能版ビジョンモデル | 高精度な画像・動画理解 |
| `glm-4v-plus-0111` | GLM-4V-Plusの特定バージョン | 動画理解対応 |
| `glm-4.5v` | 新世代視覚推論モデル | MOEアーキテクチャ、106Bパラメータ |
| `glm-4.6v` | フラッグシップマルチモーダルモデル | 2025年12月リリース |

### 3.2 オープンソース版

| モデル名 | 説明 |
|---------|------|
| `GLM-4V-9B` | オープンソース版（9Bパラメータ） |

---

## 4. 正しいAPI呼び出し方法

### 4.1 ZhipuAI公式SDKを使用する場合（推奨）

```bash
# SDKインストール
pip install zai-sdk
```

#### 基本的な呼び出し（Python）

```python
from zai import ZhipuAiClient

client = ZhipuAiClient(api_key="YOUR_API_KEY")

response = client.chat.completions.create(
    model="glm-4v",  # 正しいモデル名
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "この画像を説明してください"},
                {"type": "image_url", "image_url": {
                    "url": "https://example.com/image.jpg"
                }},
            ],
        }
    ],
    temperature=0.5,
)
print(response.choices[0].message.content)
```

#### Base64エンコードされた画像を使用する場合

```python
import base64
from zai import ZhipuAiClient

img_path = "/path/to/image.jpg"
with open(img_path, "rb") as img_file:
    img_base = base64.b64encode(img_file.read()).decode("utf-8")

client = ZhipuAiClient(api_key="YOUR_API_KEY")
response = client.chat.completions.create(
    model="glm-4v-plus-0111",  # 高性能モデルを使用
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": img_base}},
                {"type": "text", "text": "この画像について説明してください"},
            ]
        }
    ]
)
print(response.choices[0].message.content)
```

### 4.2 cURLを使用する場合

```bash
curl --location 'https://api.z.ai/api/paas/v4/chat/completions' \
--header 'Authorization: Bearer YOUR_API_KEY' \
--header 'Content-Type: application/json' \
--data '{
  "model": "glm-4.5v",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "https://example.com/image.jpg"
          }
        },
        {
          "type": "text",
          "text": "この画像を説明してください"
        }
      ]
    }
  ]
}'
```

---

## 5. 古いSDK（zhipuai）との互換性

従来の `zhipuai` パッケージから新しい `zai-sdk` への移行が推奨されています。

```python
# 従来の方法（まだ動作する可能性があります）
from zhipuai import ZhipuAI
client = ZhipuAI(api_key="YOUR_API_KEY")

# 新しい方法（推奨）
from zai import ZhipuAiClient
client = ZhipuAiClient(api_key="YOUR_API_KEY")
```

---

## 6. 推奨アクション

### 実装者が行うべき変更：

1. **モデル名の確認**: 使用しているモデル名が上記の有効なリストに含まれているか確認
2. **モデル名の修正**: `glm-4v` または `glm-4v-plus` / `glm-4v-plus-0111` / `glm-4.5v` に変更
3. **SDKの更新**: 必要に応じて `zai-sdk` へアップグレード
4. **APIキーの確認**: 有効なAPIキーを使用しているか確認

### よくある問題の解決策：

| 問題 | 解決策 |
|------|--------|
| モデル名に大文字が含まれている | 小文字に変換（例: `GLM-4V` → `glm-4v`）|
| バージョン番号が間違っている | 正しいバージョンを確認（例: `glm-4v-plus`）|
| 非推奨モデルを使用している | 新しいモデルに切り替え |

---

## 7. 参考資料

- [ZhipuAI エラーコードドキュメント](https://docs.bigmodel.cn/cn/api/api-code)
- [GLM-4V-Plus-0111 ドキュメント](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-4v-plus-0111)
- [GLM-4.5V ドキュメント](https://docs.z.ai/guides/vlm/glm-4.5v)
- [ZhipuAI Open Platform](https://open.bigmodel.cn/dev/api)
- [GLM Cookbook (GitHub)](https://github.com/MetaGLM/glm-cookbook)

---

## 8. まとめ

エラーコード1211は「モデルが存在しない」ことを示しています。解決策は以下の通りです：

1. **推奨モデル**: `glm-4v`, `glm-4v-plus`, `glm-4v-plus-0111`, `glm-4.5v` のいずれかを使用
2. **小文字で記述**: モデル名はすべて小文字
3. **最新SDKの使用**: `zai-sdk` の使用を推奨

**調査完了**
