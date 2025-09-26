from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from typing import List, Optional, Dict, Any
from app.database.supabase import get_supabase_client
from app.service.kiwoom_service import KiwoomService

router = APIRouter()

def get_finance_service(supabase: Client = Depends(get_supabase_client)) -> KiwoomService:
    return KiwoomService(supabase)

@router.get("/stock_info/{symbol}")
async def getStockInfo(
    symbol: str, 
    service: KiwoomService = Depends(get_finance_service)
) -> Dict[str, Any]:
    """주식 정보 조회"""
    try:
        print(f"📊 주식 정보 조회 요청: {symbol}")
        
        result = await service.get_stock_info(symbol.upper())
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"주식 정보를 찾을 수 없습니다: {symbol}"
            )
        
        return {
            "success": True,
            "data": result,
            "message": f"{symbol} 주식 정보 조회 성공"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 주식 정보 조회 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"주식 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )