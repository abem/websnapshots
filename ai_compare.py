#!/usr/bin/env python3
"""
AI-based Image Comparison Tool

AI認識による画像差分比較ツール。
OCR（PaddleOCR）によるテキスト比較と、ピクセル差分（pixelmatch）を統合して
意味のある差分を検出・表示する。
"""

import argparse
import asyncio
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse
from dataclasses import dataclass, asdict

try:
    from PIL import Image, ImageDraw, ImageChops, ImageStat
    from playwright.async_api import async_playwright, Error as PlaywrightError
except ImportError as e:
    missing_lib = str(e).split("'")[1] if "'" in str(e) else str(e)
    print(f"エラー: {missing_lib} がインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("  pip install Pillow>=10.0.0 playwright")
    sys.exit(1)


# =============================================================================
# データクラス
# =============================================================================

@dataclass
class TextRegion:
    """テキスト領域情報"""
    text: str
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float


@dataclass
class TextDiff:
    """テキスト差分情報"""
    text_before: str
    text_after: str
    bbox: Tuple[int, int, int, int]
    diff_type: str  # 'added', 'removed', 'modified'


@dataclass
class ObjectRegion:
    """オブジェクト領域情報"""
    label: str
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    object_type: str  # 'ui_element', 'shape', 'image', 'button', etc.


@dataclass
class ObjectDiff:
    """オブジェクト差分情報"""
    object_before: Optional[ObjectRegion]
    object_after: Optional[ObjectRegion]
    diff_type: str  # 'added', 'removed', 'modified', 'moved'


@dataclass
class ComparisonResult:
    """比較結果"""
    timestamp: str
    image1: str
    image2: str
    pixel_similarity: float
    text_similarity: float
    object_similarity: float
    text_regions_before: List[Dict]
    text_regions_after: List[Dict]
    text_diffs: List[Dict]
    object_regions_before: List[Dict]
    object_regions_after: List[Dict]
    object_diffs: List[Dict]
    pixel_diff_stats: Dict
    overall_diff_score: float


# =============================================================================
# ユーティリティ関数
# =============================================================================

def is_url(text: str) -> bool:
    """文字列がURLかどうかを判定する。"""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc]) and result.scheme in ('http', 'https')
    except Exception:
        return False


def generate_filename(prefix: str, ext: str = 'png') -> str:
    """タイムスタンプ付きのファイル名を生成する。"""
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    return f'{prefix}-{timestamp}.{ext}'


