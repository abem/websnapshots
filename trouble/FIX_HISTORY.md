# フルページスクリーンショット欠損問題 - 改修履歴

**日時:** 2026-02-15
**対象:** websnapshot v2.0.0 (devブランチ)
**対象ファイル:** `websnapshot/screenshot.py`

---

## 問題の概要

フルページスクリーンショットを取得すると、画像サイズ（解像度）は正しいが、
ビューポート外のコンテンツが描画されず空白になる。
ページの上部（1画面分）しか取得できない。

---

## 発生までの経緯

### Phase 1: オリジナル実装（Playwright screenshot メソッド）

もともとの実装は Playwright の標準APIを使用していた。

```python
# オリジナルコード
await page.goto(url, wait_until='networkidle', timeout=30000)
await page.screenshot(path=output_path, full_page=full_page)
```

**問題:** 一部のサイト（chat.z.ai、jin115.com 等）でフォント読み込みが完了せず、
`page.screenshot()` 内部で無限にフォントレンダリングを待機し、タイムアウトする。

```
エラー: Page.goto: Timeout 30000ms exceeded.
```

### Phase 2: GLMエージェントによる修正試行（コミット b5f11ca）

GLMエージェントが以下の段階的修正を試みた。

#### 試行1: タイムアウト値の引き上げ
- **変更:** `timeout=30000` → `timeout=60000`
- **結果:** 失敗。タイムアウト値を上げてもフォント待機は解消しない。

#### 試行2: wait_until条件の変更
- **変更:** `wait_until='networkidle'` → `wait_until='domcontentloaded'`
- **結果:** goto自体は成功するようになったが、`page.screenshot()` フェーズでタイムアウト。
  Playwrightのscreenshotメソッドが内部でフォントレンダリング完了を待機するため。

#### 試行3: ブラウザ起動オプション
- **変更:** フォント関連オプションを追加
  ```python
  browser = await p.chromium.launch(
      headless=True,
      args=['--disable-font-subpixel-positioning', '--disable-features=FontLookupTable']
  )
  ```
- **結果:** 失敗。Playwright の screenshot() の内部待機には影響しない。

#### 試行4: CDP（Chrome DevTools Protocol）への切り替え
- **変更:** `page.screenshot()` をやめ、CDPの `Page.captureScreenshot` を使用
  ```python
  cdp = await page.context.new_cdp_session(page)
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
- **結果:** タイムアウトは解消。しかし**新たな問題**が発生。

### Phase 3: CDP clip問題の発覚（本問題）

CDP切り替え後、エラーは出なくなったが、取得した画像を確認すると：

- **ビューポートモード（1920x1080）:** 正常
- **フルページモード（1920x10538）:** 高さは正しいが、上部のビューポート分のみ描画され、
  残り約85%が背景色のみの空白

**証拠:**
| ファイル | 解像度 | ファイルサイズ | 状態 |
|---------|--------|-------------|------|
| `test-viewport.png` | 1920x1080 | 544KB | 正常 |
| `test-fullpage.png` | 1920x10538 | 617KB | 欠損（ほぼ空白） |

1920x10538 という大きな画像が 617KB しかないのは、大部分が空白であることの証拠。

---

## 根本原因の分析

### なぜ `clip` パラメータでは駄目なのか

CDPの `Page.captureScreenshot` に `clip` パラメータを指定すると、
指定した座標範囲の「ピクセルデータ」を切り出す。

しかし、**Chromium はビューポート外のコンテンツをレンダリングしない**。
ブラウザはパフォーマンス最適化のため、現在のビューポート付近のみを描画する。

したがって：
1. `clip` で `height: 10538` を指定しても
2. 実際にレンダリングされているのはビューポートの 1080px 分のみ
3. 残りの 9458px 分はピクセルデータが存在しないため空白になる

### Chrome DevTools の「フルサイズのスクリーンショットをキャプチャ」との違い

Chrome DevTools のフルページキャプチャは内部的に：
1. ビューポートをページ全体のサイズに一時的に拡大
2. Chromium に全コンテンツをレンダリングさせる
3. キャプチャ後にビューポートを元に戻す

この手順を経ているため、全コンテンツが描画された状態でキャプチャできる。
GLMの実装ではこの「ビューポート拡大」の手順が欠けていた。

---

## 修正内容

### 修正ファイル

`websnapshot/screenshot.py` の `take_screenshot()` 関数内、CDPキャプチャ部分

### 修正前のコード（GLMが実装したもの）

```python
# CDPを使用してスクリーンショット（ChromeのCapture full size screenshotと同じ方法）
cdp = await page.context.new_cdp_session(page)

if full_page:
    # フルページキャプチャ
    result = await cdp.send('Page.captureScreenshot', {
        'clip': {
            'x': 0,
            'y': 0,
            'width': width,
            'height': await page.evaluate('document.documentElement.scrollHeight'),
            'scale': 1
        }
    })
else:
    # ビューポートのみキャプチャ
    result = await cdp.send('Page.captureScreenshot', {
        'clip': {
            'x': 0,
            'y': 0,
            'width': width,
            'height': height,
            'scale': 1
        }
    })
```

**問題点:**
- `clip` パラメータはレンダリング済みの領域を切り出すだけ
- ビューポート外はレンダリングされていないため空白になる
- `format` パラメータが未指定

### 修正後のコード

```python
# CDPを使用してスクリーンショット（Playwrightのフォント待機を回避）
cdp = await page.context.new_cdp_session(page)

