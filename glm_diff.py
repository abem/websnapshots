#!/usr/bin/env python3
"""
GLM-4V AI画像比較ツール

GLM-4V APIを使用して、AIによる高度な画像差分分析を行う。
文字、図形、レイアウトなど、意味的な差分を検出・分析します。
"""

import argparse
import asyncio
import base64
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

try:
    from PIL import Image
    from playwright.async_api import async_playwright, Error as PlaywrightError
    try:
        from zai import ZhipuAiClient
        USE_NEW_SDK = True
    except ImportError:
        from zhipuai import ZhipuAI
        USE_NEW_SDK = False
except ImportError as e:
    missing_lib = str(e).split("'")[1] if "'" in str(e) else str(e)
    print(f"エラー: {missing_lib} がインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("  pip install Pillow playwright zhipuai")
    sys.exit(1)


def generate_filename(prefix: str, ext: str = 'png') -> str:
    """タイムスタンプ付きのファイル名を生成する。"""
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    return f'{prefix}-{timestamp}.{ext}'


def is_url(text: str) -> bool:
    """文字列がURLかどうかを判定する。"""
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


def load_image(path_or_url: str, temp_dir: Optional[tempfile.TemporaryDirectory] = None) -> str:
    """画像を読み込み、ファイルパスを返す。URLの場合はスクリーンショットを取得。"""
    if is_url(path_or_url):
        print(f"スクリーンショットを取得中: {path_or_url}")
        if temp_dir is None:
            temp_dir = tempfile.TemporaryDirectory()
            temp_path = Path(temp_dir.name) / generate_filename('temp_screenshot')
        else:
            temp_path = Path(temp_dir.name) / generate_filename('temp_screenshot')

        try:
            asyncio.run(take_screenshot_from_url(path_or_url, str(temp_path)))
            return str(temp_path)
        except Exception as e:
            raise IOError(f"URLからのスクリーンショット取得に失敗しました: {e}")

    path = Path(path_or_url)
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {path_or_url}")

    return str(path)


def encode_image_to_base64(image_path: str) -> str:
    """画像をbase64エンコードする。"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def analyze_with_glm4v(
    image1_path: str,
    image2_path: str,
    api_key: str,
    model: str = "glm-4v"
) -> dict:
    """
    GLM-4V APIを使用して2つの画像の差分を分析する。

    Args:
        image1_path: 1つ目の画像のパス
        image2_path: 2つ目の画像のパス
        api_key: GLM APIキー
        model: 使用するモデル（デフォルト: glm-4v）
               利用可能なモデル: glm-4v, glm-4v-flash, glm-4v-plus, glm-4.5v, glm-4

    Returns:
        dict: 分析結果
    """
    # 画像をbase64エンコード
    base64_img1 = encode_image_to_base64(image1_path)
    base64_img2 = encode_image_to_base64(image2_path)

    # クライアントの初期化（新旧SDK両対応）
    if USE_NEW_SDK:
        client = ZhipuAiClient(api_key=api_key)
    else:
        client = ZhipuAI(api_key=api_key)

    # プロンプト
    prompt = """あなたはWebページの視覚的回帰テストの専門家です。
2つのスクリーンショット画像を比較し、以下の形式でJSONを出力してください：

{
  "overall_similarity": 0.95,
  "summary": "全体的な差分の要約",
  "differences": [
    {
      "type": "text|layout|color|element",
      "description": "差分の説明",
      "location": "画面上部/中央/下部/左側/右側",
      "severity": "low|medium|high",
      "before": "変更前の内容（該当する場合）",
      "after": "変更後の内容（該当する場合）"
    }
  ],
  "text_changes": {
    "added": ["追加されたテキスト1", "追加されたテキスト2"],
    "removed": ["削除されたテキスト1", "削除されたテキスト2"],
    "modified": [{"before": "変更前", "after": "変更後", "location": "位置"}]
  },
  "visual_changes": {
    "color_changes": ["色の変化があった場所"],
    "layout_changes": ["レイアウトの変化があった場所"],
    "element_changes": ["UI要素の変化があった場所"]
  },
  "recommendation": "この差分についての推奨事項（例：デプロイすべき、要調査など）"
}

JSONのみを出力し、他のテキストを含めないでください。"""

    # フォールバックモデルのリスト
    fallback_models = [model]
    if model == "glm-4v" and "glm-4v-plus" not in fallback_models:
        fallback_models.extend(["glm-4v-plus", "glm-4.6v", "glm-4.5v"])

    last_error = None

    for try_model in fallback_models:
        try:
            print(f"GLM-4Vで分析中... (モデル: {try_model})")
            response = client.chat.completions.create(
                model=try_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_img1}"}
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_img2}"}
                            }
                        ]
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )

            # レスポンスからJSONを抽出
            content = response.choices[0].message.content

            # ```jsonと```を削除（もしあれば）
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]

            # JSONをパース
            result = json.loads(content.strip())
            result["_model_used"] = try_model  # 使用したモデルを記録
            return result

        except Exception as e:
            last_error = e
            error_msg = str(e)
            # エラーコード1211（モデルが存在しない）の場合は次のモデルを試す
            if '1211' in error_msg or '模型不存在' in error_msg:
                print(f"  モデル {try_model} は利用できません。次のモデルを試します...")
                continue
            # その他のエラー場合は即座にリターン
            break

    return {
        "error": f"すべてのモデルでエラーが発生しました: {last_error}",
        "raw_response": content if 'content' in locals() else None,
        "_models_tried": fallback_models
    }


def generate_glm_comparison_report(
    image1_path: str,
    image2_path: str,
    analysis: dict,
    diff_image_path: Optional[str] = None
) -> str:
    """GLM分析レポートを生成する。"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    lines = [
        "# GLM-4V AI画像差分分析レポート",
        "",
        f"生成日時: {timestamp}",
        "",
        "## 比較対象",
        "",
        f"- **画像1**: `{image1_path}`",
        f"- **画像2**: `{image2_path}`",
        "",
    ]

    if "error" in analysis:
        lines.extend([
            "## エラー",
            "",
            f"分析中にエラーが発生しました: {analysis['error']}",
        ])
        if analysis.get("raw_response"):
            lines.extend([
                "",
                "### 生レスポンス",
                "",
                "```",
                analysis["raw_response"],
                "```"
            ])
        return '\n'.join(lines)

    lines.extend([
        f"## 全体評価",
        "",
        f"- **類似度**: {analysis.get('overall_similarity', 'N/A')}",
        f"- **要約**: {analysis.get('summary', 'N/A')}",
        "",
    ])

    # 差分詳細
    differences = analysis.get('differences', [])
    if differences:
        lines.extend([
            "## 差分詳細",
            ""
        ])
        for i, diff in enumerate(differences, 1):
            severity_emoji = {
                'low': '🟢',
                'medium': '🟡',
                'high': '🔴'
            }.get(diff.get('severity', 'low'), '⚪')

            lines.extend([
                f"### 差分 {i}: {diff.get('type', 'N/A')} {severity_emoji}",
                f"- **説明**: {diff.get('description', 'N/A')}",
                f"- **位置**: {diff.get('location', 'N/A')}",
                f"- **重要度**: {diff.get('severity', 'N/A')}",
            ])
            if diff.get('before'):
                lines.append(f"- **変更前**: `{diff.get('before')}`")
            if diff.get('after'):
                lines.append(f"- **変更後**: `{diff.get('after')}`")
            lines.append("")
    else:
        lines.extend([
            "## 差分詳細",
            "",
            "差分は検出されませんでした。",
            ""
        ])

    # テキスト変更
    text_changes = analysis.get('text_changes', {})
    if text_changes:
        lines.extend([
            "## テキスト変更",
            ""
        ])

        if text_changes.get('added'):
            lines.extend([
                "### 追加されたテキスト",
                ""
            ])
            for text in text_changes['added']:
                lines.append(f"- + {text}")
            lines.append("")

        if text_changes.get('removed'):
            lines.extend([
                "### 削除されたテキスト",
                ""
            ])
            for text in text_changes['removed']:
                lines.append(f"- - {text}")
            lines.append("")

        if text_changes.get('modified'):
            lines.extend([
                "### 変更されたテキスト",
                ""
            ])
            for change in text_changes['modified']:
                lines.append(f"- `{change.get('before', 'N/A')}` → `{change.get('after', 'N/A')}` ({change.get('location', 'N/A')})")
            lines.append("")

    # 視覚的変更
    visual_changes = analysis.get('visual_changes', {})
    if visual_changes:
        lines.extend([
            "## 視覚的変更",
            ""
        ])

        if visual_changes.get('color_changes'):
            lines.extend([
                "### 色の変化",
                ""
            ])
            for change in visual_changes['color_changes']:
                lines.append(f"- {change}")
            lines.append("")

        if visual_changes.get('layout_changes'):
            lines.extend([
                "### レイアウトの変化",
                ""
            ])
            for change in visual_changes['layout_changes']:
                lines.append(f"- {change}")
            lines.append("")

        if visual_changes.get('element_changes'):
            lines.extend([
                "### UI要素の変化",
                ""
            ])
            for change in visual_changes['element_changes']:
                lines.append(f"- {change}")
            lines.append("")

    # 推奨事項
    recommendation = analysis.get('recommendation')
    if recommendation:
        lines.extend([
            "## 推奨事項",
            "",
            recommendation,
            ""
        ])

    # 差分画像
    if diff_image_path:
        lines.extend([
            "## 参照画像",
            "",
            f"![差分画像]({diff_image_path})",
            ""
        ])

    return '\n'.join(lines)


