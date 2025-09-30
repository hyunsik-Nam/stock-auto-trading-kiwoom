from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from typing import List, Optional, Dict, Any
from app.database.supabase import get_supabase_client
from app.service.kiwoom_service import KiwoomService
from app.utils.logging_utils import setupLogging, safePrint

logger = setupLogging()
router = APIRouter()

def get_finance_service(supabase: Client = Depends(get_supabase_client)) -> KiwoomService:
    return KiwoomService(supabase)

@router.get("/stock_info/{symbol}")
async def get_stock_info(
    symbol: str, 
    service: KiwoomService = Depends(get_finance_service)
) -> Dict[str, Any]:
    """주식 정보 조회"""
    try:
        logger.info(f"📊 주식 정보 조회 요청: {symbol}")
        
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
        logger.info(f"❌ 주식 정보 조회 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"주식 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )
    
@router.post("/order")
async def order_stock(
    symbol: str, 
    quantity: int, 
    price: float, 
    order_type: str,  # 'buy' or 'sell'
    service: KiwoomService = Depends(get_finance_service)
) -> Dict[str, Any]:
    """주식 주문 처리"""
    try:
        logger.info(f"📡 주식 주문 요청: {order_type} {quantity} {symbol} at {price}")
        
        order_result = await service.order_stock(
            symbol,
            quantity,
            price,
            order_type
        )

        if "error" in order_result:
            raise HTTPException(
                status_code=400,
                detail=order_result["error"]
            )
        
        logger.info(f"✅ 주식 주문 성공: {order_result}")
        
        return {
            "success": True,
            "data": order_result,
            "message": f"{symbol} 주식 {order_type} 주문이 성공적으로 접수되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주식 주문 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"주식 주문 중 오류가 발생했습니다: {str(e)}"
)

@router.get("/pending_orders")
async def get_pending_orders(
    service: KiwoomService = Depends(get_finance_service)
) -> Dict[str, Any]:
    """미체결 주문 조회"""
    try:
        logger.info("📋 미체결 주문 조회 요청")
        
        orders = await service.get_pending_orders()
        
        return {
            "success": True,
            "data": orders,
            "message": "미체결 주문 조회 성공"
        }
        
    except Exception as e:
        logger.error(f"❌ 미체결 주문 조회 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"미체결 주문 조회 중 오류가 발생했습니다: {str(e)}"
        )
    
@router.post("/cancel_order")
async def cancel_order(
    orderNo: str,
    accountNo: Optional[str] = None,
    service: KiwoomService = Depends(get_finance_service)
) -> Dict[str, Any]:
    """주문 취소 처리"""
    try:
        logger.info(f"🛑 주문 취소 요청: {orderNo}")
        
        cancel_result = await service.cancel_order(orderNo, accountNo)
        
        if "error" in cancel_result:
            raise HTTPException(
                status_code=400,
                detail=cancel_result["error"]
            )
        
        logger.info(f"✅ 주문 취소 성공: {cancel_result}")
        
        return {
            "success": True,
            "data": cancel_result,
            "message": f"주문 {orderNo} 취소가 성공적으로 접수되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주문 취소 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"주문 취소 중 오류가 발생했습니다: {str(e)}"
        )