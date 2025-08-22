"""
検索履歴の管理を行うリポジトリモジュール

このモジュールは、検索履歴の記録、取得、分析機能を提供します。
ユーザーの検索パターンの分析や検索提案機能をサポートします。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from .database import DatabaseManager
from .models import SearchType
from ..utils.exceptions import DatabaseError


class SearchHistoryRepository:
    """検索履歴の管理を行うリポジトリクラス
    
    検索履歴の記録、取得、統計分析機能を提供し、
    ユーザーの検索体験向上をサポートします。
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """SearchHistoryRepositoryを初期化
        
        Args:
            db_manager (DatabaseManager): データベースマネージャー
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def add_search_record(self, query: str, search_type: SearchType, 
                         result_count: int, execution_time_ms: int) -> bool:
        """検索履歴レコードを追加
        
        Args:
            query (str): 検索クエリ
            search_type (SearchType): 検索タイプ
            result_count (int): 結果数
            execution_time_ms (int): 実行時間（ミリ秒）
            
        Returns:
            bool: 成功した場合True
        """
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    INSERT INTO search_history (
                        query, search_type, result_count, execution_time_ms
                    ) VALUES (?, ?, ?, ?)
                """, (query, search_type.value, result_count, execution_time_ms))
                
                conn.commit()
                self.logger.debug(f"検索履歴を記録: {query} ({search_type.value})")
                return True
                
        except Exception as e:
            self.logger.error(f"検索履歴記録エラー: {e}")
            raise DatabaseError(f"検索履歴の記録に失敗しました: {e}")
    
    def get_recent_searches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """最近の検索履歴を取得
        
        Args:
            limit (int): 取得する最大件数
            
        Returns:
            List[Dict[str, Any]]: 検索履歴のリスト
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, query, search_type, timestamp, 
                           result_count, execution_time_ms
                    FROM search_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                return [
                    {
                        'id': row[0],
                        'query': row[1],
                        'search_type': SearchType(row[2]),
                        'timestamp': datetime.fromisoformat(row[3]),
                        'result_count': row[4],
                        'execution_time_ms': row[5]
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            self.logger.error(f"最近の検索履歴取得エラー: {e}")
            raise DatabaseError(f"検索履歴の取得に失敗しました: {e}")
    
    def get_popular_queries(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """人気の検索クエリを取得
        
        Args:
            days (int): 対象期間（日数）
            limit (int): 取得する最大件数
            
        Returns:
            List[Dict[str, Any]]: 人気クエリのリスト
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT query, COUNT(*) as search_count,
                           AVG(result_count) as avg_results,
                           AVG(execution_time_ms) as avg_time
                    FROM search_history
                    WHERE timestamp >= ?
                    GROUP BY query
                    ORDER BY search_count DESC, avg_results DESC
                    LIMIT ?
                """, (since_date, limit))
                
                return [
                    {
                        'query': row[0],
                        'search_count': row[1],
                        'avg_results': round(row[2], 1),
                        'avg_execution_time_ms': round(row[3], 1)
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            self.logger.error(f"人気クエリ取得エラー: {e}")
            raise DatabaseError(f"人気クエリの取得に失敗しました: {e}")
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """検索提案を取得
        
        Args:
            partial_query (str): 部分的な検索クエリ
            limit (int): 取得する最大件数
            
        Returns:
            List[str]: 検索提案のリスト
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT query, COUNT(*) as frequency
                    FROM search_history
                    WHERE query LIKE ? AND LENGTH(query) > ?
                    GROUP BY query
                    ORDER BY frequency DESC, LENGTH(query) ASC
                    LIMIT ?
                """, (f"{partial_query}%", len(partial_query), limit))
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"検索提案取得エラー: {e}")
            raise DatabaseError(f"検索提案の取得に失敗しました: {e}")
    
    def get_search_statistics(self, days: int = 30) -> Dict[str, Any]:
        """検索統計情報を取得
        
        Args:
            days (int): 対象期間（日数）
            
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            with self.db_manager.get_connection() as conn:
                stats = {}
                
                # 総検索数
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM search_history WHERE timestamp >= ?
                """, (since_date,))
                stats['total_searches'] = cursor.fetchone()[0]
                
                # 検索タイプ別統計
                cursor = conn.execute("""
                    SELECT search_type, COUNT(*) as count,
                           AVG(result_count) as avg_results,
                           AVG(execution_time_ms) as avg_time
                    FROM search_history
                    WHERE timestamp >= ?
                    GROUP BY search_type
                """, (since_date,))
                
                stats['by_search_type'] = {
                    row[0]: {
                        'count': row[1],
                        'avg_results': round(row[2], 1),
                        'avg_execution_time_ms': round(row[3], 1)
                    }
                    for row in cursor.fetchall()
                }
                
                # 日別検索数
                cursor = conn.execute("""
                    SELECT DATE(timestamp) as search_date, COUNT(*) as count
                    FROM search_history
                    WHERE timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY search_date DESC
                """, (since_date,))
                
                stats['daily_counts'] = {
                    row[0]: row[1] for row in cursor.fetchall()
                }
                
                # パフォーマンス統計
                cursor = conn.execute("""
                    SELECT AVG(execution_time_ms) as avg_time,
                           MIN(execution_time_ms) as min_time,
                           MAX(execution_time_ms) as max_time,
                           AVG(result_count) as avg_results
                    FROM search_history
                    WHERE timestamp >= ?
                """, (since_date,))
                
                row = cursor.fetchone()
                if row and row[0] is not None:
                    stats['performance'] = {
                        'avg_execution_time_ms': round(row[0], 1),
                        'min_execution_time_ms': row[1],
                        'max_execution_time_ms': row[2],
                        'avg_result_count': round(row[3], 1)
                    }
                else:
                    stats['performance'] = {
                        'avg_execution_time_ms': 0,
                        'min_execution_time_ms': 0,
                        'max_execution_time_ms': 0,
                        'avg_result_count': 0
                    }
                
                return stats
                
        except Exception as e:
            self.logger.error(f"検索統計取得エラー: {e}")
            raise DatabaseError(f"検索統計の取得に失敗しました: {e}")
    
    def clear_old_history(self, days_to_keep: int = 90) -> int:
        """古い検索履歴を削除
        
        Args:
            days_to_keep (int): 保持する日数
            
        Returns:
            int: 削除されたレコード数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM search_history WHERE timestamp < ?
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"{deleted_count}件の古い検索履歴を削除しました")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"古い履歴削除エラー: {e}")
            raise DatabaseError(f"古い検索履歴の削除に失敗しました: {e}")
    
    def get_search_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """検索トレンドを取得
        
        Args:
            days (int): 対象期間（日数）
            
        Returns:
            List[Dict[str, Any]]: トレンド情報のリスト
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT query, 
                           COUNT(*) as total_searches,
                           COUNT(DISTINCT DATE(timestamp)) as active_days,
                           AVG(result_count) as avg_results,
                           MAX(timestamp) as last_searched
                    FROM search_history
                    WHERE timestamp >= ? AND result_count > 0
                    GROUP BY query
                    HAVING total_searches >= 2
                    ORDER BY total_searches DESC, avg_results DESC
                    LIMIT 50
                """, (since_date,))
                
                return [
                    {
                        'query': row[0],
                        'total_searches': row[1],
                        'active_days': row[2],
                        'avg_results': round(row[3], 1),
                        'last_searched': datetime.fromisoformat(row[4]),
                        'frequency_score': row[1] / max(1, days - row[2])  # 検索頻度スコア
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            self.logger.error(f"検索トレンド取得エラー: {e}")
            raise DatabaseError(f"検索トレンドの取得に失敗しました: {e}")
    
    def get_failed_searches(self, days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        """結果が見つからなかった検索を取得
        
        Args:
            days (int): 対象期間（日数）
            limit (int): 取得する最大件数
            
        Returns:
            List[Dict[str, Any]]: 失敗した検索のリスト
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT query, search_type, COUNT(*) as failure_count,
                           MAX(timestamp) as last_attempt
                    FROM search_history
                    WHERE timestamp >= ? AND result_count = 0
                    GROUP BY query, search_type
                    ORDER BY failure_count DESC, last_attempt DESC
                    LIMIT ?
                """, (since_date, limit))
                
                return [
                    {
                        'query': row[0],
                        'search_type': SearchType(row[1]),
                        'failure_count': row[2],
                        'last_attempt': datetime.fromisoformat(row[3])
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            self.logger.error(f"失敗検索取得エラー: {e}")
            raise DatabaseError(f"失敗した検索の取得に失敗しました: {e}")
    
    def export_search_history(self, start_date: Optional[datetime] = None, 
                            end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """検索履歴をエクスポート
        
        Args:
            start_date (Optional[datetime]): 開始日時
            end_date (Optional[datetime]): 終了日時
            
        Returns:
            List[Dict[str, Any]]: エクスポートデータ
        """
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT id, query, search_type, timestamp, 
                           result_count, execution_time_ms
                    FROM search_history
                """
                params = []
                
                conditions = []
                if start_date:
                    conditions.append("timestamp >= ?")
                    params.append(start_date)
                if end_date:
                    conditions.append("timestamp <= ?")
                    params.append(end_date)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY timestamp DESC"
                
                cursor = conn.execute(query, params)
                
                return [
                    {
                        'id': row[0],
                        'query': row[1],
                        'search_type': row[2],
                        'timestamp': row[3],
                        'result_count': row[4],
                        'execution_time_ms': row[5]
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            self.logger.error(f"検索履歴エクスポートエラー: {e}")
            raise DatabaseError(f"検索履歴のエクスポートに失敗しました: {e}")