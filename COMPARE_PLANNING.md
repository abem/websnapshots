# Web Snapshot Compare Tool - 企画・要件定義

## プロジェクト概要

2つの画像（URLまたはファイル）を比較し、差分を可視化するCLIツールを開発する。比較結果をMarkdown形式で出力する。

## 要件

### 基本要件
- 2つの画像（ファイルパスまたはURL）を比較する
- 差分を可視化した画像を生成する
- 比較結果をMarkdown文書として出力する

### 実行環境
- Python 3.10+
- 既存のweb_snapshot.pyとの連携を考慮

## 技術選定

### 画像比較ライブラリの比較

| ライブラリ | メンテナンス | 速度 | 精度 | 導入の容易さ | 推奨度 |
|-----------|--------------|------|------|-------------|--------|
| **Pillow (PIL)** | Active | 高速 | 中等 | 簡単 | **推奨** |
| **OpenCV (cv2)** | Active | 高速 | 高い | やや複雑 | ○ |
| **imagehash** | Active | 高速 | 高い | 簡単 | **推奨** |
| **skimage** | Active | 中等 | 高い | やや複雑 | △ |

### 採用技術: Pillow + imagehash

**選定理由:**

1. **Pillow（PIL）**:
   - Python標準の画像処理ライブラリ
   - 軽量で導入が容易
   - 基本的な画像操作（リサイズ、比較）に十分
   - 既存のweb_snapshot.pyとの親和性が高い

2. **imagehash**:
   - 知覚画像ハッシュ（Perceptual Hash）による比較が可能
   - 類似度スコアを数値化できる
   - 高速かつメモリ効率が良い
   - 以下のハッシュアルゴリズムをサポート:
     - aHash: Average Hash（平均ハッシュ）
     - pHash: Perceptual Hash（知覚ハッシュ）
     - dHash: Difference Hash（差分ハッシュ）
     - wHash: Wavelet Hash（ウェーブレットハッシュ）
     - WHash: Haar Wavelet Hash

3. **比較検討したが採用を見送った技術**:
   - **OpenCV**: 高機能だがライブラリサイズが大きく、導入が複雑
   - **skimage**: 科学計算用途向けでオーバースペック

### インストール予定パッケージ

```bash
pip install Pillow>=10.0.0 imagehash>=4.3.0
```

## 仕様策定

### コマンドラインインターフェース

```bash
# 基本使用法
python compare_images.py <image1> <image2>

# URLから直接比較（web_snapshot.pyとの連携）
python compare_images.py --url1 https://example.com --url2 https://example.org

# 出力ファイル名を指定
python compare_images.py image1.png image2.png --output comparison_report.md

# 差分画像も出力
python compare_images.py image1.png image2.png --diff-image diff.png

# ハッシュアルゴリズムを指定
python compare_images.py image1.png image2.png --hash-algorithm phash
```

### コマンドラインオプション

| オプション | 省略形 | 説明 | デフォルト値 |
|-----------|--------|------|--------------|
| `image1` | - | 比較する1つ目の画像（ファイルパス） | - |
| `image2` | - | 比較する2つ目の画像（ファイルパス） | - |
| `--url1` | - | 1つ目の画像のURL（スクリーンショットを取得） | - |
| `--url2` | - | 2つ目の画像のURL（スクリーンショットを取得） | - |
| `--output` | `-o` | 出力Markdownファイルパス | `comparison_report-{timestamp}.md` |
| `--diff-image` | `-d` | 差分画像の出力パス | `diff-{timestamp}.png` |
| `--hash-algorithm` | - | ハッシュアルゴリズム (ahash/phash/dhash/whash) | `phash` |
| `--threshold` | - | 差分と判定する閾値（0-1） | `0.95` |
| `--no-diff` | - | 差分画像を生成しない | false |
| `--help` | `-h` | ヘルプを表示 | - |

### 差分検出方法

#### 1. 画像サイズの事前チェック
- 2つの画像のサイズが異なる場合は警告を表示
- 必要に応じてリサイズして比較

#### 2. 知覚画像ハッシュ（Perceptual Hash）による比較
- imagehashを使用して画像のハッシュ値を計算
- ハンming距離により類似度を算出
- 類似度スコア: 0（完全に異なる）〜 1（同一）

#### 3. ピクセル単位の差分検出
- Pillowを使用してピクセル単位の差分を抽出
- 差分画像には以下の色付け:
  - 赤: 1つ目の画像にのみ存在する領域
  - 緑: 2つ目の画像にのみ存在する領域
  - 黄: 両方の画像で異なるピクセル

### 出力文書形式（Markdown）

```markdown
# 画像比較レポート

生成日時: 2026-02-13 15:30:45

## 比較対象

- **画像1**: `image1.png` (1920x1080)
- **画像2**: `image2.png` (1920x1080)

## 類似度スコア

| ハッシュアルゴリズム | 類似度 | ハミング距離 |
|---------------------|--------|-------------|
| aHash | 0.9876 | 4 |
| pHash | 0.9512 | 16 |
| dHash | 0.9234 | 24 |

**総合判定**: 類似しています（閾値: 0.95）

## 差分画像

![差分画像](diff-20260213T153045.png)

## 詳細統計

- **異なるピクセル数**: 1,234 / 2,073,600 (0.06%)
- **最大差分値**: 127
- **平均差分値**: 12.3
```

## 実装方針

### フェーズ1: 基本実装
1. Pillowとimagehashのセットアップ
2. 2つの画像ファイルを読み込み、比較
3. 類似度スコアの算出

### フェーズ2: 差分可視化
1. ピクセル単位の差分検出
2. 差分画像の生成
3. 色分けによる差分の強調

### フェーズ3: Markdown出力
1. 比較結果の構造化
2. Markdown形式での出力
3. 統計情報の計算と表示

### フェーズ4: URL対応
1. web_snapshot.pyとの連携
2. URLからスクリーンショットを取得して比較

## ファイル構成

```
web-snapshot/
├── requirements.txt       # 既存（画像比較ライブラリを追加）
├── web_snapshot.py        # 既存（スクリーンショット取得）
├── compare_images.py      # 新規（画像比較メイン）
├── COMPARE_PLANNING.md    # 新規（本ドキュメント）
└── comparisons/           # 新規（出力ディレクトリ）
    ├── reports/           # Markdownレポート
    └── diffs/             # 差分画像
```

## 依存関係の更新

`requirements.txt` に以下を追加:

```txt
# 画像比較用ライブラリ
Pillow>=10.0.0
imagehash>=4.3.0
```

## 開発スケジュール

1. **企画・要件定義**（本フェーズ）✓
2. **基本実装**: 画像読み込みとハッシュ比較
3. **差分可視化**: 差分画像の生成
4. **Markdown出力**: レポートの生成
5. **URL対応**: web_snapshot.pyとの連携
6. **テスト**: 各種画像での動作確認

## 将来の拡張機能

- 複数画像の一括比較
- ビデオフレームの比較
- CSSセレクタによる特定要素の比較
- JSON形式での結果出力
- CI/CDツールとの連携