async def take_screenshot_from_url(
    url: str,
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    full_page: bool = True
) -> str:
    """URLからスクリーンショットを取得する。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(viewport={'width': width, 'height': height})
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.screenshot(path=output_path, full_page=full_page)
            return output_path
        finally:
            await browser.close()


def load_image(path_or_url: str, temp_dir: Optional[tempfile.TemporaryDirectory] = None) -> Image.Image:
    """画像を読み込む。URLの場合はスクリーンショットを取得。"""
    if is_url(path_or_url):
        print(f"スクリーンショットを取得中: {path_or_url}")
        if temp_dir is None:
            temp_dir = tempfile.TemporaryDirectory()
            temp_path = Path(temp_dir.name) / generate_filename('temp_screenshot')
        else:
            temp_path = Path(temp_dir.name) / generate_filename('temp_screenshot')

        try:
            asyncio.run(take_screenshot_from_url(path_or_url, str(temp_path)))
            return Image.open(temp_path)
        except Exception as e:
            raise IOError(f"URLからのスクリーンショット取得に失敗しました: {e}")

    path = Path(path_or_url)
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {path_or_url}")

    try:
        return Image.open(path)
    except Exception as e:
        raise IOError(f"画像の読み込みに失敗しました: {e}")


# =============================================================================
# PaddleOCR モジュール（モック実装 + 実装切り替え可能）
# =============================================================================

class OCRProvider:
    """OCRプロバイダーの基底クラス"""

    def extract_text(self, image: Image.Image) -> List[TextRegion]:
        """画像からテキストを抽出する。"""
        raise NotImplementedError


class PaddleOCRProvider(OCRProvider):
    """PaddleOCRを使用したOCRプロバイダー"""

    def __init__(self, lang: str = 'japanese'):
        self.lang = lang
        self._ocr = None
        self._initialized = False

    def _initialize(self):
        """PaddleOCRを初期化する。"""
        if self._initialized:
            return

        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                show_log=False
            )
            self._initialized = True
        except ImportError:
            print("警告: PaddleOCRがインストールされていません。")
            print("インストールコマンド: pip install paddleocr")
            self._ocr = None
            self._initialized = True

    def extract_text(self, image: Image.Image) -> List[TextRegion]:
        """画像からテキストを抽出する。"""
        self._initialize()

        if self._ocr is None:
            # モック/フォールバック: 空のリストを返す
            return []

        # PIL画像をopencv形式に変換
        import numpy as np
        img_array = np.array(image)

        # OCR実行
        result = self._ocr.ocr(img_array, cls=True)

        regions = []
        if result and result[0]:
            for line in result[0]:
                bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = line[1]  # (text, confidence)

                text = text_info[0]
                confidence = float(text_info[1])

                # バウンディングボックスを計算
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                x = int(min(x_coords))
                y = int(min(y_coords))
                width = int(max(x_coords) - x)
                height = int(max(y_coords) - y)

                regions.append(TextRegion(
                    text=text,
                    bbox=(x, y, width, height),
                    confidence=confidence
                ))

        return regions


class MockOCRProvider(OCRProvider):
    """モックOCRプロバイダー（開発・テスト用）"""

    def extract_text(self, image: Image.Image) -> List[TextRegion]:
        """モックテキスト抽出（画像サイズに基づいてダミーデータを生成）"""
        # 実際のOCRライブラリがない場合のフォールバック
        return []


def get_ocr_provider(use_paddleocr: bool = True, lang: str = 'japanese') -> OCRProvider:
    """OCRプロバイダーを取得する。"""
    if use_paddleocr:
        return PaddleOCRProvider(lang=lang)
    return MockOCRProvider()


# =============================================================================
# オブジェクト検出モジュール（SAM 2 / OpenCVベース）
# =============================================================================

class ObjectDetector:
    """オブジェクト検出器の基底クラス"""

    def detect_objects(self, image: Image.Image) -> List[ObjectRegion]:
        """画像からオブジェクトを検出する。"""
        raise NotImplementedError


class EdgeBasedDetector(ObjectDetector):
    """エッジ検出ベースのオブジェクト検出器（OpenCV使用）"""

    def __init__(self, min_area: int = 1000):
        self.min_area = min_area
        self._initialized = False

    def _initialize(self):
        """OpenCVを初期化する。"""
        if self._initialized:
            return

        try:
            import cv2
            self._cv2 = cv2
            self._initialized = True
        except ImportError:
            print("警告: OpenCVがインストールされていません。")
            print("インストールコマンド: pip install opencv-python")
            self._cv2 = None
            self._initialized = True

    def detect_objects(self, image: Image.Image) -> List[ObjectRegion]:
        """エッジ検出と輪郭抽出でオブジェクトを検出する。"""
        self._initialize()

        if self._cv2 is None:
            return []

        # PIL画像をOpenCV形式に変換
        import numpy as np
        img_array = np.array(image)
        img_gray = self._cv2.cvtColor(img_array, self._cv2.COLOR_RGB2GRAY)

        # エッジ検出（Canny）
        edges = self._cv2.Canny(img_gray, 50, 150)

        # 輪郭抽出
        contours, _ = self._cv2.findContours(
            edges,
            self._cv2.RETR_EXTERNAL,
            self._cv2.CHAIN_APPROX_SIMPLE
        )

        regions = []
        for contour in contours:
            area = self._cv2.contourArea(contour)
            if area >= self.min_area:
                # バウンディングボックスを取得
                x, y, w, h = self._cv2.boundingRect(contour)

                # アスペクト比からオブジェクトタイプを推定
                aspect_ratio = w / h if h > 0 else 0
                if aspect_ratio > 3 or aspect_ratio < 0.33:
                    obj_type = 'shape'  # 細長い形状
                elif area < 5000:
                    obj_type = 'button'  # 小さな領域
                else:
                    obj_type = 'ui_element'  # 一般的なUI要素

                regions.append(ObjectRegion(
                    label=f"object_{len(regions)}",
                    bbox=(x, y, w, h),
                    confidence=0.8,  # 固定値（実際の検出器は信頼度を返す）
                    object_type=obj_type
                ))

        return regions


class SAM2Detector(ObjectDetector):
    """SAM 2を使用したオブジェクト検出器"""

    def __init__(self, model_size: str = 'base'):
        self.model_size = model_size
        self._model = None
        self._initialized = False

    def _initialize(self):
        """SAM 2を初期化する。"""
        if self._initialized:
            return

        try:
            from ultralytics import SAM  # Ultralytics SAM 2
            model_map = {
                'tiny': 'sam2_t.pt',
                'small': 'sam2_s.pt',
                'base': 'sam2_b.pt',
                'large': 'sam2_l.pt'
            }
            model_path = model_map.get(self.model_size, 'sam2_b.pt')
            self._model = SAM(model_path)
            self._initialized = True
        except ImportError:
            print("警告: Ultralytics SAM 2がインストールされていません。")
            print("インストールコマンド: pip install ultralytics")
            self._model = None
            self._initialized = True
        except Exception as e:
            print(f"警告: SAM 2の初期化に失敗しました: {e}")
            self._model = None
            self._initialized = True

    def detect_objects(self, image: Image.Image) -> List[ObjectRegion]:
        """SAM 2でオブジェクトを検出する。"""
        self._initialize()

        if self._model is None:
            return []

        # PIL画像を保存してパスを渡す
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            image.save(tmp.name)
            tmp_path = tmp.name

        try:
            # SAM 2で推論
            results = self._model(tmp_path)

            regions = []
            if results and len(results) > 0:
                result = results[0]
                if hasattr(result, 'boxes') and result.boxes is not None:
                    for i, box in enumerate(result.boxes):
                        # バウンディングボックスを取得 [x1, y1, x2, y2]
                        xyxy = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, xyxy)
                        x, y, w, h = x1, y1, x2 - x1, y2 - y1

                        # 信頼度
                        confidence = float(box.conf[0]) if hasattr(box, 'conf') else 0.8

                        # クラス（如果有）
                        if hasattr(box, 'cls') and box.cls is not None:
                            cls_id = int(box.cls[0])
                            label = f"class_{cls_id}"
                        else:
                            label = f"object_{i}"

                        regions.append(ObjectRegion(
                            label=label,
                            bbox=(x, y, w, h),
                            confidence=confidence,
                            object_type='detected_object'
                        ))

            return regions

        finally:
            # 一時ファイルを削除
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class MockObjectDetector(ObjectDetector):
    """モックオブジェクト検出器（開発・テスト用）"""

    def detect_objects(self, image: Image.Image) -> List[ObjectRegion]:
        """モックオブジェクト検出（空のリストを返す）"""
        return []


def get_object_detector(
    use_sam2: bool = False,
    use_edge_detection: bool = True,
    sam2_model_size: str = 'base'
) -> ObjectDetector:
    """オブジェクト検出器を取得する。"""
    if use_sam2:
        return SAM2Detector(model_size=sam2_model_size)
    elif use_edge_detection:
        return EdgeBasedDetector()
    return MockObjectDetector()


# =============================================================================
# オブジェクト差分検出
# =============================================================================

def calculate_bbox_iou(bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
    """2つのバウンディングボックスのIoUを計算する。"""
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2

    # 交差領域
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    bbox1_area = w1 * h1
    bbox2_area = w2 * h2
    union_area = bbox1_area + bbox2_area - intersection_area

    return intersection_area / union_area if union_area > 0 else 0.0


def calculate_object_similarity(regions1: List[ObjectRegion], regions2: List[ObjectRegion]) -> float:
    """オブジェクトの類似度を計算する。"""
    if not regions1 and not regions2:
        return 1.0

    if not regions1 or not regions2:
        return 0.0

    # 各オブジェクトをIoUでマッチング
    matched_pairs = []
    used_indices2 = set()

    for i, obj1 in enumerate(regions1):
        best_iou = 0.0
        best_j = -1
        for j, obj2 in enumerate(regions2):
            if j in used_indices2:
                continue
            iou = calculate_bbox_iou(obj1.bbox, obj2.bbox)
            if iou > best_iou:
                best_iou = iou
                best_j = j

        if best_j >= 0 and best_iou > 0.3:  # IoU閾値
            matched_pairs.append((i, best_j, best_iou))
            used_indices2.add(best_j)

    # マッチしたオブジェクトの平均IoUを類似度とする
    if not matched_pairs:
        return 0.0

    avg_iou = sum(iou for _, _, iou in matched_pairs) / len(matched_pairs)

    # 未マッチのオブジェクトを考慮してスコアを調整
    total_objects = len(regions1) + len(regions2)
    matched_count = len(matched_pairs) * 2
    coverage = matched_count / total_objects if total_objects > 0 else 0

    return avg_iou * coverage


def detect_object_diffs(
    regions1: List[ObjectRegion],
    regions2: List[ObjectRegion]
) -> List[ObjectDiff]:
    """オブジェクト差分を検出する。"""
    diffs = []

    # IoUでマッチング
    matched1 = set()
    matched2 = set()

    for i, obj1 in enumerate(regions1):
        best_iou = 0.0
        best_j = -1
        for j, obj2 in enumerate(regions2):
            iou = calculate_bbox_iou(obj1.bbox, obj2.bbox)
            if iou > best_iou:
                best_iou = iou
                best_j = j

        if best_j >= 0 and best_iou > 0.5:  # 高いIoU閾値で同一と判定
            matched1.add(i)
            matched2.add(best_j)

            # 位置が大きく変わっている場合は「移動」と判定
            x1, y1, w1, h1 = obj1.bbox
            x2, y2, w2, h2 = regions2[best_j].bbox
            center_dist = ((x1 + w1/2) - (x2 + w2/2))**2 + ((y1 + h1/2) - (y2 + h2/2))**2
            if center_dist > (w1 * 0.5)**2 + (h1 * 0.5)**2:  # 中心がサイズの半分以上移動
                diffs.append(ObjectDiff(
                    object_before=obj1,
                    object_after=regions2[best_j],
                    diff_type='moved'
                ))

    # 削除されたオブジェクト
    for i, obj1 in enumerate(regions1):
        if i not in matched1:
            diffs.append(ObjectDiff(
                object_before=obj1,
                object_after=None,
                diff_type='removed'
            ))

    # 追加されたオブジェクト
    for j, obj2 in enumerate(regions2):
        if j not in matched2:
            diffs.append(ObjectDiff(
                object_before=None,
                object_after=obj2,
                diff_type='added'
            ))

    return diffs


# =============================================================================
# テキスト差分検出
# =============================================================================

def normalize_text(text: str) -> str:
    """テキストを正規化する（空白や改行の統一）。"""
    return re.sub(r'\s+', ' ', text.strip())


def calculate_text_similarity(regions1: List[TextRegion], regions2: List[TextRegion]) -> float:
    """テキストの類似度を計算する。"""
    texts1 = set(normalize_text(r.text) for r in regions1)
    texts2 = set(normalize_text(r.text) for r in regions2)

    if not texts1 and not texts2:
        return 1.0

    if not texts1 or not texts2:
        return 0.0

    # Jaccard類似度
    intersection = len(texts1 & texts2)
    union = len(texts1 | texts2)

    return intersection / union if union > 0 else 0.0


def detect_text_diffs(
    regions1: List[TextRegion],
    regions2: List[TextRegion]
) -> List[TextDiff]:
    """テキスト差分を検出する。"""
    diffs = []

    texts1 = {normalize_text(r.text): r for r in regions1}
    texts2 = {normalize_text(r.text): r for r in regions2}

    # 削除されたテキスト
    for text, region in texts1.items():
        if text not in texts2:
            diffs.append(TextDiff(
                text_before=text,
                text_after="",
                bbox=region.bbox,
                diff_type='removed'
            ))

    # 追加されたテキスト
    for text, region in texts2.items():
        if text not in texts1:
            diffs.append(TextDiff(
                text_before="",
                text_after=text,
                bbox=region.bbox,
                diff_type='added'
            ))

    return diffs


# =============================================================================
# ピクセル差分検出（pixelmatch スタイル）
# =============================================================================

def calculate_pixel_diff(img1: Image.Image, img2: Image.Image) -> Tuple[float, Dict]:
    """ピクセル差分を計算する（pixelmatch スタイル）。"""
    # 同じサイズにリサイズ
    if img1.size != img2.size:
        target_width = max(img1.width, img2.width)
        target_height = max(img1.height, img2.height)
        img1 = img1.resize((target_width, target_height), Image.Resampling.LANCZOS)
        img2 = img2.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # 差分を計算
    diff = ImageChops.difference(img1, img2).convert('L')

    # 統計情報
    stat = ImageStat.Stat(diff)
    hist = diff.histogram()

    total_pixels = diff.width * diff.height
    different_pixels = sum(hist[10:])  # 閾値: 10
    diff_ratio = (different_pixels / total_pixels) * 100 if total_pixels > 0 else 0

    similarity = 1.0 - (diff_ratio / 100.0)

    stats = {
        'total_pixels': total_pixels,
        'different_pixels': different_pixels,
        'diff_ratio': diff_ratio,
        'mean_diff': float(stat.mean[0]) if stat.mean else 0.0,
        'max_diff': int(stat.extrema[0][1]) if stat.extrema else 0
    }

    return similarity, stats


# =============================================================================
# 差分統合・スコアリング
# =============================================================================

def calculate_overall_diff_score(
    pixel_similarity: float,
    text_similarity: float,
    object_similarity: float = 1.0,
    pixel_weight: float = 0.3,
    text_weight: float = 0.4,
    object_weight: float = 0.3
) -> float:
    """全体の差分スコアを計算する。"""
    # スコアは0（完全に異なる）〜1（同一）
    return (
        pixel_similarity * pixel_weight +
        text_similarity * text_weight +
        object_similarity * object_weight
    )


def categorize_diff_score(score: float) -> str:
    """差分スコアをカテゴリ分類する。"""
    if score >= 0.95:
        return "ほぼ同一"
    elif score >= 0.85:
        return "わずかな差分"
    elif score >= 0.70:
        return "中程度の差分"
    elif score >= 0.50:
        return "大きな差分"
    else:
        return "完全に異なる"


# =============================================================================
# 差分可視化
# =============================================================================

def create_diff_visualization(
    img1: Image.Image,
    img2: Image.Image,
    text_diffs: List[TextDiff],
    object_diffs: List[ObjectDiff],
    output_path: str
) -> None:
    """差分可視化画像を作成する。"""
    # サイド・バイ・サイド
    if img1.size != img2.size:
        target_width = max(img1.width, img2.width)
        target_height = max(img1.height, img2.height)
        img1 = img1.resize((target_width, target_height), Image.Resampling.LANCZOS)
        img2 = img2.resize((target_width, target_height), Image.Resampling.LANCZOS)

    width, height = img1.size
    side_by_side = Image.new('RGB', (width * 2, height))
    side_by_side.paste(img1, (0, 0))
    side_by_side.paste(img2, (width, 0))

    draw = ImageDraw.Draw(side_by_side)

    # ピクセル差分を強調
    diff = ImageChops.difference(img1, img2).convert('L')
    threshold = 30

    for y in range(0, height, 10):
        for x in range(0, width, 10):
            # ピクセル差分をチェック
            has_diff = False
            for by in range(y, min(y + 10, height)):
                for bx in range(x, min(x + 10, width)):
                    if diff.getpixel((bx, by)) > threshold:
                        has_diff = True
                        break
                if has_diff:
                    break

            if has_diff:
                # 赤い枠を描画
                draw.rectangle([x, y, x + 10, y + 10], outline='red', width=1)
                draw.rectangle([width + x, y, width + x + 10, y + 10], outline='red', width=1)

    # オブジェクト差分をオーバーレイ
    for obj_diff in object_diffs:
        if obj_diff.object_before:
            x, y, w, h = obj_diff.object_before.bbox
            if obj_diff.diff_type == 'removed':
                color = 'magenta'  # 削除はマゼンタ
                draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
            elif obj_diff.diff_type == 'moved':
                color = 'orange'  # 移動はオレンジ
                draw.rectangle([x, y, x + w, y + h], outline=color, width=2)

        if obj_diff.object_after:
            x, y, w, h = obj_diff.object_after.bbox
            if obj_diff.diff_type == 'added':
                color = 'cyan'  # 追加はシアン
                draw.rectangle([width + x, y, width + x + w, y + h], outline=color, width=2)
            elif obj_diff.diff_type == 'moved':
                color = 'orange'  # 移動はオレンジ
                draw.rectangle([width + x, y, width + x + w, y + h], outline=color, width=2)

    # テキスト差分をオーバーレイ（最上位に表示）
    for text_diff in text_diffs:
        x, y, w, h = text_diff.bbox

        if text_diff.diff_type == 'added':
            color = 'green'  # 追加は緑
        elif text_diff.diff_type == 'removed':
            color = 'blue'   # 削除は青
        else:
            color = 'yellow' # 修正は黄色

        # 左側（元画像）
        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
        # 右側（比較画像）
        draw.rectangle([width + x, y, width + x + w, y + h], outline=color, width=3)

    side_by_side.save(output_path)


# =============================================================================
# メイン比較関数
# =============================================================================

def compare_images_with_ai(
    image1_path: str,
    image2_path: str,
    use_paddleocr: bool = True,
    ocr_lang: str = 'japanese',
    use_object_detection: bool = True,
    use_sam2: bool = False
) -> ComparisonResult:
    """AI認識を使用して画像を比較する。"""

    temp_dir = tempfile.TemporaryDirectory()

    try:
        # 画像を読み込み
        img1 = load_image(image1_path, temp_dir)
        img2 = load_image(image2_path, temp_dir)

        # OCRプロバイダーを取得
        ocr = get_ocr_provider(use_paddleocr=use_paddleocr, lang=ocr_lang)

        # テキスト抽出
        print(f"テキスト抽出中: {image1_path}")
        regions1 = ocr.extract_text(img1)

        print(f"テキスト抽出中: {image2_path}")
        regions2 = ocr.extract_text(img2)

        # テキスト差分検出
        text_diffs = detect_text_diffs(regions1, regions2)
        text_similarity = calculate_text_similarity(regions1, regions2)

        # オブジェクト検出
        object_regions1 = []
        object_regions2 = []
        object_diffs = []
        object_similarity = 1.0

        if use_object_detection:
            obj_detector = get_object_detector(use_sam2=use_sam2)

            print(f"オブジェクト検出中: {image1_path}")
            object_regions1 = obj_detector.detect_objects(img1)

            print(f"オブジェクト検出中: {image2_path}")
            object_regions2 = obj_detector.detect_objects(img2)

            # オブジェクト差分検出
            object_diffs = detect_object_diffs(object_regions1, object_regions2)
            object_similarity = calculate_object_similarity(object_regions1, object_regions2)

        # ピクセル差分
        pixel_similarity, pixel_stats = calculate_pixel_diff(img1, img2)

        # 全体スコア
        overall_score = calculate_overall_diff_score(
            pixel_similarity,
            text_similarity,
            object_similarity
        )

        # 結果を構築
        result = ComparisonResult(
            timestamp=datetime.now().isoformat(),
            image1=image1_path,
            image2=image2_path,
            pixel_similarity=pixel_similarity,
            text_similarity=text_similarity,
            object_similarity=object_similarity,
            text_regions_before=[{
                'text': r.text,
                'bbox': r.bbox,
                'confidence': r.confidence
            } for r in regions1],
            text_regions_after=[{
                'text': r.text,
                'bbox': r.bbox,
                'confidence': r.confidence
            } for r in regions2],
            text_diffs=[{
                'text_before': d.text_before,
                'text_after': d.text_after,
                'bbox': d.bbox,
                'diff_type': d.diff_type
            } for d in text_diffs],
            object_regions_before=[{
                'label': o.label,
                'bbox': o.bbox,
                'confidence': o.confidence,
                'object_type': o.object_type
            } for o in object_regions1],
            object_regions_after=[{
                'label': o.label,
                'bbox': o.bbox,
                'confidence': o.confidence,
                'object_type': o.object_type
            } for o in object_regions2],
            object_diffs=[{
                'object_before': {
                    'label': d.object_before.label,
                    'bbox': d.object_before.bbox,
                    'confidence': d.object_before.confidence,
                    'object_type': d.object_before.object_type
                } if d.object_before else None,
                'object_after': {
                    'label': d.object_after.label,
                    'bbox': d.object_after.bbox,
                    'confidence': d.object_after.confidence,
                    'object_type': d.object_after.object_type
                } if d.object_after else None,
                'diff_type': d.diff_type
            } for d in object_diffs],
            pixel_diff_stats=pixel_stats,
            overall_diff_score=overall_score
        )

        return result

    finally:
        temp_dir.cleanup()


# =============================================================================
# レポート生成
# =============================================================================

def generate_ai_comparison_report(result: ComparisonResult, diff_image_path: Optional[str] = None) -> str:
    """AI比較レポートを生成する。"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    category = categorize_diff_score(result.overall_diff_score)

    lines = [
        "# AI画像比較レポート",
        "",
        f"生成日時: {timestamp}",
        "",
        "## 比較対象",
        "",
        f"- **画像1**: `{result.image1}`",
        f"- **画像2**: `{result.image2}`",
        "",
        "## 類似度スコア",
        "",
        f"- **ピクセル類似度**: {result.pixel_similarity:.4f}",
        f"- **テキスト類似度**: {result.text_similarity:.4f}",
        f"- **オブジェクト類似度**: {result.object_similarity:.4f}",
        f"- **総合スコア**: {result.overall_diff_score:.4f}",
        f"- **判定**: {category}",
        "",
        "## ピクセル差分詳細",
        "",
        f"- **差分ピクセル数**: {result.pixel_diff_stats['different_pixels']:,} / {result.pixel_diff_stats['total_pixels']:,}",
        f"- **差分比率**: {result.pixel_diff_stats['diff_ratio']:.2f}%",
        f"- **平均差分値**: {result.pixel_diff_stats['mean_diff']:.1f}",
        f"- **最大差分値**: {result.pixel_diff_stats['max_diff']}",
        "",
        "## オブジェクト検出結果",
        "",
        f"### 画像1のオブジェクト ({len(result.object_regions_before)}件)",
        ""
    ]

    for i, obj in enumerate(result.object_regions_before[:20]):
        lines.append(f"{i+1}. `{obj['label']}` ({obj['object_type']}) - 位置: {obj['bbox']} (信頼度: {obj['confidence']:.2f})")

    if len(result.object_regions_before) > 20:
        lines.append(f"... 他 {len(result.object_regions_before) - 20} 件")

    lines.extend([
        "",
        f"### 画像2のオブジェクト ({len(result.object_regions_after)}件)",
        ""
    ])

    for i, obj in enumerate(result.object_regions_after[:20]):
        lines.append(f"{i+1}. `{obj['label']}` ({obj['object_type']}) - 位置: {obj['bbox']} (信頼度: {obj['confidence']:.2f})")

    if len(result.object_regions_after) > 20:
        lines.append(f"... 他 {len(result.object_regions_after) - 20} 件")

    # オブジェクト差分
    lines.extend([
        "",
        "## オブジェクト差分",
        ""
    ])

    if result.object_diffs:
        diff_type_map = {'added': '追加', 'removed': '削除', 'moved': '移動', 'modified': '変更'}
        for i, diff in enumerate(result.object_diffs):
            lines.append(f"### 差分 {i+1}: {diff_type_map.get(diff['diff_type'], diff['diff_type'])}")
            if diff['object_before']:
                obj = diff['object_before']
                lines.append(f"- 変更前: `{obj['label']}` ({obj['object_type']}) - 位置: {obj['bbox']}")
            if diff['object_after']:
                obj = diff['object_after']
                lines.append(f"- 変更後: `{obj['label']}` ({obj['object_type']}) - 位置: {obj['bbox']}")
            lines.append("")
    else:
        lines.extend([
            "オブジェクト差分は検出されませんでした。",
            ""
        ])

    # テキスト抽出結果
    lines.extend([
        "## テキスト抽出結果",
        "",
        f"### 画像1のテキスト ({len(result.text_regions_before)}件)",
        ""
    ])

    for i, region in enumerate(result.text_regions_before[:20]):
        lines.append(f"{i+1}. `{region['text']}` (信頼度: {region['confidence']:.2f})")

    if len(result.text_regions_before) > 20:
        lines.append(f"... 他 {len(result.text_regions_before) - 20} 件")

    lines.extend([
        "",
        f"### 画像2のテキスト ({len(result.text_regions_after)}件)",
        ""
    ])

    for i, region in enumerate(result.text_regions_after[:20]):
        lines.append(f"{i+1}. `{region['text']}` (信頼度: {region['confidence']:.2f})")

    if len(result.text_regions_after) > 20:
        lines.append(f"... 他 {len(result.text_regions_after) - 20} 件")

    # テキスト差分
    lines.extend([
        "",
        "## テキスト差分",
        ""
    ])

    if result.text_diffs:
        for i, diff in enumerate(result.text_diffs):
            diff_type_map = {'added': '追加', 'removed': '削除', 'modified': '変更'}
            lines.append(f"### 差分 {i+1}: {diff_type_map.get(diff['diff_type'], diff['diff_type'])}")
            lines.append(f"- 位置: {diff['bbox']}")
            if diff['text_before']:
                lines.append(f"- 変更前: `{diff['text_before']}`")
            if diff['text_after']:
                lines.append(f"- 変更後: `{diff['text_after']}`")
            lines.append("")
    else:
        lines.extend([
            "テキスト差分は検出されませんでした。",
            ""
        ])

    if diff_image_path:
        lines.extend([
            "## 差分可視化",
            "",
            f"![差分画像]({diff_image_path})",
            ""
        ])

    return '\n'.join(lines)


