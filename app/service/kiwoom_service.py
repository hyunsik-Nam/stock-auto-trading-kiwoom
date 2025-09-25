from supabase import Client
from typing import List, Optional, Dict, Any

class KiwoomService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def get_finance_service(self, limit: int = 100) -> List[Dict[str, Any]]:
        """모든 주식 데이터 조회"""
        result = self.supabase.table('financial_data').select("*").limit(limit).execute()
        return result.data
    
    def get_stock_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """심볼로 주식 조회"""
        result = self.supabase.table('financial_data').select("*").eq('symbol', symbol).execute()
        return result.data[0] if result.data else None
    
    def update_stock_price(self, symbol: str, new_price: float) -> Dict[str, Any]:
        """주식 가격 업데이트"""
        result = self.supabase.table('financial_data').update({
            'price': new_price,
            'updated_at': 'now()'
        }).eq('symbol', symbol).execute()
        return result.data[0] if result.data else None
    
    def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """주식 검색"""
        result = self.supabase.table('financial_data').select("*").ilike('name', f'%{query}%').execute()
        return result.data