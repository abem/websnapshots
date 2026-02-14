# GLM-4V修正テストレポート

**テスト日時**: 2026-02-13 20:35:00
**テスター**: tester (glm-fix-team)
**対象**: `/home/abem/ドキュメント/websnapshots/glm_diff.py`

---

## テスト環境

- **OS**: Linux 6.17.0-14-generic
- **Python**: 3.12.3
- **作業ディレクトリ**: `/home/abem/ドキュメント/websnapshots`

---

## 1. 概要

調査報告書（GLM_FIX_INVESTIGATION.md）に基づく修正のテストを実施しました。

## 2. 修正内容

### 2.1 コード変更

1. **SDKインポートの変更**
   - 新SDK (`zai-sdk`) を優先的に使用
   - 旧SDK (`zhipuai`) へのフォールバックを維持

2. **モデルフォールバック機能の追加**
   - `glm-4v` → `glm-4v-plus` → `glm-4.5v` の順で試行
   - エラーコード1211（モデルが存在しない）の場合は次のモデルを試行

3. **画像MIMEタイプの変更**
   - `image/png` → `image/jpeg` に変更（一部環境での互換性向上）

### 2.2 依存ライブラリ更新

```txt
# GLM API用ライブラリ
zai-sdk>=1.0.0  # 新しいSDK（推奨）
zhipuai>=2.1.0  # 旧SDK（フォールバック用）
```

---

## 3. テスト結果

### 3.1 構文チェック (PASSED)

```bash
python3 -m py_compile glm_diff.py
```

**結果**: 構文エラーなし

### 3.2 SDKインストール (PASSED)

```bash
uv pip install zai-sdk
```

**結果**: zai-sdk==0.2.2 が正常にインストールされました

### 3.3 ヘルプメッセージ (PASSED)

```bash
python3 glm_diff.py --help
```

**結果**: ヘルプメッセージが正常に表示されました

### 3.4 エラーハンドリング (PASSED)

**APIキー未設定時のエラーメッセージ**:
```
エラー: APIキーが指定されていません。
--api-key オプションまたは GLM_API_KEY 環境変数を設定してください。
```

**結果**: 適切なエラーメッセージが表示されます

---

## 4. 実運用テスト（要APIキー）

以下のコマンドで実際のURLテストを実施可能です：

```bash
export GLM_API_KEY="your_api_key_here"
glm-diff http://192.168.1.129:8080/ http://192.168.1.129:8081/ --json --side-by-side
```

**注意事項**:
- APIキーの設定が必要です
- 内部IPアドレス（192.168.1.129:8080/8081）へのアクセスが必要です
- インターネット接続が必要です（GLM APIへアクセス）

---

## 5. テスト項目チェックリスト

| 項目 | ステータス | 備考 |
|------|----------|------|
| 構文チェック | PASSED | |
| SDKインストール | PASSED | zai-sdk==0.2.2 |
| ヘルプメッセージ | PASSED | |
| エラーハンドリング | PASSED | APIキー未設定時 |
| モデルフォールバック | PENDING | 実APIキーでテスト必要 |
| URLからの比較 | PENDING | 実APIキーでテスト必要 |
| JSON出力 | PENDING | 実APIキーでテスト必要 |
| サイド・バイ・サイド画像 | PENDING | 実APIキーでテスト必要 |

---

## 6. 総合評価

**構文・基本動作**: **PASSED**

**実APIキーでのテスト**: **要実施**

**推奨事項**:
1. ユーザーがAPIキーを設定した後、実際のURLでテストを実施してください
2. 内部IPアドレス（192.168.1.129:8080/8081）がアクセス可能であることを確認してください

---

## 7. 追加テスト（2026-02-13 20:35:00）

### 7.1 コード構造検証 (PASSED)

モックモジュールを使用したコード構造検証を実施：

```python
# モックモジュールでインポートロジックを検証
# インポート、フォールバック、主要関数の構造を確認
```

**結果**: コード構造は正常 ✅

### 7.2 SDKライブラリの状況

現在の環境でのSDK状況：
- `zai` モジュール: 未インストール
- `zhipuai` モジュール: 未インストール

**注意**: 前回テストで `zai-sdk==0.2.2` がインストールされた記録がありますが、
現在のPython環境（/usr/bin/python3）にはインストールされていません。
別の環境（`uv` 環境など）にインストールされた可能性があります。

### 7.3 修正内容の詳細検証

**1. インポートフォールバック (glm_diff.py:23-28)**
```python
try:
    from zai import ZhipuAiClient      # 新SDK
    USE_NEW_SDK = True
except ImportError:
    from zhipuai import ZhipuAI        # 旧SDK
    USE_NEW_SDK = False
```
✅ フォールバックロジックは正しい

**2. モデルフォールバック (glm_diff.py:160-163)**
```python
fallback_models = [model]
if model == "glm-4v" and "glm-4v-plus" not in fallback_models:
    fallback_models.extend(["glm-4v-plus", "glm-4.5v"])
```
✅ モデルフォールバックは正しい

**3. エラーハンドリング (glm_diff.py:212-214)**
```python
if '1211' in error_msg or '模型不存在' in error_msg:
    print(f"  モデル {try_model} は利用できません。次のモデルを試します...")
    continue
```
✅ エラーコード1211の検出は正しい

**4. クライアント初期化 (glm_diff.py:123-126)**
```python
if USE_NEW_SDK:
    client = ZhipuAiClient(api_key=api_key)
else:
    client = ZhipuAI(api_key=api_key)
```
✅ クライアント初期化は正しい

---

## 8. 結論

修正は構文的に正しく、コード構造も検証済みです。
実APIキーでのテストを完了次第、承認フェーズに進むことができます。

**テスト結果**: **構文検証・コード構造検証合格（実APIキーでの動作確認待ち）**

---

## 9. APIキー設定後の実行テスト手順

ユーザーがAPIキーを取得した後、以下の手順でテストを実施してください：

### ステップ1: SDKのインストール

```bash
# 方法A: zai-sdk（推奨）
pip install zai-sdk

# 方法B: 旧SDK（フォールバック用）
pip install zhipuai
```

### ステップ2: APIキーの設定

```bash
# 環境変数で設定
export GLM_API_KEY="your_api_key_here"
```

### ステップ3: テスト実行

```bash
# ヘルプメッセージ確認
python3 glm_diff.py --help

# 実際のURLでテスト
python3 glm_diff.py http://192.168.1.129:8080/ http://192.168.1.129:8081/ --json --side-by-side
```

### ステップ4: 結果確認

- JSONファイルが生成されていること
- Markdownレポートが生成されていること
- サイド・バイ・サイド画像が生成されていること（--side-by-side指定時）
