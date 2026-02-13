#!/usr/bin/env python3
"""
Web Snapshot Compare Tool

2つの画像（URLまたはファイル）を比較し、差分を可視化するCLIツール。
"""

import argparse
import asyncio
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

try:
    from PIL import Image, ImageDraw, ImageChops, ImageStat
    import imagehash
    from playwright.async_api import async_playwright, Error as PlaywrightError
except ImportError as e:
    missing_lib = str(e).split("'")[1] if "'" in str(e) else str(e)
    print(f"エラー: {missing_lib} がインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("  pip install Pillow>=10.0.0 imagehash>=4.3.0 playwright")
    sys.exit(1)


def is_url(text: str) -> bool:
    """
    文字列がURLかどうかを判定する。

    Args:
        text: 判定する文字列

    Returns:
        bool: URLの場合はTrue
    """
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc]) and result.scheme in ('http', 'https')
    except Exception:
        return False


async def take_screenshot_from_url(
    url: str,
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    full_page: bool = True
) -> str:
    """
    URLからスクリーンショットを取得する。

    Args:
        url: スクリーンショットを取得するURL
        output_path: 出力ファイルパス
        width: ビューポートの幅（ピクセル）
        height: ビューポートの高さ（ピクセル）
        full_page: フルページスクリーンショットを取得するかどうか

    Returns:
        str: 保存されたファイルのパス

    Raises:
        PlaywrightError: ブラウザ操作エラー
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(viewport={'width': width, 'height': height})
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.screenshot(path=output_path, full_page=full_page)
            return output_path
        finally:
            await browser.close()


def generate_filename(prefix: str, ext: str = 'png') -> str:
    """
    タイムスタンプ付きのファイル名を生成する。

    Args:
        prefix: ファイル名のプレフィックス
        ext: 拡張子（デフォルト: png）

    Returns:
        str: {prefix}-{timestamp}.{ext} 形式のファイル名
    """
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    return f'{prefix}-{timestamp}.{ext}'


def load_image(path_or_url: str, temp_dir: Optional[tempfile.TemporaryDirectory] = None) -> Image.Image:
    """
    画像を読み込む。
    URLの場合はスクリーンショットを取得して比較する。

    Args:
        path_or_url: 画像のファイルパスまたはURL
        temp_dir: 一時ディレクトリ（URLの場合に使用）

    Returns:
        Image.Image: 読み込んだ画像

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        IOError: 画像の読み込みに失敗した場合
    """
    # URLの場合はスクリーンショットを取得
    if is_url(path_or_url):
        print(f"スクリーンショットを取得中: {path_or_url}")
        if temp_dir is None:
            temp_dir = tempfile.TemporaryDirectory()
            temp_path = Path(temp_dir.name) / generate_filename('temp_screenshot')
        else:
            temp_path = Path(temp_dir.name) / generate_filename('temp_screenshot')

        # 非同期関数を実行
        try:
            asyncio.run(take_screenshot_from_url(path_or_url, str(temp_path)))
            return Image.open(temp_path)
        except Exception as e:
            raise IOError(f"URLからのスクリーンショット取得に失敗しました: {e}")

    # ファイルパスの場合
    path = Path(path_or_url)
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {path_or_url}")

    try:
        return Image.open(path)
    except Exception as e:
        raise IOError(f"画像の読み込みに失敗しました: {e}")


def calculate_similarity(hash1: imagehash.ImageHash, hash2: imagehash.ImageHash) -> float:
    """
    2つの画像ハッシュの類似度を計算する。

    Args:
        hash1: 1つ目の画像ハッシュ
        hash2: 2つ目の画像ハッシュ

    Returns:
        float: 類似度（0: 完全に異なる, 1: 同一）
    """
    max_distance = hash1.hash.size  # ハッシュサイズ（通常64）
    hamming_distance = hash1 - hash2
    return 1 - (hamming_distance / max_distance)


def compute_hashes(img: Image.Image) -> dict[str, imagehash.ImageHash]:
    """
    画像の各種ハッシュを計算する。

    Args:
        img: 入力画像

    Returns:
        dict: 各アルゴリズムのハッシュ値
    """
    return {
        'ahash': imagehash.average_hash(img),
        'phash': imagehash.phash(img),
        'dhash': imagehash.dhash(img),
        'whash': imagehash.whash(img),
    }


def resize_to_match(img1: Image.Image, img2: Image.Image) -> Tuple[Image.Image, Image.Image]:
    """
    2つの画像を同じサイズにリサイズする。

    Args:
        img1: 1つ目の画像
        img2: 2つ目の画像

    Returns:
        Tuple[Image.Image, Image.Image]: リサイズされた画像ペア
    """
    # 大きい方のサイズに合わせる
    target_width = max(img1.width, img2.width)
    target_height = max(img1.height, img2.height)

    resized1 = img1.resize((target_width, target_height), Image.Resampling.LANCZOS)
    resized2 = img2.resize((target_width, target_height), Image.Resampling.LANCZOS)

    return resized1, resized2


def create_diff_image(img1: Image.Image, img2: Image.Image) -> Image.Image:
    """
    2つの画像の差分画像を生成する。

    Args:
        img1: 1つ目の画像
        img2: 2つ目の画像

    Returns:
        Image.Image: 差分画像
    """
    # 同じサイズにリサイズ
    resized1, resized2 = resize_to_match(img1, img2)

    # 差分を計算
    diff = ImageChops.difference(resized1, resized2)

    # 差分を目立たせるために強調（3倍）
    diff = diff.point(lambda x: x * 3)

    # 背景を黒にするため、差分があるピクセル以外を黒く
    mask = diff.convert('L').point(lambda x: 255 if x > 30 else 0)

    # 赤色の差分画像を作成
    diff_colored = Image.new('RGB', diff.size, (0, 0, 0))
    diff_pixels = diff_colored.load()

    # diffをRGBに変換してピクセルにアクセス
    diff_rgb = diff.convert('RGB')

    for y in range(diff.size[1]):
        for x in range(diff.size[0]):
            if mask.getpixel((x, y)) > 0:
                # 差分の大きさに応じて色の強さを変える
                intensity = min(255, diff_rgb.getpixel((x, y))[0])
                diff_pixels[x, y] = (intensity, 0, 0)

    return diff_colored


def create_side_by_side_diff(
    img1: Image.Image,
    img2: Image.Image,
    box_size: int = 10
) -> Image.Image:
    """
    サイド・バイ・サイド（並列）差分画像を生成する。
    左に画像1、右に画像2を配置し、差分領域を赤い枠で囲む。

    Args:
        img1: 1つ目の画像
        img2: 2つ目の画像
        box_size: 差分枠の太さ

    Returns:
        Image.Image: サイド・バイ・サイド差分画像
    """
    # 同じサイズにリサイズ
    resized1, resized2 = resize_to_match(img1, img2)

    # 差分を計算
    diff = ImageChops.difference(resized1, resized2).convert('L')

    # サイド・バイ・サイド画像を作成
    width, height = resized1.size
    side_by_side = Image.new('RGB', (width * 2, height))
    side_by_side.paste(resized1, (0, 0))
    side_by_side.paste(resized2, (width, 0))

    # 差分領域を検出して矩形を描画
    draw = ImageDraw.Draw(side_by_side)

    # 差分のあるピクセルをグループ化して矩形を生成
    threshold = 30
    visited = set()
    diff_pixels = []

    for y in range(0, height, box_size):
        for x in range(0, width, box_size):
            # ボックス内に差分があるかチェック
            has_diff = False
            for by in range(y, min(y + box_size, height)):
                for bx in range(x, min(x + box_size, width)):
                    if diff.getpixel((bx, by)) > threshold:
                        has_diff = True
                        break
                if has_diff:
                    break

            if has_diff:
                # 左側の画像に赤枠
                draw.rectangle(
                    [x, y, x + box_size, y + box_size],
                    outline='red',
                    width=2
                )
                # 右側の画像にも赤枠
                draw.rectangle(
                    [width + x, y, width + x + box_size, y + box_size],
                    outline='red',
                    width=2
                )

    return side_by_side


def find_diff_regions(img1: Image.Image, img2: Image.Image, threshold: int = 30) -> list:
    """
    差分のある領域を検出する。

    Args:
        img1: 1つ目の画像
        img2: 2つ目の画像
        threshold: 差分と判定する閾値

    Returns:
        list: 差分領域のリスト [{'x', 'y', 'width', 'height', 'intensity'}, ...]
    """
    resized1, resized2 = resize_to_match(img1, img2)
    diff = ImageChops.difference(resized1, resized2).convert('L')

    regions = []
    box_size = 50  # 領域のサイズ
    width, height = diff.size

    for y in range(0, height, box_size):
        for x in range(0, width, box_size):
            # ボックス内の差分をチェック
            max_diff = 0
            diff_count = 0

            for by in range(y, min(y + box_size, height)):
                for bx in range(x, min(x + box_size, width)):
                    d = diff.getpixel((bx, by))
                    if d > threshold:
                        diff_count += 1
                        max_diff = max(max_diff, d)

            # 差分が一定以上ある場合は領域として記録
            if diff_count > 10:  # ボックス内の10ピクセル以上が差分
                regions.append({
                    'x': x,
                    'y': y,
                    'width': min(box_size, width - x),
                    'height': min(box_size, height - y),
                    'diff_pixels': diff_count,
                    'max_intensity': max_diff
                })

    return regions


def calculate_pixel_stats(img1: Image.Image, img2: Image.Image) -> dict:
    """
    ピクセル単位の差分統計を計算する。

    Args:
        img1: 1つ目の画像
        img2: 2つ目の画像

    Returns:
        dict: 差分統計情報
    """
    resized1, resized2 = resize_to_match(img1, img2)
    diff = ImageChops.difference(resized1, resized2).convert('L')

    # 統計情報を計算
    stat = ImageStat.Stat(diff)
    hist = diff.histogram()

    # 差分のあるピクセル数をカウント（閾値: 10）
    different_pixels = sum(hist[10:])

    total_pixels = diff.width * diff.height
    ratio = (different_pixels / total_pixels) * 100 if total_pixels > 0 else 0

    # extremaとmeanを安全に取得
    # extremaは [(min, max), ...] のリスト（各バンドごと）
    try:
        extrema = stat.extrema
        if extrema and len(extrema) > 0:
            # 最初のバンドの最大値を取得
            band_extrema = extrema[0]
            if isinstance(band_extrema, tuple) and len(band_extrema) >= 2:
                max_diff = int(band_extrema[1])
            else:
                max_diff = int(band_extrema) if band_extrema else 0
        else:
            max_diff = 0
    except (IndexError, TypeError):
        max_diff = 0

    try:
        mean_diff = float(stat.mean[0]) if stat.mean else 0.0
    except (IndexError, TypeError):
        mean_diff = 0.0

    return {
        'total_pixels': total_pixels,
        'different_pixels': different_pixels,
        'ratio': ratio,
        'max_diff': max_diff,
        'mean_diff': mean_diff,
    }


def compare_images(
    image1_path: str,
    image2_path: str,
    hash_algorithm: str = 'phash',
    threshold: float = 0.95
) -> dict:
    """
    2つの画像を比較する。
    URLの場合はスクリーンショットを取得して比較する。

    Args:
        image1_path: 1つ目の画像のパスまたはURL
        image2_path: 2つ目の画像のパスまたはURL
        hash_algorithm: ハッシュアルゴリズム
        threshold: 差分と判定する閾値

    Returns:
        dict: 比較結果
    """
    # 一時ディレクトリを作成（URLの場合に使用）
    temp_dir = tempfile.TemporaryDirectory()

    try:
        # 画像を読み込み（URLの場合はスクリーンショットを取得）
        img1 = load_image(image1_path, temp_dir)
        img2 = load_image(image2_path, temp_dir)

        # サイズチェック
        size_mismatch = img1.size != img2.size

        # 全ハッシュを計算
        hashes1 = compute_hashes(img1)
        hashes2 = compute_hashes(img2)

        # 類似度を計算
        similarities = {}
        for alg in hashes1:
            similarities[alg] = calculate_similarity(hashes1[alg], hashes2[alg])

        # 主要ハッシュアルゴリズムの類似度
        main_similarity = similarities[hash_algorithm]

        # 総合判定
        is_similar = main_similarity >= threshold
        if is_similar:
            judgment = "類似しています"
        else:
            judgment = "異なっています"

        # ピクセル統計
        pixel_stats = calculate_pixel_stats(img1, img2)

        result = {
            'image1': image1_path,
            'image2': image2_path,
            'size1': img1.size,
            'size2': img2.size,
            'size_mismatch': size_mismatch,
            'similarities': similarities,
            'main_similarity': main_similarity,
            'threshold': threshold,
            'is_similar': is_similar,
            'judgment': judgment,
            'hash_algorithm': hash_algorithm,
            'pixel_stats': pixel_stats,
        }

        return result

    finally:
        # 一時ディレクトリをクリーンアップ
        temp_dir.cleanup()


def generate_markdown_report(
    comparison: dict,
    diff_image_path: Optional[str] = None
) -> str:
    """
    Markdown形式の比較レポートを生成する。

    Args:
        comparison: 比較結果
        diff_image_path: 差分画像のパス（オプション）

    Returns:
        str: Markdown形式のレポート
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    lines = [
        "# 画像比較レポート",
        "",
        f"生成日時: {timestamp}",
        "",
        "## 比較対象",
        "",
        f"- **画像1**: `{comparison['image1']}` ({comparison['size1'][0]}x{comparison['size1'][1]})",
        f"- **画像2**: `{comparison['image2']}` ({comparison['size2'][0]}x{comparison['size2'][1]})",
    ]

    if comparison['size_mismatch']:
        lines.extend([
            "",
            "**注意**: 画像サイズが異なるため、比較時にリサイズされています。",
        ])

    lines.extend([
        "",
        "## 類似度スコア",
        "",
        "| ハッシュアルゴリズム | 類似度 | ハミング距離 |",
        "|---------------------|--------|-------------|",
    ])

    for alg in ['ahash', 'phash', 'dhash', 'whash']:
        sim = comparison['similarities'][alg]
        # ハミング距離を逆算
        hamming = int((1 - sim) * 64)
        lines.append(f"| {alg.upper()} | {sim:.4f} | {hamming} |")

    lines.extend([
        "",
        f"**総合判定**: {comparison['judgment']}（閾値: {comparison['threshold']}）",
        "",
        "## 詳細統計",
        "",
    ])

    stats = comparison['pixel_stats']
    ratio = stats['ratio']
    lines.extend([
        f"- **異なるピクセル数**: {stats['different_pixels']:,} / {stats['total_pixels']:,} ({ratio:.2f}%)",
        f"- **最大差分値**: {stats['max_diff']}",
        f"- **平均差分値**: {stats['mean_diff']:.1f}",
    ])

    if diff_image_path:
        lines.extend([
            "",
            "## 差分画像",
            "",
            f"![差分画像]({diff_image_path})",
        ])

    return '\n'.join(lines)


