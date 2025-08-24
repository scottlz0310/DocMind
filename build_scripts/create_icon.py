#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVGファイルをICOファイルに変換するスクリプト
DocMindプロジェクト用のアイコンファイルを生成します
"""

import sys
from pathlib import Path
from PIL import Image
import cairosvg
import io

def svg_to_ico(svg_path, ico_path, sizes=None):
    """
    SVGファイルをICOファイルに変換する
    
    Args:
        svg_path (str): 入力SVGファイルのパス
        ico_path (str): 出力ICOファイルのパス
        sizes (list): ICOファイルに含めるサイズのリスト
    """
    if sizes is None:
        sizes = [16, 32, 48, 64, 128, 256]
    
    # SVGをPNGに変換
    png_data = cairosvg.svg2png(
        url=svg_path, 
        output_width=256, 
        output_height=256
    )
    
    # PNGデータをPIL Imageに変換
    png_image = Image.open(io.BytesIO(png_data))
    
    # 各サイズの画像を作成
    images = []
    for size in sizes:
        resized_image = png_image.resize(
            (size, size), 
            Image.Resampling.LANCZOS
        )
        images.append(resized_image)
    
    # ICOファイルとして保存
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(size, size) for size in sizes],
        append_images=images[1:]
    )
    
    print(f"✅ ICOファイルを作成しました: {ico_path}")
    print(f"   含まれるサイズ: {', '.join(map(str, sizes))}")


def main():
    """メイン関数"""
    # プロジェクトルートを取得
    project_root = Path(__file__).parent.parent
    assets_dir = project_root / "assets"
    
    # 入力・出力パス
    svg_path = assets_dir / "docmind_icon.svg"
    ico_path = assets_dir / "docmind.ico"
    
    # SVGファイルの存在確認
    if not svg_path.exists():
        print(f"❌ SVGファイルが見つかりません: {svg_path}")
        sys.exit(1)
    
    # 出力ディレクトリの作成
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # SVGをICOに変換
        svg_to_ico(str(svg_path), str(ico_path))
        
        # ファイルサイズの確認
        if ico_path.exists():
            size_kb = ico_path.stat().st_size / 1024
            print(f"📁 ファイルサイズ: {size_kb:.1f} KB")
        
        print("🎉 DocMindアイコンの作成が完了しました！")
        
    except ImportError as e:
        print(f"❌ 必要なライブラリがインストールされていません: {e}")
        print("以下のコマンドでインストールしてください:")
        print("pip install pillow cairosvg")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
