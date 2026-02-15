# GLM vs Opus トラブルシューティング比較

**日時:** 2026-02-15
**対象:** websnapshot v2.0.0 (devブランチ)
**問題:** フルページスクリーンショットの欠損問題

---

## 問題の概要

フルページスクリーンショットを取得すると、画像サイズ（解像度）は正しいが、
**ビューポート外のコンテンツが空白になる**問題が発生していた。

- ビューポートモード（1920x1080）: 正常
- フルページモード（1920x10538）: 高さは正しいが、上部1画面分のみ描画、残り約85%が空白

---

## GLM エージェントの対応（解決できず）

### 試行履歴

| # | 試行内容 | 変更点 | 結果 |
|---|----------|--------|------|
| 1 | タイムアウト値の引き上げ | `timeout=30000` → `timeout=60000` | 失敗。フォント待機は解消しない |
| 2 | wait_until条件の変更 | `wait_until='networkidle'` → `'domcontentloaded'` | 失敗。gotoは成功するが、screenshotフェーズでタイムアウト |
| 3 | ブラウザ起動オプション | フォント関連オプション追加<br>`--disable-font-subpixel-positioning`<br>`--disable-features=FontLookupTable` | 失敗。Playwrightの内部待機には影響しない |
| 4 | CDPへの切り替え | `page.screenshot()` → CDPの`Page.captureScreenshot` | タイムアウト解消。**但し新たな問題（画像欠損）発生** |

### GLMが実装したCDPコード

```python
cdp = await page.context.new_cdp_session(page)

if full_page:
    result = await cdp.send('Page.captureScreenshot', {
        'clip': {
            'x': 0,
            'y': 0,
            'width': width,
            'height': await page.evaluate('document.documentElement.scrollHeight'),
            'scale': 1
        }
    })
```

### GLMのアプローチの問題点

1. **根本的な誤解:** `clip`パラメータは「指定範囲をキャプチャする」ものではなく、
   「**レンダリング済みの領域から指定範囲を切り出す**」もの

2. **Chromiumのレンダリング仕様の無視:** Chromiumはパフォーマンス最適化のため、
   ビューポート外のコンテンツをレンダリングしない

3. **原因の特定に至らず:** ファイルサイズが617KBしかない（1920x10538に対して異常に小さい）
   という事実から、大部分が空白であることは推測できたはずだが、
   そこから「ビューポート拡大が必要」という解決策に至らなかった

---

## Opus エージェントの解決策

### 解決のアプローチ

Chrome DevToolsの「Capture full size screenshot」が内部で行っている処理を分析し、
その仕組みを適用することで解決。

### 技術的洞察

**Chrome DevToolsのフルページキャプチャ仕様:**
1. ビューポートをページ全体のサイズに一時的に拡大
2. Chromiumに全コンテンツをレンダリングさせる
3. キャプチャ後にビューポートを元に戻す

### Opusが実装したコード

```python
cdp = await page.context.new_cdp_session(page)

if full_page:
    # Step 1: ページ全体の正確なサイズを取得
    layout = await cdp.send('Page.getLayoutMetrics')
    content_width = int(layout['contentSize']['width'])
    content_height = int(layout['contentSize']['height'])

    # Step 2: ビューポートをページ全体に拡大して全コンテンツをレンダリング
    await cdp.send('Emulation.setDeviceMetricsOverride', {
        'mobile': False,
        'width': content_width,
        'height': content_height,
        'deviceScaleFactor': 1,
    })
    await page.wait_for_timeout(500)  # レンダリング完了待機

    # Step 3: キャプチャ（clip不要、captureBeyondViewportで全ページ取得）
    result = await cdp.send('Page.captureScreenshot', {
        'format': 'png',
        'captureBeyondViewport': True,
    })

    # Step 4: ビューポートを元に戻す
    await cdp.send('Emulation.clearDeviceMetricsOverride')
else:
    # ビューポートのみキャプチャ
    result = await cdp.send('Page.captureScreenshot', {
        'format': 'png',
        'clip': {
            'x': 0, 'y': 0,
            'width': width,
            'height': height,
            'scale': 1
        }
    })
```

### Opusの解決のポイント

| ポイント | 技術的内容 | 効果 |
|----------|-----------|------|
| 1 | `Page.getLayoutMetrics` で正確なページサイズ取得 | JavaScriptの`scrollHeight`より正確 |
| 2 | `Emulation.setDeviceMetricsOverride` でビューポート拡大 | Chromiumが全コンテンツをレンダリング |
| 3 | 500ms待機 | レンダリング完了を待つ |
| 4 | `captureBeyondViewport: True` | clipパラメータ不要、ビューポート外もキャプチャ |
| 5 | `Emulation.clearDeviceMetricsOverride` でリセット | 後続処理に影響なし |

---

## 結果の比較

### テストサイト: jin115.com

| 指標 | GLM（修正前） | Opus（修正後） | 変化 |
|------|--------------|---------------|------|
| ファイル名 | test-fullpage.png | test-fix-jin115.png | - |
| 解像度 | 1920 x 10538 | 1920 x 10538 | 変化なし |
| ファイルサイズ | **617 KB** | **5,967 KB** | **約10倍増加** |
| 描画内容 | 上部1画面分のみ、残り85%が空白 | ページ全体が正しく描画 | **完全に修正** |

