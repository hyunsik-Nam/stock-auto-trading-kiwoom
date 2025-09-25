from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from typing import List
from app.database.supabase import get_supabase_client
from app.service.kiwoom_service import KiwoomService

router = APIRouter()

def get_finance_service(supabase: Client = Depends(get_supabase_client)) -> KiwoomService:
    return KiwoomService(supabase)

@router.put("/stocks/{symbol}/price")
def update_stock_price(
    symbol: str,
    new_price: float,
    service: KiwoomService = Depends(get_finance_service)
):
    """주식 가격 업데이트"""
    result = service.update_stock_price(symbol.upper(), new_price)
    if not result:
        raise HTTPException(status_code=404, detail="주식을 찾을 수 없습니다")
    return result

@router.get("/stocks/search/")
def search_stocks(
    q: str,
    service: KiwoomService = Depends(get_finance_service)
):
    """주식 검색"""
    return service.search_stocks(q)