if full_page:
    # ページ全体のサイズを取得
    layout = await cdp.send('Page.getLayoutMetrics')
    content_width = int(layout['contentSize']['width'])
    content_height = int(layout['contentSize']['height'])

    # ビューポートをページ全体に拡大してコンテンツを全てレンダリングさせる
    await cdp.send('Emulation.setDeviceMetricsOverride', {
        'mobile': False,
        'width': content_width,
        'height': content_height,
        'deviceScaleFactor': 1,
    })
    await page.wait_for_timeout(500)

    # フルページスクリーンショット
    result = await cdp.send('Page.captureScreenshot', {
        'format': 'png',
        'captureBeyondViewport': True,
    })

    # ビューポートをリセット
    await cdp.send('Emulation.clearDeviceMetricsOverride')
else:
    # ビューポートのみキャプチャ
    result = await cdp.send('Page.captureScreenshot', {
        'format': 'png',
        'clip': {
            'x': 0,
            'y': 0,
            'width': width,
            'height': height,
            'scale': 1
        }
    })
```

### 修正のポイント（3段階）

#### 1. `Page.getLayoutMetrics` でページ全体のサイズを取得

```python
layout = await cdp.send('Page.getLayoutMetrics')
content_width = int(layout['contentSize']['width'])
content_height = int(layout['contentSize']['height'])
```

JavaScript の `scrollHeight` ではなく、CDP の `Page.getLayoutMetrics` を使用。
`contentSize` フィールドにページ全体の正確なサイズが含まれる。

#### 2. `Emulation.setDeviceMetricsOverride` でビューポートを拡大

```python
await cdp.send('Emulation.setDeviceMetricsOverride', {
    'mobile': False,
    'width': content_width,
    'height': content_height,
    'deviceScaleFactor': 1,
})
await page.wait_for_timeout(500)
```

ビューポートをページ全体のサイズに拡大することで、
Chromium にページ全体をレンダリングさせる。
500ms の待機でレンダリング完了を待つ。

#### 3. `captureBeyondViewport: True` でキャプチャ

```python
result = await cdp.send('Page.captureScreenshot', {
    'format': 'png',
    'captureBeyondViewport': True,
})
```

`clip` パラメータを廃止し、`captureBeyondViewport: True` を指定。
ビューポート全体（= ページ全体）をキャプチャする。

#### 4. キャプチャ後にビューポートをリセット

```python
await cdp.send('Emulation.clearDeviceMetricsOverride')
```

後続処理に影響しないよう、ビューポートを元に戻す。

---

## 修正の検証結果

### テスト: jin115.com（修正前に問題が発生していたサイト）

| 項目 | 修正前 | 修正後 |
|------|--------|--------|
| ファイル | `test-fullpage.png` | `test-fix-jin115.png` |
| 解像度 | 1920x10538 | 1920x10538 |
| ファイルサイズ | **617KB** | **5,967KB** |
| コンテンツ | 上部1画面分のみ、残り空白 | ページ全体が正しく描画 |
| タイムアウト | なし | なし |

ファイルサイズが約10倍に増加しており、全コンテンツが正しくレンダリングされていることを示す。

### テスト: example.com（正常系の確認）

| 項目 | 結果 |
|------|------|
| ファイル | `test-fix-example.png` |
| 解像度 | 1920x1080 |
| ファイルサイズ | 22KB |
| 状態 | 正常 |

### 目視確認

- **修正前:** 上部にコンテンツが見え、下部約85%が水色の背景色で空白
- **修正後:** ページ最上部から最下部（フッター）まで全ての記事・画像・ナビゲーションが描画

---

## 使用したCDP APIの技術解説

### `Page.getLayoutMetrics`
ページのレイアウトメトリクスを返す。`contentSize` にページ全体の幅と高さが含まれる。

### `Emulation.setDeviceMetricsOverride`
デバイスのメトリクス（画面サイズ等）を上書きする。
- `mobile`: モバイルエミュレーションの有無
- `width` / `height`: ビューポートサイズ
- `deviceScaleFactor`: デバイスピクセル比（1 = 等倍）

### `Page.captureScreenshot`
スクリーンショットをキャプチャする。
- `format`: 画像フォーマット（png / jpeg / webp）
- `captureBeyondViewport`: ビューポート外もキャプチャするか
- `clip`: 切り出し領域（今回のフルページでは未使用）

### `Emulation.clearDeviceMetricsOverride`
`setDeviceMetricsOverride` で上書きした設定をリセットする。

---

## 処理フローの比較

### 修正前のフロー

```
goto(url) → lazy load走査 → scrollTop(0)
  → CDP: captureScreenshot(clip={全ページ高さ})
  → 問題: ビューポート外はレンダリングされていない → 空白
```

### 修正後のフロー

```
goto(url) → lazy load走査 → scrollTop(0)
  → CDP: getLayoutMetrics → ページ全体のサイズ取得
  → CDP: setDeviceMetricsOverride → ビューポートをページ全体に拡大
  → 500ms待機 → Chromiumが全コンテンツをレンダリング
  → CDP: captureScreenshot(captureBeyondViewport=true) → 全ページキャプチャ
  → CDP: clearDeviceMetricsOverride → ビューポートリセット
```

---

## troubleディレクトリのファイル一覧

```
trouble/
├── REPORT.md              # GLMエージェントによる初期調査レポート
├── FIX_HISTORY.md         # 本ファイル（改修履歴の詳細）
├── test-viewport.png      # 修正前: ビューポートモード（正常）
├── test-fullpage.png      # 修正前: フルページモード（欠損あり、617KB）
├── test-font.png          # フォントレンダリングテスト
├── test-fix-example.png   # 修正後: example.com（正常）
└── test-fix-jin115.png    # 修正後: jin115.com フルページ（正常、5,967KB）
```