### ファイルサイズから読み取れる事実

1920x10538ピクセルのフルカラーPNG画像の理論上のファイルサイズは、
コンテンツが充実していれば数MB〜十数MBになるはず。

- **617KB（修正前）:** 大部分が単色の背景色 → 空白であることの証拠
- **5,967KB（修正後）:** 全ピクセルにコンテンツデータ → 正しく描画されている証拠

---

## なぜ GLM は解決できなかったのか

### 原因分析

1. **表面的な問題解決にとどまった**
   - タイムアウト→値を増やす
   - フォント待機→CDPに切り替え
   - しかし、CDPの`clip`パラメータの仕様を深く理解しなかった

2. **Chromiumのレンダリング仕様を考慮しなかった**
   - 「ビューポート外はレンダリングされない」という基本仕様を考慮していなかった
   - `clip`で高さを指定すればその分キャプチャできるという誤った前提

3. **異常値の分析不足**
   - 617KBという小さなファイルサイズから、大部分が空白であることは推測できたはず
   - そこから「何故空白になるのか？」→「ビューポート外がレンダリングされていないから」→
     「ビューポートを拡大すれば良い」という論理的帰結に至れなかった

4. **既存の実装のリサーチ不足**
   - Chrome DevToolsがフルページキャプチャをどのように実現しているか
   - その情報を検索・参考にするアプローチをとらなかった

---

## なぜ Opus は解決できたのか

### 成功の要因

1. **問題の本質を見抜いた**
   - 画像サイズは正しいが内容が空白 → 「キャプチャ領域の指定」ではなく「レンダリング問題」であると特定

2. **Chrome DevToolsの実装を参考にした**
   - Chrome DevToolsの「Capture full size screenshot」は内部でどのような処理をしているか
   - その仕組み（ビューポート拡大）を調査し適用

3. **CDP APIの正しい使用方法**
   - `Page.getLayoutMetrics` で正確なサイズ取得
   - `Emulation.setDeviceMetricsOverride` でビューポート操作
   - `captureBeyondViewport` で全ページキャプチャ

4. **論理的推論**
   - ファイルサイズ617KB → 大部分空白 → ビューポート外がレンダリングされていない
   - 解決策: ビューポートを拡大して全コンテンツをレンダリングさせる

---

## 教訓・学び

### 1. 問題の根本原因を特定する

表面的な対処療法（タイムアウト値の変更など）ではなく、
「なぜ空白になるのか？」という根本原因に向き合う重要性。

### 2. 既存の動作する実装を参考にする

Chrome DevToolsや既存のツールがどのような問題をどのように解決しているか、
リサーチすることの重要性。

### 3. 技術仕様を理解する

使用しているAPI（今回はCDP）の仕様を正しく理解することの重要性。
- `clip` は何をするものか
- Chromiumはいつ何をレンダリングするか

### 4. データから推論する

ファイルサイズやログなどのデータから、何が起きているか推論することの重要性。

### 5. 問題の階層を理解する

| 階層 | 問題 | 解決アプローチ |
|------|------|---------------|
| アプリケーション | Playwrightのscreenshot()がタイムアウト | CDPに切り替え |
| API | CDPのclipで画像欠損 | ビューポート拡大 |
| プラットフォーム | Chromiumのレンダリング仕様 | 仕様に合わせた実装 |

---

## コミット履歴

| コミット | エージェント | 内容 |
|----------|------------|------|
| b5f11ca | GLM | CDPへの切り替え（画像欠損問題あり） |
| [opus-fix] | Opus | ビューポート拡大による完全な解決 |

---

## まとめ

GLMは「Playwrightのタイムアウト問題」の解決には成功したが、
その代償として発生した「フルページキャプチャの欠損問題」を解決できなかった。

OpusはChrome DevToolsの実装を参考に、CDPの正しい使用方法（ビューポート拡大）を
適用することで、両方の問題を同時に解決した。

**鍵となる洞察:** 「ビューポート外はレンダリングされない」というChromiumの仕様を
理解し、それを回避するためにビューポートを一時的に拡大する。

---

## 参考情報

### 使用したCDPコマンド

| コマンド | 目的 |
|----------|------|
| `Page.getLayoutMetrics` | ページ全体の正確なサイズ取得 |
| `Emulation.setDeviceMetricsOverride` | ビューポートサイズの上書き |
| `Page.captureScreenshot` | スクリーンショットキャプチャ |
| `Emulation.clearDeviceMetricsOverride` | ビューポート設定のリセット |

### 関連ファイル

- `websnapshot/screenshot.py` - 修正対象ファイル
- `trouble/REPORT.md` - GLMによる初期調査レポート
- `trouble/FIX_HISTORY.md` - 改修履歴の詳細
- `trouble/test-fullpage.png` - GLMの実装結果（欠損あり）
- `trouble/test-fix-jin115.png` - Opusの実装結果（正常）
