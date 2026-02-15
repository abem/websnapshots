# トラブルシューティングレポート

## 問題概要

**日時:** 2026-02-15
**バージョン:** websnapshot v2.0.0 (devブランチ)
**問題:** スクリーンショットが一部しか取れていない

---

## 経緯詳細

### 1. 初期問題: タイムアウトエラー

最初に以下のURLでテスト実行：

```bash
web-snapshot https://abem2.tailf8b3c7.ts.net/overview
```

**エラー内容:**
```
エラー: ページの読み込みに失敗しました: Page.goto: net::ERR_NAME_NOT_RESOLVED
```
→ DNS解決の問題（Tailscaleネットワーク名）

### 2. 2回目の試行: chat.z.ai

```bash
web-snapshot https://chat.z.ai/
```

**エラー内容:**
```
エラー: ページの読み込みに失敗しました: Page.goto: Timeout 30000ms exceeded.
```
→ 30秒タイムアウト

### 3. 3回目の試行: jin115.com

```bash
web-snapshot https://jin115.com/
```

**エラー内容:**
```
エラー: ページの読み込みに失敗しました: Page.goto: Timeout 30000ms exceeded.
```
→ 複数サイトで同様のタイムアウト

---

## 修正試行履歴

### 試行1: タイムアウト値の引き上げ

**変更:** `timeout=30000` → `timeout=60000`

**結果:** 失敗（まだタイムアウト）

### 試行2: wait_until条件の変更

**変更:** `wait_until='networkidle'` → `wait_until='domcontentloaded'`

**結果:** 失敗（screenshotフェーズでタイムアウト）

### 試行3: ブラウザ起動オプション

**変更:** フォントレンダリング無効化オプション追加
```python
browser = await p.chromium.launch(
    headless=True,
    args=['--disable-font-subpixel-positioning', '--disable-features=FontLookupTable']
)
```

**結果:** 失敗

### 試行4: CDP（Chrome DevTools Protocol）使用

**変更:** Playwrightの`screenshot()`メソッドからCDPの`Page.captureScreenshot`に変更

**実装:**
```python
cdp = await page.context.new_cdp_session(page)
result = await cdp.send('Page.captureScreenshot', {
    'clip': {
        'x': 0, 'y': 0,
        'width': width,
        'height': page_height,
        'scale': 1
    }
})
```

**結果:** 成功（エラーなし）

---

## 現在の問題

**現象:** CDP方法でキャプチャ成功しているが、**画像が一部しか取れていない**

**テスト結果:**
- `test-viewport.png`: 1920 x 1080 ✅ 正常
- `test-fullpage.png`: 1920 x 10538 ⚠️ 高さは取得できているが、内容が一部のみ

**想定される原因:**
1. CDPの`clip`パラメータが指定した領域のみをキャプチャしている
2. ページのスクロール位置がトップになっているため、下の部分が空白になっている
3. CDPの`Page.captureScreenshot`は現在のビューポートのみをキャプチャしている可能性

---

## 技術的詳細

### CDP方法の問題点

CDPの`Page.captureScreenshot`の`clip`パラメータ：
- 指定された座標範囲のみをキャプチャ
- ページのスクロールに対応していない
- 実質的に「現在見えている部分」のみを切り出している

### Chromeの「Capture full size screenshot」との違い

Chrome DevToolsの「Capture full size screenshot」：
- 内部的にページをスクロールしながら複数の画像を結合
- CDPコマンドではなく、DevToolsの独自実装

---

## 次のステップ

### オプション1: Playwrightのscreenshot()に戻す

**問題:** フォント読み込みでタイムアウト

**解決策:** JavaScriptで強制的にフォント読み込みを完了させる

### オプション2: CDPでスクロールしながら複数キャプチャ

**方法:** ページを分割してキャプチャし、結合する

### オプション3: 別のライブラリを使用

**候補:**
- Selenium WebDriver
- puppeteer
- playwright-go

---

## 環境情報

- OS: Linux 6.17.0-14-generic
- Python: 3.12
- Playwright: 最新版
- Chromium: 最新版

---

## テストケース

| URL | 結果 | 問題 |
|-----|------|------|
| https://example.com | ✅ 成功 | - |
| https://jin115.com/ | ⚠️ 一部のみ | フルページで下が空白 |
| https://chat.z.ai/ | ❌ タイムアウト | フォント読み込み |

---

## ファイル構成

```
trouble/
├── REPORT.md           # 本ファイル
├── test-viewport.png   # ビューポートモード（1920x1080）
└── test-fullpage.png   # フルページモード（1920x10538）
```