def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数を解析する。"""
    parser = argparse.ArgumentParser(
        description='GLM-4V AIによる高度な画像差分分析ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用例:
  python glm_diff.py image1.png image2.png
  python glm_diff.py https://example.com https://example.org
  python glm_diff.py image1.png image2.png --output report.md
  python glm_diff.py image1.png image2.png --api-key YOUR_KEY
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
        '--api-key', '-k',
        type=str,
        default=None,
        help='GLM APIキー（省略時は環境変数GLM_API_KEYを使用）'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='glm-4v',
        help='使用するモデル（デフォルト: glm-4v）。利用可能なモデル: glm-4v, glm-4v-flash, glm-4v-plus, glm-4.6v, glm-4.5v, glm-4'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='出力Markdownファイルパス'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='JSON形式でも出力'
    )

    parser.add_argument(
        '--side-by-side',
        action='store_true',
        help='サイド・バイ・サイド画像も生成'
    )

    return parser.parse_args()


def main() -> int:
    """メイン関数。"""
    args = parse_arguments()

    # APIキーの取得
    api_key = args.api_key
    if not api_key:
        import os
        api_key = os.environ.get('GLM_API_KEY')
        if not api_key:
            print("エラー: APIキーが指定されていません。")
            print("--api-key オプションまたは GLM_API_KEY 環境変数を設定してください。")
            return 1

    # 出力ファイル名の決定
    if args.output is None:
        output_path = generate_filename('glm_diff_report', 'md')
    else:
        output_path = args.output

    try:
        print(f"GLM-4V AI画像差分分析を開始: {args.image1} vs {args.image2}")

        # 画像を読み込み
        temp_dir = tempfile.TemporaryDirectory()
        try:
            img1_path = load_image(args.image1, temp_dir)
            img2_path = load_image(args.image2, temp_dir)

            # GLM-4Vで分析
            analysis = analyze_with_glm4v(
                img1_path,
                img2_path,
                api_key,
                model=args.model
            )

            # サイド・バイ・サイド画像（オプション）
            diff_image_path = None
            if args.side_by_side:
                diff_image_path = generate_filename('glm_diff', 'png')
                print(f"サイド・バイ・サイド画像を生成中: {diff_image_path}")

                from PIL import Image
                img1 = Image.open(img1_path)
                img2 = Image.open(img2_path)

                if img1.size != img2.size:
                    target_width = max(img1.width, img2.width)
                    target_height = max(img1.height, img2.height)
                    img1 = img1.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    img2 = img2.resize((target_width, target_height), Image.Resampling.LANCZOS)

                width, height = img1.size
                side_by_side = Image.new('RGB', (width * 2, height))
                side_by_side.paste(img1, (0, 0))
                side_by_side.paste(img2, (width, 0))
                side_by_side.save(diff_image_path)

            # レポート生成
            print(f"レポートを生成中: {output_path}")
            report = generate_glm_comparison_report(
                args.image1,
                args.image2,
                analysis,
                diff_image_path
            )

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)

            # JSON出力
            if args.json:
                json_path = output_path.replace('.md', '.json') if output_path.endswith('.md') else output_path + '.json'
                print(f"JSONデータを生成中: {json_path}")

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, indent=2, ensure_ascii=False)

                print(f"JSONデータを保存しました: {json_path}")

            # 結果表示
            if "error" in analysis:
                print(f"\nエラーが発生しました: {analysis['error']}")
                return 1

            print(f"\n=== 分析結果 ===")
            print(f"類似度: {analysis.get('overall_similarity', 'N/A')}")
            print(f"要約: {analysis.get('summary', 'N/A')}")
            print(f"差分数: {len(analysis.get('differences', []))}")

            if diff_image_path:
                print(f"\nサイド・バイ・サイド画像を保存しました: {diff_image_path}")
            print(f"レポートを保存しました: {output_path}")

            return 0

        finally:
            temp_dir.cleanup()

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"エラー: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
