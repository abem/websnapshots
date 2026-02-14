# 使用方法ガイド

Web Snapshot Toolの各機能の詳細な使用方法を説明します。

---

## 目次

1. [Web スクリーンショット](#web-スクリーンショット)
2. [画像比較](#画像比較)
3. [AI 画像差分分析](#ai-画像差分分析)
4. [実践的な使用例](#実践的な使用例)
5. [コマンド一覧](#コマンド一覧)

---

## Web スクリーンショット

### 基本構文

```bash
python web_snapshot.py <URL> [オプション]
```

### よく使うオプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--width` | ウィンドウ幅（ピクセル） | 1920 |
| `--height` | ウィンドウ高さ（ピクセル） | 1080 |
| `--output`, `-o` | 出力ファイル名 | 自動生成 |
| `--full-page` | フルページスクリーンショット | false |
| `--viewport` | ビューポートのみ撮影 | false |
| `--wait` | 読み込み後待機時間（ms） | なし |

### 使用例

#### デスクトップサイズでキャプチャ

```bash
python web_snapshot.py https://example.com
```

#### モバイルサイズでキャプチャ

```bash
python web_snapshot.py https://example.com --width 375 --height 667 --output mobile.png
```

#### フルページキャプチャ

```bash
python web_snapshot.py https://example.com --full-page
```

#### 待機時間を指定してキャプチャ

```bash
# ページ読み込み後に3秒待機
python web_snapshot.py https://example.com --wait 3000
```

#### 内部IPアドレスからキャプチャ

```bash
python web_snapshot.py http://192.168.1.100:8080/
```

---

## 画像比較

### 基本構文

```bash
python compare_images.py <画像1> <画像2> [オプション]
```

### よく使うオプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--output`, `-o` | レポート出力先 | 自動生成 |
| `--diff-image`, `-d` | 差分画像出力先 | 自動生成 |
| `--hash-algorithm` | ハッシュアルゴリズム | phash |
| `--threshold` | 類似度閾値（0-1） | 0.95 |
| `--no-diff` | 差分画像を生成しない | false |

### 使用例

#### 基本比較

```bash
python compare_images.py before.png after.png
```

#### URL同士の比較

```bash
# 自動的にスクリーンショットを取得して比較
python compare_images.py https://example.com https://example.org
```

#### 閾値を調整して厳密に比較

```bash
python compare_images.py before.png after.png --threshold 0.98
```

#### レポートのみ生成

```bash
python compare_images.py before.png after.png --no-diff --output report.md
```

---

## AI 画像差分分析

### 基本構文

```bash
python glm_diff.py <画像1> <画像2> [オプション]
```

### よく使うオプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--api-key`, `-k` | GLM APIキー | GLM_API_KEY環境変数 |
| `--model` | 使用するモデル | glm-4v |
| `--output`, `-o` | レポート出力先 | 自動生成 |
| `--json` | JSON形式でも出力 | false |
| `--side-by-side` | サイドバイサイド画像生成 | false |

### 使用例

#### 基本分析

```bash
python glm_diff.py before.png after.png
```

#### URL同士の分析

```bash
# スクリーンショットを自動取得してAI分析
python glm_diff.py https://example.com https://example.org
```

#### JSONとサイドバイサイド画像を出力

```bash
python glm_diff.py before.png after.png --json --side-by-side
```

#### 内部IPアドレスの比較

```bash
glm-diff http://192.168.1.129:8080/ http://192.168.1.129:8081/ --json
```

### AI分析の出力例

```markdown
## 全体評価

- **類似度**: 0.85
- **要約**: ヘッダーのテキストが変更され、CTAボタンの色が変更されています

## 差分詳細

### 差分 1: text 🟢
- **説明**: ヘッダーのキャッチコピーが更新されました
- **位置**: 画面上部
- **重要度**: low
- **変更前**: `ようこそ`
- **変更後**: `こんにちは`

### 差分 2: element 🟡
- **説明**: CTAボタンの色が変更されました
- **位置**: 画面中央
- **重要度**: medium
```

---

## 実践的な使用例

### シナリオ1: リグレッションテスト

デプロイ前後でWebページの視覚的な差分を確認：

```bash
# デプロイ前
python web_snapshot.py https://staging.example.com --output before.png

# デプロイ後
python web_snapshot.py https://staging.example.com --output after.png

# 比較
python glm_diff.py before.png after.png --json --side-by-side
```

### シナリオ2: 定期監視

Cronジョブで定期的にスクリーンショットを取得：

```bash
# crontab -e
# 毎時0分にスクリーンショットを保存
0 * * * * cd ~/websnapshots && python web_snapshot.py https://example.com --output "screenshot-$(date +\%Y\%m\%d\%H\%M).png"
```

### シナリオ3: 複数サイトの監視

複数のURLを一括チェック：

```bash
#!/bin/bash
urls=("https://site1.com" "https://site2.com" "https://site3.com")
for url in "${urls[@]}"; do
    python web_snapshot.py "$url" --output "${url##*/}-$(date +%Y%m%d).png"
done
```

### シナリオ4: A/Bテスト比較

A/Bテスト結果の視覚的比較：

```bash
python glm_diff.py https://example.com?variant=A https://example.com?variant=B --json
```

---

## コマンド一覧

### エイリアス

`.bashrc` または `.zshrc` に設定すると便利です：

```bash
# ~/.bashrc または ~/.zshrc
alias web-snapshot='source ~/ドキュメント/websnapshots/.venv/bin/activate && python ~/ドキュメント/websnapshots/web_snapshot.py'
alias compare-images='source ~/ドキュメント/websnapshots/.venv/bin/activate && python ~/ドキュメント/websnapshots/compare_images.py'
alias glm-diff='source ~/ドキュメント/websnapshots/.venv/bin/activate && python ~/ドキュメント/websnapshots/glm_diff.py'
```

### ショートカット

エイリアス設定後の使用例：

```bash
# スクリーンショット
web-snapshot https://example.com

# 画像比較
compare-images before.png after.png

# AI分析
glm-diff before.png after.png --json
```

---

## 注意事項

### URL指定時の注意

- HTTPSのURLは `https://` を省略できます
- HTTPのURLは `http://` を明記してください
- 内部IPアドレスも指定可能です

### 出力ファイルについて

- タイムスタンプ付きのファイル名が自動生成されます
- 形式: `screenshot-YYYYMMDDTHHMMSS.png`
- カスタム名を指定するには `--output` を使用してください

### APIキーについて

- GLM-4V APIを使用するにはAPIキーが必要です
- `.env`ファイルに保存することを推奨します
- APIキーは秘密にしてください

---

## 関連ドキュメント

- [セットアップガイド](SETUP.md)
- [APIリファレンス](API_REFERENCE.md)
- [トラブルシューティング](TROUBLESHOOTING.md)
