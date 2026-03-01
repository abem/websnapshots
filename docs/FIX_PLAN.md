# 不備修正計画書

作成日: 2026-02-28
ブランチ: fix/cli-improvements

---

## 1. 現状の問題点

### 1.1 cli.py の重複関数

- `validate_options()` (行18) と `validate_args()` (行172) が類似機能
- どちらも引数バリデーションを行うが、役割が重複している

### 1.2 使用していないインポート

- `cli.py` の `from playwright.async_api import Error as PlaywrightError` は使用されているが、エラーハンドリングが不完全

### 1.3 テスト不足

- 新規追加した `--output-dir`, `--batch` 機能のテストがない

---

## 2. 修正内容

### 2.1 cli.py のリファクタリング

| 修正項目 | 内容 |
|----------|------|
| 関数統合 | `validate_options()` と `validate_args()` を統合 |
| エラー処理改善 | より詳細なエラーメッセージ |

### 2.2 テスト追加

| テスト項目 | 内容 |
|------------|------|
| test_output_dir | --output-dir オプションのテスト |
| test_batch | --batch オプションのテスト |
| test_validate | 引数バリデーションのテスト |

---

## 3. 実施手順

1. **新規ブランチ作成**
   ```bash
   git checkout -b fix/cli-improvements
   ```

2. **cli.py 修正**
   - バリデーション関数の統合
   - エラーメッセージの改善

3. **テスト追加**
   - `test_cli.py` を作成
   - 新機能のテストケースを追加

4. **動作確認**
   - 手動テスト実施
   - 自動テスト実行

5. **コミット・プッシュ**
   ```bash
   git add .
   git commit -m "Fix: CLI improvements and test additions"
   git push origin fix/cli-improvements
   ```

---

## 4. 影響範囲

| ファイル | 影響 |
|----------|------|
| `websnapshot/cli.py` | リファクタリング |
| `test_cli.py` | 新規作成 |
| その他 | 変更なし |

---

## 5. ロールバック手順

問題が発生した場合：

```bash
git checkout main
git branch -D fix/cli-improvements
```

---

## 6. 承認

- [ ] 計画内容の確認
- [ ] 実施の承認