def parse_arguments() -> argparse.Namespace:
    """
    コマンドライン引数を解析する。

    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(
        description='2つの画像（ファイルまたはURL）を比較し、差分を可視化するCLIツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用例:
  python compare_images.py image1.png image2.png
  python compare_images.py https://example.com https://example.org
  python compare_images.py image1.png image2.png --output report.md
  python compare_images.py https://example.com https://example.org --diff-image diff.png
  python compare_images.py image1.png image2.png --hash-algorithm ahash --threshold 0.90
        '''
    )

    parser.add_argument(
        'image1',
        nargs='?',
        help='比較する1つ目の画像（ファイルパスまたはURL）'
    )

    parser.add_argument(
        'image2',
        nargs='?',
        help='比較する2つ目の画像（ファイルパスまたはURL）'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        metavar='FILE',
        help='出力Markdownファイルパス（デフォルト: comparison_report-{timestamp}.md）'
    )

    parser.add_argument(
        '--diff-image', '-d',
        type=str,
        default=None,
        metavar='FILE',
        help='差分画像の出力パス（デフォルト: diff-{timestamp}.png）'
    )

    parser.add_argument(
        '--hash-algorithm',
        type=str,
        choices=['ahash', 'phash', 'dhash', 'whash'],
        default='phash',
        help='ハッシュアルゴリズム（デフォルト: phash）'
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=0.95,
        metavar='VALUE',
        help='差分と判定する閾値0-1（デフォルト: 0.95）'
    )

    parser.add_argument(
        '--no-diff',
        action='store_true',
        help='差分画像を生成しない'
    )

    parser.add_argument(
        '--side-by-side',
        action='store_true',
        help='サイド・バイ・サイド（並列）差分画像を生成'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='差分情報をJSON形式で出力'
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> Tuple[int, Optional[str]]:
    """
    コマンドライン引数をバリデーションする。

    Args:
        args: パースされたコマンドライン引数

    Returns:
        Tuple[int, Optional[str]]: (終了コード, エラーメッセージ)
    """
    if not args.image1 or not args.image2:
        return 1, "エラー: 2つの画像ファイルパスを指定してください"

    if args.threshold < 0 or args.threshold > 1:
        return 1, "エラー: --threshold は0から1の間で指定してください"

    return 0, None


def main() -> int:
    """
    メイン関数。

    Returns:
        int: 終了コード（0: 成功, 1: エラー）
    """
    args = parse_arguments()

    # 引数バリデーション
    exit_code, error_msg = validate_args(args)
    if exit_code != 0:
        print(error_msg)
        return exit_code

    # 出力ファイル名の決定
    if args.output is None:
        output_path = generate_filename('comparison_report', 'md')
    else:
        output_path = args.output

    if args.no_diff:
        diff_image_path = None
    elif args.diff_image is None:
        diff_image_path = generate_filename('diff', 'png')
    else:
        diff_image_path = args.diff_image

    try:
        # 画像比較
        print(f"画像を比較中: {args.image1} vs {args.image2}")

        # URLかどうかをチェック
        is_url1 = is_url(args.image1)
        is_url2 = is_url(args.image2)

        comparison = compare_images(
            args.image1,
            args.image2,
            hash_algorithm=args.hash_algorithm,
            threshold=args.threshold
        )

        # 差分画像の生成（URLの場合は再度スクリーンショットを取得）
        diff_regions = []
        if not args.no_diff:
            # 一時ディレクトリを作成
            temp_diff_dir = tempfile.TemporaryDirectory()
            try:
                img1 = load_image(args.image1, temp_diff_dir)
                img2 = load_image(args.image2, temp_diff_dir)

                # サイド・バイ・サイドモード
                if args.side_by_side:
                    print(f"サイド・バイ・サイド差分画像を生成中: {diff_image_path}")
                    diff_img = create_side_by_side_diff(img1, img2)
                    diff_img.save(diff_image_path)
                else:
                    print(f"差分画像を生成中: {diff_image_path}")
                    diff_img = create_diff_image(img1, img2)
                    diff_img.save(diff_image_path)

                # 差分領域を検出
                diff_regions = find_diff_regions(img1, img2)

            finally:
                temp_diff_dir.cleanup()

        # Markdownレポートの生成
        print(f"レポートを生成中: {output_path}")
        report = generate_markdown_report(comparison, diff_image_path)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        # JSON出力（オプション）
        if args.json:
            import json
            json_path = output_path.replace('.md', '.json') if output_path.endswith('.md') else output_path + '.json'
            print(f"JSONデータを生成中: {json_path}")

            # comparison辞書をJSONシリアライズ可能な形式に変換
            comparison_serializable = {
                'image1': comparison['image1'],
                'image2': comparison['image2'],
                'size1': comparison['size1'],
                'size2': comparison['size2'],
                'size_mismatch': comparison['size_mismatch'],
                'similarities': comparison['similarities'],
                'main_similarity': comparison['main_similarity'],
                'threshold': comparison['threshold'],
                'is_similar': bool(comparison['is_similar']),
                'judgment': comparison['judgment'],
                'hash_algorithm': comparison['hash_algorithm'],
                'pixel_stats': comparison['pixel_stats']
            }

            json_data = {
                'timestamp': datetime.now().isoformat(),
                'comparison': comparison_serializable,
                'diff_regions': diff_regions,
                'diff_region_count': len(diff_regions),
                'image1': args.image1,
                'image2': args.image2
            }

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            print(f"JSONデータを保存しました: {json_path}")

        # 結果の表示
        print(f"\n{comparison['judgment']}（類似度: {comparison['main_similarity']:.4f}）")
        print(f"異なるピクセル: {comparison['pixel_stats']['different_pixels']:,} / {comparison['pixel_stats']['total_pixels']:,} ({comparison['pixel_stats']['ratio']:.2f}%)")

        if diff_regions and not args.side_by_side:
            print(f"\n差分領域数: {len(diff_regions)}")
            for i, region in enumerate(diff_regions[:10]):  # 最大10件表示
                print(f"  領域{i+1}: x={region['x']}, y={region['y']}, size={region['width']}x{region['height']}, diff_pixels={region['diff_pixels']}")
            if len(diff_regions) > 10:
                print(f"  ... 他 {len(diff_regions) - 10} 領域")

        if not args.no_diff:
            print(f"\n差分画像を保存しました: {diff_image_path}")
        print(f"レポートを保存しました: {output_path}")

        return 0

    except FileNotFoundError as e:
        print(f"エラー: {e}")
        return 1
    except IOError as e:
        print(f"エラー: {e}")
        return 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"エラー: 予期しないエラーが発生しました: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
