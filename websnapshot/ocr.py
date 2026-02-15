"""
OCR functionality for Web Snapshot Tool.

GLM-4V APIを使用して画像をOCR分析する機能を提供します。
"""

import json
from datetime import datetime
from typing import Dict, Any

from websnapshot.utils import encode_image_to_base64


OCR_PROMPT = """Extract all text from this image. Return JSON only. Format:
{
  "page_title": "string",
  "text_blocks": [{"type": "string", "text": "string"}],
  "links": ["string"],
  "buttons": ["string"]
}"""


def perform_ocr(
    image_path: str,
    api_key: str,
    languages: str = "ja+en",
    model: str = "glm-4v"
) -> Dict[str, Any]:
    """
    GLM-4V APIを使用して画像をOCR分析する。

    Args:
        image_path: 分析する画像のパス
        api_key: GLM APIキー
        languages: 対象言語（+区切り、例: "ja+en"）
        model: 使用するモデル（デフォルト: glm-4v）
               利用可能なモデル: glm-4v, glm-4v-flash, glm-4v-plus, glm-4.5v, glm-4

    Returns:
        dict: OCR分析結果
    """
    base64_img = encode_image_to_base64(image_path)

    # クライアントの初期化（新旧SDK両対応）
    try:
        from zai import ZhipuAiClient
        USE_NEW_SDK = True
    except ImportError:
        from zhipuai import ZhipuAI
        USE_NEW_SDK = False

    if USE_NEW_SDK:
        client = ZhipuAiClient(api_key=api_key)
    else:
        client = ZhipuAI(api_key=api_key)

    # 言語指定をプロンプトに追加
    prompt = OCR_PROMPT
    if languages:
        lang_prompt = f"\n\n対象言語: {languages}\n以上の言語を中心にテキストを抽出してください。"
        prompt = OCR_PROMPT + lang_prompt

    # フォールバックモデルのリスト
    fallback_models = [model]
    if model == "glm-4v" and "glm-4v-plus" not in fallback_models:
        fallback_models.extend(["glm-4v-plus", "glm-4.6v", "glm-4.5v"])

    last_error = None
    content = None  # 変数を初期化してUnboundLocalErrorを防ぐ

    for try_model in fallback_models:
        try:
            print(f"GLM-4VでOCR分析中... (モデル: {try_model})")
            response = client.chat.completions.create(
                model=try_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                            }
                        ]
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )

            content = response.choices[0].message.content

            # ```jsonや```を削除（もしあれば）
            content = content.strip()
            # 複数のマークダウンコードブロックパターンに対応
            while content.startswith('```'):
                # 最初の```を探して削除
                first_newline = content.find('\n')
                if first_newline != -1:
                    content = content[first_newline + 1:]
                else:
                    content = content[3:]
                    break
                content = content.strip()
            while content.endswith('```'):
                content = content[:-3].strip()

            result = json.loads(content.strip())
            result["_model_used"] = try_model
            return result

        except Exception as e:
            last_error = e
            error_msg = str(e)
            if '1211' in error_msg or '模型不存在' in error_msg:
                print(f"  モデル {try_model} は利用できません。次のモデルを試します...")
                continue
            break

    return {
        "error": f"すべてのモデルでエラーが発生しました: {last_error}",
        "raw_response": content if 'content' in locals() else None,
        "_models_tried": fallback_models
    }


def generate_ocr_report(
    ocr_result: Dict[str, Any],
    image_path: str,
    url: str,
    format_type: str = "markdown"
) -> str:
    """
    OCR結果からレポートを生成する。

    Args:
        ocr_result: GLM-4VのOCR分析結果
        image_path: 分析した画像のパス
        url: 元のURL
        format_type: 出力フォーマット（markdown, json, text）

    Returns:
        str: 生成されたレポート
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if format_type == "json":
        return json.dumps(ocr_result, indent=2, ensure_ascii=False)

    if format_type == "text":
        lines = [
            "=== OCR結果 ===",
            f"URL: {url}",
            ""
        ]

        if "error" in ocr_result:
            lines.extend([
                f"エラー: {ocr_result['error']}"
            ])
            return '\n'.join(lines)

        if ocr_result.get('page_title'):
            lines.extend([
                f"タイトル: {ocr_result['page_title']}",
                ""
            ])

        if ocr_result.get('full_text'):
            lines.extend([
                "【全テキスト】",
                ocr_result['full_text'],
                ""
            ])

        if ocr_result.get('text_blocks'):
            lines.extend([
                "【テキストブロック】",
                ""
            ])
            for i, block in enumerate(ocr_result['text_blocks'], 1):
                block_type = block.get('type', 'unknown')
                text = block.get('text', '')
                location = block.get('location', '')
                lines.append(f"{i}. [{block_type}] {text}")
                if location:
                    lines.append(f"   位置: {location}")
            lines.append("")

        if ocr_result.get('links'):
            lines.extend([
                "【リンク】",
                ""
            ])
            for i, link in enumerate(ocr_result['links'], 1):
                text = link.get('text', '')
                href = link.get('href', '')
                location = link.get('location', '')
                lines.append(f"{i}. {text} -> {href}")
                if location:
                    lines.append(f"   位置: {location}")
            lines.append("")

        if ocr_result.get('metadata'):
            lines.extend([
                "【メタデータ】",
                ""
            ])
            metadata = ocr_result['metadata']
            for key, value in metadata.items():
                lines.append(f"{key}: {value}")

        return '\n'.join(lines)

    # Markdown形式（デフォルト）
    lines = [
        "# OCRレポート",
        "",
        f"**URL**: {url}",
        f"**抽出日時**: {timestamp}",
        ""
    ]

    if "error" in ocr_result:
        lines.extend([
            "## エラー",
            "",
            f"分析中にエラーが発生しました: {ocr_result['error']}",
        ])
        if ocr_result.get("raw_response"):
            lines.extend([
                "",
                "### 生レスポンス",
                "",
                "```",
                ocr_result["raw_response"],
                "```"
            ])
        return '\n'.join(lines)

    if ocr_result.get('page_title'):
        lines.extend([
            f"**タイトル**: {ocr_result['page_title']}",
            ""
        ])

    if ocr_result.get('full_text'):
        lines.extend([
            "## 全テキスト",
            "",
            ocr_result['full_text'],
            ""
        ])

    if ocr_result.get('text_blocks'):
        lines.extend([
            "## テキストブロック詳細",
            ""
        ])
        for block in ocr_result['text_blocks']:
            block_type = block.get('type', 'unknown')
            lines.extend([
                f"### {block_type}",
                f"- **テキスト**: {block.get('text', '')}",
                f"- **位置**: {block.get('location', '')}",
                f"- **信頼度**: {block.get('confidence', '')}",
                ""
            ])

    if ocr_result.get('links'):
        lines.extend([
            "## リンク",
            "",
            "| テキスト | URL | 位置 |",
            "|---------|-----|------|",
        ])
        for link in ocr_result['links']:
            text = link.get('text', '')
            href = link.get('href', '')
            location = link.get('location', '')
            lines.append(f"| {text} | {href} | {location} |")
        lines.append("")

    if ocr_result.get('metadata'):
        lines.extend([
            "## メタデータ",
            "",
            "| 項目 | 値 |",
            "|------|-----|",
        ])
        metadata = ocr_result['metadata']
        for key, value in metadata.items():
            lines.append(f"| {key} | {value} |")

    return '\n'.join(lines)
