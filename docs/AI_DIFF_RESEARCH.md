# AI認識による差分比較機能 技術調査レポート

**作成日**: 2026-02-13
**担当**: researcher (ai-diff-team)

---

## 1. 調査目的

ユーザー要望：「文字とか図形とか認識して判別、差分を表示することはできるか」

Webページのスクリーンショット等の画像に対して、AI/ML技術を用いて：
- テキスト（文字）の認識と差分検出
- 図形・UI要素の認識と差分検出
- 意味のある差分の表示

を実現するための技術調査を行う。

---

## 2. OCR技術調査

### 2.1 主要OCRライブラリ比較

| ライブラリ | 特徴 | メリット | デメリット |
|-----------|------|----------|------------|
| **Tesseract** | オープンソースOCRの標準 | - 歴史が長く安定している<br>- 個別文字認識に強い<br>- ラテン語系に最適 | - 中国語等の追加学習が必要<br>- 精度が他と比較して劣る場合あり |
| **EasyOCR** | PyTorchベースの多言語OCR | - 導入が容易<br>- 単語レベル認識に強い<br>- 多言語サポート | - 文字レベルの認識は苦手 |
| **PaddleOCR** | 百度開発の中国語向けOCR | - 高精度<br>- 中国語に最適化<br>- 誤認識が比較的少ない | - リソース消費が大きい<br>- モデルサイズが大きい |
| **LayoutParser** | ドキュメントレイアウト解析 | - 文書構造の認識に特化<br>- レイアウト理解が可能 | - 純粋なOCRエンジンではない<br>- 別途OCRが必要 |

### 2.2 2026年のトレンド

- **オープンソース vs 商用ソリューション**: Azure Document Intelligence、Amazon Textract等の商用サービスとの比較が活発
- **マルチ言語サポートの改善**: 特にアジア言語（日本語、中国語）の精度向上
- **現代AI/MLパイプラインとの統合**: ニューラルネットワークベースのアプローチが主流

---

## 3. オブジェクト検出・セグメンテーション技術調査

### 3.1 主要技術

| 技術 | 説明 | 最新状況 |
|------|------|----------|
| **YOLO** | リアルタイム物体検出 | YOLOv11までリリース（Ultralytics） |
| **Detectron2** | Facebook AI Researchの検出・セグメンテーションライブラリ | 次世代アルゴリズムをサポート |
| **SAM (Segment Anything Model)** | Metaのゼロショットセグメンテーション | **SAM 2、SAM 3が登場**（2025-2026） |
| **YOLO-SAM** | YOLO検出とSAMセグメンテーションの統合 | 2025年に論文発表 |

### 3.2 2026年の最新動向

- **SAM 2**: 動画対応の次世代セグメンテーションモデル
- **SAM 3**: コンセプトプロンプトによる検出・セグメンテーション・追跡を統合
- **YOLO-SAM統合**: リアルタイム検出と高精度セグメンテーションの組み合わせがトレンド
- **Ultralytics統合**: YOLOとSAMが同じフレームワークで利用可能に

---

## 4. 視覚的回帰テストツール調査

### 4.1 主要ツール比較

| ツール | コスト | AI技術 | 特徴 |
|--------|--------|--------|------|
| **Applitools** | 有料 | 高度なVisual AI | - 最も機能が豊富<br>- エンタープライズ向け<br>- 高度なAI分析 |
| **Percy (BrowserStack)** | 有料 | AI搭載 | - バランスの取れた機能セット<br>- スナップショットベース<br>- 幅広いフレームワーク対応 |
| **Playwright** | **無料** | 基本的なスナップショット比較 | - ネイティブ機能<br>- `pixelmatch`ライブラリ使用<br>- 2026年ではコスト重視で選択される傾向 |

### 4.2 Playwrightの視覚比較機能

- **基本機能**: `await expect(page).toHaveScreenshot()`
- **比較方式**: pixelmatchライブラリによるピクセルレベル比較
- **閾値設定**: 許容される差異を設定可能
- **AI拡張**: 2025年以降、AI駆動の視覚テスト拡張が登場

### 4.3 2026年のトレンド

- **コスト重視**: Playwrightのような無料ソリューションの採用増加
- **AI統合**: すべての主要プラットフォームがAIを活用したスマートな比較を実装
- **モバイル対応**: モバイル視覚回帰テストへの注力

---

## 5. Webページ要素認識：DOMベース vs 画像ベース

### 5.1 アプローチ比較

| アプローチ | メリット | デメリット |
|-----------|----------|------------|
| **DOMベース** | - コード構造へのアクセス<br>- 自動化に安定 | - React/Vue/Angular等の動的DOMに苦戦<br>- Shadow DOMの複雑さ |
| **画像ベース** | - レンダリングされた視覚出力を直接分析<br>- DOM複雑さに依存しない | - 計算コストが高い<br>- 意味の欠落可能性 |
| **ハイブリッド** | - 両方の利点を活用<br>- 2026年の主流アプローチ | - 実装複雑度 |

### 5.2 2026年のハイブリッドアプローチ

- **UI Vision**: DOM自動化と画像/視覚認識の組み合わせ
- **CoVA (Context-aware Visual Attention)**: 外観特徴とDOM木の構文構造の統合
- **モダンWebアプリ対策**: Shadow DOMやSPA対応のための二重アプローチ
- **アクセシビリティスナップショット**: Playwright等でのサポート拡大