# =============================================================================
# コマンドラインインターフェース
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数を解析する。"""
    parser = argparse.ArgumentParser(
        description='AI認識による画像差分比較ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用例:
  python ai_compare.py image1.png image2.png
  python ai_compare.py https://example.com https://example.org
  python ai_compare.py image1.png image2.png --output report.md
  python ai_compare.py image1.png image2.png --no-ocr
  python ai_compare.py image1.png image2.png --lang english
        '''
    )

    parser.add_argument(
        'image1',
        help='比較する1つ目の画像（ファイルパスまたはURL）'
    )

    parser.add_argument(
        'image2',
        help='比較する2つ目の画像（ファイルパスまたはURL）'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='出力Markdownファイルパス'
    )

    parser.add_argument(
        '--diff-image', '-d',
        type=str,
        default=None,
        help='差分画像の出力パス'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='JSON形式でも出力'
    )

    parser.add_argument(
        '--no-ocr',
        action='store_true',
        help='OCRを使用しない（ピクセル比較のみ）'
    )

    parser.add_argument(
        '--lang', '-l',
        type=str,
        choices=['japanese', 'english', 'chinese', 'korean'],
        default='japanese',
        help='OCR言語（デフォルト: japanese）'
    )

    parser.add_argument(
        '--no-visualization',
        action='store_true',
        help='差分可視化画像を生成しない'
    )

    parser.add_argument(
        '--no-object-detection',
        action='store_true',
        help='オブジェクト検出を使用しない'
    )

    parser.add_argument(
        '--use-sam2',
        action='store_true',
        help='SAM 2を使用してオブジェクト検出（要ultralytics）'
    )

    return parser.parse_args()


def main() -> int:
    """メイン関数。"""
    args = parse_arguments()

    # 出力ファイル名の決定
    if args.output is None:
        output_path = generate_filename('ai_comparison_report', 'md')
    else:
        output_path = args.output

    diff_image_path = args.diff_image
    if diff_image_path is None and not args.no_visualization:
        diff_image_path = generate_filename('ai_diff', 'png')
    elif args.no_visualization:
        diff_image_path = None

    try:
        print(f"AI画像比較を開始: {args.image1} vs {args.image2}")

        # 比較実行
        result = compare_images_with_ai(
            args.image1,
            args.image2,
            use_paddleocr=not args.no_ocr,
            ocr_lang=args.lang,
            use_object_detection=not args.no_object_detection,
            use_sam2=args.use_sam2
        )

        # 差分可視化
        if diff_image_path:
            print(f"差分可視化画像を生成中: {diff_image_path}")
            temp_dir = tempfile.TemporaryDirectory()
            try:
                img1 = load_image(args.image1, temp_dir)
                img2 = load_image(args.image2, temp_dir)

                # TextDiffオブジェクトを復元
                text_diffs = [
                    TextDiff(
                        text_before=d['text_before'],
                        text_after=d['text_after'],
                        bbox=tuple(d['bbox']),
                        diff_type=d['diff_type']
                    )
                    for d in result.text_diffs
                ]

                # ObjectDiffオブジェクトを復元
                object_diffs = []
                for d in result.object_diffs:
                    obj_before = None
                    obj_after = None
                    if d['object_before']:
                        obj_before = ObjectRegion(
                            label=d['object_before']['label'],
                            bbox=tuple(d['object_before']['bbox']),
                            confidence=d['object_before']['confidence'],
                            object_type=d['object_before']['object_type']
                        )
                    if d['object_after']:
                        obj_after = ObjectRegion(
                            label=d['object_after']['label'],
                            bbox=tuple(d['object_after']['bbox']),
                            confidence=d['object_after']['confidence'],
                            object_type=d['object_after']['object_type']
                        )
                    object_diffs.append(ObjectDiff(
                        object_before=obj_before,
                        object_after=obj_after,
                        diff_type=d['diff_type']
                    ))

                create_diff_visualization(img1, img2, text_diffs, object_diffs, diff_image_path)
            finally:
                temp_dir.cleanup()

        # レポート生成
        print(f"レポートを生成中: {output_path}")
        report = generate_ai_comparison_report(result, diff_image_path)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        # JSON出力
        if args.json:
            json_path = output_path.replace('.md', '.json') if output_path.endswith('.md') else output_path + '.json'
            print(f"JSONデータを生成中: {json_path}")

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, indent=2, ensure_ascii=False)

            print(f"JSONデータを保存しました: {json_path}")

        # 結果表示
        category = categorize_diff_score(result.overall_diff_score)
        print(f"\n=== 比較結果 ===")
        print(f"総合スコア: {result.overall_diff_score:.4f} ({category})")
        print(f"ピクセル類似度: {result.pixel_similarity:.4f}")
        print(f"テキスト類似度: {result.text_similarity:.4f}")
        print(f"オブジェクト類似度: {result.object_similarity:.4f}")
        print(f"テキスト差分数: {len(result.text_diffs)}")
        print(f"オブジェクト差分数: {len(result.object_diffs)}")

        if diff_image_path:
            print(f"\n差分画像を保存しました: {diff_image_path}")
        print(f"レポートを保存しました: {output_path}")

        return 0

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"エラー: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
