# 機能改善提案

このドキュメントでは、Web Snapshot Toolの使い勝手を向上させるための改善提案をまとめています。

---

## 1. CLIの使い勝手改善

### 1.1 短縮コマンドの追加

現在の `python -m websnapshot` は入力が長いです。

**提案**: グローバルコマンドを追加

```bash
# ~/.bashrc に追加
alias ws='python -m websnapshot'
alias wsc='python compare_images.py'
```

**使用例**:
```bash
ws https://example.com
wsc before.png after.png
```

### 1.2 設定ファイルのサポート

**提案**: `.websnapshorrc` または `websnapshot.config.yaml` でデフォルト設定を管理

```yaml
# websnapshot.config.yaml
defaults:
  width: 1920
  height: 1080
  full_page: true
  output_dir: ./screenshots

ocr:
  enabled: false
  language: ja+en
  model: glm-4v
```

---

## 2. 出力管理の改善

### 2.1 出力ディレクトリの自動作成

**提案**: `--output-dir` オプションを追加

```bash
python -m websnapshot https://example.com --output-dir ./screenshots
```

### 2.2 ファイル名のカスタマイズ

**提案**: テンプレート形式のファイル名指定

```bash
python -m websnapshot https://example.com --name-template "{domain}_{date}_{time}"
# 出力: example.com_20260228_120000.png
```

**プレースホルダー**:
- `{domain}` - ドメイン名
- `{date}` - 日付 (YYYYMMDD)
- `{time}` - 時刻 (HHMMSS)
- `{timestamp}` - タイムスタンプ

---

## 3. バッチ処理機能

### 3.1 複数URLの一括処理

**提案**: URLリストファイルからの読み込み

```bash
# urls.txt
https://example.com
https://example.org
https://example.net

# 実行
python -m websnapshot --batch urls.txt
```

### 3.2 定期実行スクリプト

**提案**: cron/jobs用のスクリプトテンプレート

```bash
# scripts/scheduled_capture.sh
#!/bin/bash
source .venv/bin/activate
python -m websnapshot https://example.com --output ./daily/$(date +%Y%m%d).png
```

---

## 4. 比較機能の強化

### 4.1 差分の視覚的改善

**提案**:
- 差分領域のハイライト色を選択可能に
- 差分の割合をパーセント表示
- サイドバイサイドにラベル追加

### 4.2 比較履歴の管理

**提案**: 比較結果をJSONで保存し、履歴を追跡

```bash
python compare_images.py before.png after.png --history ./history/
```

---

## 5. エラー処理とフィードバック

### 5.1 詳細なエラーメッセージ

**提案**: エラーの種類に応じた対処法を表示

```
エラー: ページの読み込みに失敗しました
原因: タイムアウト (30秒)
対処法:
  - --wait オプションで待機時間を増やす
  - ネットワーク接続を確認する
  - URLが正しいか確認する
```

### 5.2 進捗表示

**提案**: スクリーンショット取得時の進捗バー

```
スクリーンショットを取得中: https://example.com
[████████████████████░░░░] 80% ページ読み込み中...
```

---

## 6. 統合・連携機能

### 6.1 Slack/Teams通知

**提案**: 比較完了時の通知機能

```bash
python compare_images.py before.png after.png --notify slack --webhook-url $SLACK_WEBHOOK
```

### 6.2 Git連携

**提案**: 比較結果をGitにコミット

```bash
python compare_images.py before.png after.png --git-commit
```

---

## 7. パフォーマンス改善

### 7.1 キャッシュ機能

**提案**: 同じURLの短期間内の再取得をスキップ

```bash
python -m websnapshot https://example.com --cache-ttl 3600  # 1時間キャッシュ
```

### 7.2 並列処理

**提案**: バッチ処理時の並列実行

```bash
python -m websnapshot --batch urls.txt --parallel 4
```

---

## 8. ドキュメント整備

### 8.1 チートシート

主要なコマンドを1枚にまとめたチートシートの作成

### 8.2 トラブルシューティングガイド

よくある問題と解決策をまとめたFAQ

### 8.3 APIドキュメント

Python APIとしての使用方法を詳細に記載

---

## 優先順位

| 優先度 | 機能 | 難易度 | 影響度 |
|--------|------|--------|--------|
| 高 | 短縮コマンド | 低 | 高 |
| 高 | 出力ディレクトリ | 低 | 高 |
| 中 | バッチ処理 | 中 | 高 |
| 中 | 詳細エラーメッセージ | 低 | 中 |
| 低 | キャッシュ機能 | 中 | 低 |
| 低 | Slack通知 | 中 | 低 |

---

## 次のステップ

1. 優先度の高い機能から順に実装
2. 各機能についてユーザーフィードバックを収集
3. ドキュメントを更新

---

*作成日: 2026-02-28*