---

## 6. 技術的実現可能性の評価

### 6.1 実現可能性

| 要件 | 実現可能性 | 推奨技術 |
|------|-----------|----------|
| **テキスト認識と差分** | ✅ 高い | PaddleOCR（日本語対応）、EasyOCR |
| **図形・UI要素検出** | ✅ 高い | SAM 2、YOLO-SAM統合 |
| **意味のある差分表示** | ⚠️ 中程度 | カスタム実装が必要 |

### 6.2 課題

1. **「意味のある差分」の定義が難しい**
   - ピクセル差異は検出できるが、重要度の自動判定は難しい
   - AIによる重要度評価モデルの構築が必要

2. **計算コスト**
   - 画像処理とOCRの組み合わせはリソース集約型
   - GPUアクセラレーションが望ましい

3. **日本語対応**
   - PaddleOCRが最適だが、モデルサイズが大きい

---

## 7. 推奨技術スタック

### 7.1 基本構成

```
Webスクリーンショット
    ↓
[前処理] 画像正規化
    ↓
[並列処理]
    ├─ [テキスト認識] PaddleOCR (日本語対応)
    ├─ [要素検出] SAM 2 + YOLO (オプション)
    └─ [ピクセル比較] pixelmatch (基礎差分)
    ↓
[差分統合] カスタム差分統合モジュール
    ↓
[結果表示] HTML/JSON出力 + 可視化UI
```

### 7.2 推奨ライブラリ

| 目的 | 推奨ライブラリ | 理由 |
|------|---------------|------|
| **OCR** | PaddleOCR | 日本語対応、高精度 |
| **オブジェクト検出** | SAM 2 (Ultralytics) | 最新技術、統合が容易 |
| **ピクセル比較** | pixelmatch | Playwrightと同じ実装 |
| **Webオートメーション** | Playwright | 無料、機能豊富 |
| **画像処理** | OpenCV, Pillow | 標準的な画像処理 |

### 7.3 実装オプション

#### オプションA：軽量版（最小構成）
- PaddleOCR（テキストのみ）
- pixelmatch（ピクセル差分）
- カスタム差分統合

#### オプションB：標準版（推奨）
- PaddleOCR
- SAM 2（図形・UI要素）
- pixelmatch
- Playwright（スクリーンショット取得）

#### オプションC：高度版（フル機能）
- 上記全て
- カスタムAIモデル（差分重要度評価）
- GPUアクセラレーション
- Web UIによる差分確認

---

## 8. 既存ツールとの差別化

| ツール | テキスト認識 | 要素認識 | 意味的差分 | コスト |
|--------|-------------|----------|-----------|--------|
| **Percy/Applitools** | ❌ | ❌ | △（AIによる） | 高 |
| **Playwright** | ❌ | ❌ | ❌ | 無料 |
| **本提案ツール** | ✅ | ✅ | △（開発次第） | 低（OSS） |

---

## 9. まとめと次のステップ

### 9.1 結論

**文字や図形を認識して差分を表示することは技術的に十分可能である。**

- テキスト認識: PaddleOCRで高精度に実現可能
- 図形・UI要素: SAM 2等の最新技術で実現可能
- 差分表示: pixelmatch等の既存技術と組み合わせて実現

### 9.2 推奨アプローチ

1. **フェーズ1**: テキスト認識とピクセル差分の基本実装
2. **フェーズ2**: SAM 2による要素検出の追加
3. **フェーズ3**: 意味的差分評価のAIモデル開発

### 9.3 次のステップ

1. プロトタイプの作成（PaddleOCR + pixelmatch）
2. 既存のwebsnapshotsプロジェクトとの統合検討
3. ユースケースの具体化

---

## 参考資料

### OCR技術
- [Best OCR Software in 2026 | PDF OCR Tool Comparison Guide](https://unstract.com/blog/best-pdf-ocr-software/)
- [Python文字识别库对比：Tesseract、EasyOCR与PaddleOCR实战指南](https://comate.baidu.com/zh/page/j8tzs42dul8)
- [PaddleOCR vs Tesseract Analysis](https://www.koncile.ai/en/ressources/paddleocr-analyse-avantages-alternatives-open-source)

### オブジェクト検出
- [SAM 2: Segment Anything Model 2 - Ultralytics YOLO Docs](https://docs.ultralytics.com/models/sam-2/)
- [YOLO-SAM: An End-to-End Framework](https://www.nature.com/articles/s41598-025-24576-6)
- [Detectron2 - GitHub](https://github.com/facebookresearch/detectron2)

### 視覚的回帰テスト
- [Top 7 Visual Testing Tools for 2026 - testRigor](https://testrigor.com/blog/visual-testing-tools/)
- [AI-Powered Visual Testing in Playwright: From Pixels to Perception](https://testrig.medium.com/ai-powered-visual-testing-in-playwright-from-pixels-to-perception-dd3ee49911d5)
- [Visual comparisons - Playwright](https://playwright.dev/docs/test-snapshots)

### Web要素認識
- [How to Implement Playwright Visual Testing - OneUptime](https://oneuptime.com/blog/post/2026-01-27-playwright-visual-testing/view)
- [AI-Driven Design Workflow: Playwright MCP Screenshots](https://egghead.io/ai-driven-design-workflow-playwright-mcp-screenshots-visual-diffs-and-cursor-rules~aulxx)
