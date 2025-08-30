#!/usr/bin/env python3
"""
SVGファイルをPNGプレビュー用に変換するスクリプト
DocMindプロジェクト用のアイコンファイルを生成します
"""

import sys
from pathlib import Path

import cairosvg


def svg_to_png(svg_path, png_path, size=512):
    """
    SVGファイルをPNGファイルに変換する

    Args:
        svg_path (str): 入力SVGファイルのパス
        png_path (str): 出力PNGファイルのパス
        size (int): 出力サイズ（幅×高さ）
    """
    # SVGをPNGに変換
    cairosvg.svg2png(
        url=svg_path,
        write_to=str(png_path),
        output_width=size,
        output_height=size
    )


def main():
    """メイン関数"""
    # プロジェクトルートを取得
    project_root = Path(__file__).parent.parent
    assets_dir = project_root / "assets"

    # 入力・出力パス
    svg_path = assets_dir / "docmind_icon.svg"
    png_path = assets_dir / "docmind_preview.png"

    # SVGファイルの存在確認
    if not svg_path.exists():
        sys.exit(1)

    # 出力ディレクトリの作成
    png_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # SVGをPNGに変換
        svg_to_png(str(svg_path), str(png_path), size=512)

        # ファイルサイズの確認
        if png_path.exists():
            png_path.stat().st_size / 1024


    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
