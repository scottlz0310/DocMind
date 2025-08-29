#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
folder_tree.py 依存関係分析スクリプト

Phase4準備: folder_tree.pyの依存関係を完全分析し、
安全なリファクタリングのための情報を収集します。
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class DependencyAnalyzer:
    """依存関係分析クラス"""
    
    def __init__(self, target_file: str):
        self.target_file = target_file
        self.project_root = Path(__file__).parent.parent
        self.results = {
            'imports': [],
            'classes': [],
            'methods': [],
            'signals': [],
            'qt_dependencies': [],
            'internal_dependencies': [],
            'async_components': [],
            'ui_components': [],
            'risk_assessment': {}
        }
    
    def analyze(self) -> Dict:
        """完全分析を実行"""
        print(f"🔍 {self.target_file} の依存関係分析を開始...")
        
        if not os.path.exists(self.target_file):
            raise FileNotFoundError(f"対象ファイルが見つかりません: {self.target_file}")
        
        with open(self.target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # AST解析
        tree = ast.parse(content)
        
        # 各種分析実行
        self._analyze_imports(tree)
        self._analyze_classes(tree)
        self._analyze_methods(tree)
        self._analyze_signals(content)
        self._analyze_qt_dependencies(content)
        self._analyze_async_components(content)
        self._analyze_ui_components(content)
        self._assess_risks()
        
        print("✅ 依存関係分析完了")
        return self.results
    
    def _analyze_imports(self, tree: ast.AST):
        """インポート分析"""
        print("  📦 インポート分析中...")
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.results['imports'].append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    self.results['imports'].append({
                        'type': 'from_import',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
    
    def _analyze_classes(self, tree: ast.AST):
        """クラス分析"""
        print("  🏗️ クラス分析中...")
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [self._get_name(base) for base in node.bases]
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                
                self.results['classes'].append({
                    'name': node.name,
                    'bases': bases,
                    'methods': methods,
                    'method_count': len(methods),
                    'line': node.lineno,
                    'is_qt_widget': any('Q' in base for base in bases)
                })
    
    def _analyze_methods(self, tree: ast.AST):
        """メソッド分析"""
        print("  ⚙️ メソッド分析中...")
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # メソッドの複雑度を簡易計算
                complexity = self._calculate_complexity(node)
                
                self.results['methods'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'complexity': complexity,
                    'is_private': node.name.startswith('_'),
                    'is_slot': self._is_slot_method(node),
                    'is_async_related': self._is_async_method(node)
                })
    
    def _analyze_signals(self, content: str):
        """シグナル・スロット分析"""
        print("  📡 シグナル・スロット分析中...")
        
        # シグナル定義を検索
        signal_pattern = r'(\w+)\s*=\s*Signal\s*\([^)]*\)'
        signals = re.findall(signal_pattern, content)
        
        # connect呼び出しを検索
        connect_pattern = r'(\w+)\.connect\s*\([^)]+\)'
        connects = re.findall(connect_pattern, content)
        
        # emit呼び出しを検索
        emit_pattern = r'(\w+)\.emit\s*\([^)]*\)'
        emits = re.findall(emit_pattern, content)
        
        self.results['signals'] = {
            'definitions': signals,
            'connections': connects,
            'emissions': emits,
            'total_signal_usage': len(signals) + len(connects) + len(emits)
        }
    
    def _analyze_qt_dependencies(self, content: str):
        """Qt依存関係分析"""
        print("  🖼️ Qt依存関係分析中...")
        
        qt_patterns = {
            'widgets': r'Q\w*Widget|Q\w*Item|Q\w*Layout',
            'core': r'Q\w*Thread|Q\w*Timer|Q\w*Object',
            'gui': r'Q\w*Font|Q\w*Color|Q\w*Cursor',
            'signals': r'Signal|Slot|connect|emit'
        }
        
        for category, pattern in qt_patterns.items():
            matches = re.findall(pattern, content)
            self.results['qt_dependencies'].append({
                'category': category,
                'components': list(set(matches)),
                'count': len(matches)
            })
    
    def _analyze_async_components(self, content: str):
        """非同期コンポーネント分析"""
        print("  🔄 非同期コンポーネント分析中...")
        
        async_patterns = {
            'threads': r'QThread|Worker|moveToThread',
            'signals': r'started|finished|terminated',
            'methods': r'start\(\)|quit\(\)|wait\(\)|terminate\(\)'
        }
        
        for category, pattern in async_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                self.results['async_components'].append({
                    'category': category,
                    'components': list(set(matches)),
                    'count': len(matches)
                })
    
    def _analyze_ui_components(self, content: str):
        """UIコンポーネント分析"""
        print("  🎨 UIコンポーネント分析中...")
        
        ui_patterns = {
            'tree_operations': r'addTopLevelItem|takeTopLevelItem|currentItem',
            'item_operations': r'setExpanded|setSelected|setHidden',
            'events': r'mousePressEvent|enterEvent|leaveEvent',
            'styling': r'setStyleSheet|setIcon|setToolTip'
        }
        
        for category, pattern in ui_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                self.results['ui_components'].append({
                    'category': category,
                    'components': list(set(matches)),
                    'count': len(matches)
                })
    
    def _assess_risks(self):
        """リスク評価"""
        print("  ⚠️ リスク評価中...")
        
        # 複雑度リスク
        method_complexities = [m['complexity'] for m in self.results['methods']]
        avg_complexity = sum(method_complexities) / len(method_complexities) if method_complexities else 0
        
        # 非同期処理リスク
        async_risk = sum(comp['count'] for comp in self.results['async_components'])
        
        # Qt依存リスク
        qt_risk = sum(comp['count'] for comp in self.results['qt_dependencies'])
        
        # シグナル・スロットリスク
        signal_risk = self.results['signals']['total_signal_usage']
        
        self.results['risk_assessment'] = {
            'complexity_risk': {
                'level': 'HIGH' if avg_complexity > 10 else 'MEDIUM' if avg_complexity > 5 else 'LOW',
                'average_complexity': avg_complexity,
                'max_complexity': max(method_complexities) if method_complexities else 0
            },
            'async_risk': {
                'level': 'HIGH' if async_risk > 20 else 'MEDIUM' if async_risk > 10 else 'LOW',
                'component_count': async_risk
            },
            'qt_dependency_risk': {
                'level': 'HIGH' if qt_risk > 50 else 'MEDIUM' if qt_risk > 25 else 'LOW',
                'dependency_count': qt_risk
            },
            'signal_risk': {
                'level': 'HIGH' if signal_risk > 30 else 'MEDIUM' if signal_risk > 15 else 'LOW',
                'signal_usage_count': signal_risk
            },
            'overall_risk': self._calculate_overall_risk(avg_complexity, async_risk, qt_risk, signal_risk)
        }
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """��ソッドの循環的複雑度を簡易計算"""
        complexity = 1  # 基本複雑度
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _is_slot_method(self, node: ast.FunctionDef) -> bool:
        """スロットメソッドかどうか判定"""
        return any(
            keyword in node.name.lower() 
            for keyword in ['slot', 'on_', 'handle_', '_on_']
        )
    
    def _is_async_method(self, node: ast.FunctionDef) -> bool:
        """非同期関連メソッドかどうか判定"""
        return any(
            keyword in node.name.lower()
            for keyword in ['thread', 'worker', 'async', 'load', 'cleanup']
        )
    
    def _get_name(self, node: ast.AST) -> str:
        """ASTノードから名前を取得"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return str(node)
    
    def _calculate_overall_risk(self, complexity: float, async_risk: int, qt_risk: int, signal_risk: int) -> str:
        """総合リスクレベルを計算"""
        risk_score = 0
        
        if complexity > 10:
            risk_score += 3
        elif complexity > 5:
            risk_score += 2
        else:
            risk_score += 1
        
        if async_risk > 20:
            risk_score += 3
        elif async_risk > 10:
            risk_score += 2
        else:
            risk_score += 1
        
        if qt_risk > 50:
            risk_score += 3
        elif qt_risk > 25:
            risk_score += 2
        else:
            risk_score += 1
        
        if signal_risk > 30:
            risk_score += 3
        elif signal_risk > 15:
            risk_score += 2
        else:
            risk_score += 1
        
        if risk_score >= 10:
            return 'CRITICAL'
        elif risk_score >= 8:
            return 'HIGH'
        elif risk_score >= 6:
            return 'MEDIUM'
        else:
            return 'LOW'

def main():
    """メイン実行関数"""
    target_file = "src/gui/folder_tree.py"
    
    if not os.path.exists(target_file):
        print(f"❌ 対象ファイルが見つかりません: {target_file}")
        return
    
    analyzer = DependencyAnalyzer(target_file)
    results = analyzer.analyze()
    
    # 結果をJSONファイルに保存
    output_file = "folder_tree_dependencies.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # サマリーレポート出力
    print("\n" + "="*60)
    print("📊 FOLDER_TREE.PY 依存関係分析結果")
    print("="*60)
    
    print(f"\n📦 インポート: {len(results['imports'])}個")
    print(f"🏗️ クラス: {len(results['classes'])}個")
    print(f"⚙️ メソッド: {len(results['methods'])}個")
    print(f"📡 シグナル使用: {results['signals']['total_signal_usage']}箇所")
    
    print(f"\n⚠️ 総合リスクレベル: {results['risk_assessment']['overall_risk']}")
    
    for risk_type, risk_data in results['risk_assessment'].items():
        if risk_type != 'overall_risk' and isinstance(risk_data, dict):
            print(f"   {risk_type}: {risk_data['level']}")
    
    print(f"\n💾 詳細結果を保存: {output_file}")
    print("✅ 分析完了")

if __name__ == "__main__":
    main()