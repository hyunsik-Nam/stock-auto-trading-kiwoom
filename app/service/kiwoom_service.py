from supabase import Client
from typing import List, Optional, Dict, Any
from app.components.kiwoom_component import kiwoom_component, KiwoomComponent

from app.utils.logging_utils import setupLogging

from datetime import datetime, timedelta
from datetime import datetime

logger = setupLogging()
class KiwoomService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self._kiwoom: KiwoomComponent = kiwoom_component
        self._logger = logger

    async def get_stock_info(self, symbol) -> List[Dict[str, Any]]:
        """주식 데이터 조회"""
        if not self._kiwoom.is_connected:
            return {"error": "키움증권 API에 연결되지 않았습니다. 먼저 로그인을 해주세요."}
        
        stock_code = self._kiwoom.get_stock_kospi(symbol)
        if not stock_code:
            return {"error": f"종목 '{symbol}'을 찾을 수 없습니다."}
        
        stock_info = await self._kiwoom.get_stock_info(stock_code)
        return stock_info
    
    async def order_stock(self, screen_name: str, symbol: str, quantity: int, price: int, order_type: int, hoga_gb: str, s_org_order_no: str) -> Dict[str, Any]:
        """주식 주문 처리"""
        try:
            # 연결 상태 확인
            if not self._kiwoom.is_connected:
                return {"error": "키움증권 API에 연결되지 않았습니다. 먼저 로그인을 해주세요."}
            
            # 종목코드 조회
            stock_code = self._kiwoom.get_stock_kospi(symbol)
            if not stock_code:
                return {"error": f"종목 '{symbol}'을 찾을 수 없습니다."}
            
            # 계좌 정보 확인
            accountList = self._kiwoom.get_account_list()
            if not accountList:
                return {"error": "사용 가능한 계좌가 없습니다."}
            
            primary_account = accountList[0]
            self._logger.info(f"주문 계좌: {primary_account}")
            
            # 주문 실행 (동기 메서드이므로 await 제거)
                # 거래시간 확인
            current_time = datetime.now()
            is_market_open = self._kiwoom._is_market_open(current_time)

            # if is_market_open.get("status") and is_market_open.get("is_open"):
            #     # 장중 거래 - 지정가 주문
            #     if hoga_gb != "00":
            #         return {"error": "시간외 거래는 불가능합니다."}
            # elif is_market_open.get("status") and not is_market_open.get("is_open"):
            #     # 장외 거래 - 시간외 단일가 주문
            #     if hoga_gb != "61":
            #         return {"error": "장중 거래 시간입니다."}

            #     screen_name = f"시간외{screen_name}"
            # else:
            #     return {"error": "현재는 거래 시간이 아닙니다. 거래 시간 내에 주문해 주세요."}

            self._logger.info(f"거래시간 구분: {'장중' if is_market_open else '장외'}, 호가구분: {hoga_gb}")
            result = await self._kiwoom.send_order(
                screen_name=screen_name,
                acc_no=primary_account,
                order_type=order_type, 
                code=stock_code,
                qty=quantity,
                price=price,
                hoga_gb=hoga_gb,  # 지정가
                org_order_no=s_org_order_no
            )

            self._logger.info(f"주문 결과: {result}")
            # else:
            #     return {"error": "order_type은 'buy' 또는 'sell'이어야 합니다."}
            
            # 결과 처리
            if result.get("success", True):
                return {
                    "success": True, 
                    "message": result.get("message"),
                    "orderResult": result,
                    "stock_code": stock_code,
                    "quantity": quantity,
                    "price": price
                }
            else:
                return {
                    "error": f"주문 실패 ",
                    "orderResult": result
                }
        
        except TypeError as e:
            self._logger.error(f"메서드 호출 오류: {e}")
            return {"error": f"메서드 호출 중 오류가 발생했습니다: {str(e)}"}
        except AttributeError as e:
            self._logger.error(f"속성 접근 오류: {e}")
            return {"error": f"키움 API 메서드 접근 중 오류가 발생했습니다: {str(e)}"}
        except Exception as e:
            self._logger.error(f"주식 주문 오류: {e}")
            return {"error": f"주식 주문 중 오류가 발생했습니다: {str(e)}"}

    async def get_pending_orders(self, accountNo: Optional[str] = None) -> Dict[str, Any]:
        """진행중인 주문 내역 조회"""
        try:
            # 연결 상태 확인
            if not self._kiwoom.is_connected:
                return {"error": "키움증권 API에 연결되지 않았습니다. 먼저 로그인을 해주세요."}
            
            # 계좌 정보 확인
            accountList = self._kiwoom.get_account_list()
            if not accountList:
                return {"error": "사용 가능한 계좌가 없습니다."}
            
            # 계좌번호 설정 (미지정시 첫 번째 계좌 사용)
            targetAccount = accountNo if accountNo else accountList[0]
            if targetAccount not in accountList:
                return {"error": f"유효하지 않은 계좌번호입니다: {targetAccount}"}
            
            self._logger.info(f"미체결 주문 조회 계좌: {targetAccount}")
            
            # opt10075 TR 요청 (실시간 미체결 요청)
            trInputs = {
                "계좌번호": targetAccount,
                "종목구분": "0",
                "매매구분": "0",   # 0: 전체, 1: 매도, 2: 매수
                "종목코드" : "",
                "체결구분": "1",  # 0: 전체, 1: 미체결, 2: 체결
                "거래소구분": "0"
            }
            
            rawData = await self._kiwoom.request_tr("opt10075", trInputs)
            
            self._logger.info(f"미체결 주문 rawData: {rawData}")

            if not rawData:
                return {
                    "success": True,
                    "message": "진행중인 주문이 없습니다.",
                    "orders": [],
                    "totalCount": 0
                }
            
            return {
                "success": True,
                "message": f"미체결 주문 {len(rawData)}건을 조회했습니다.",
                "orders": rawData,
                "totalCount": len(rawData),
                "accountNo": targetAccount
            }
            
        except Exception as e:
            self._logger.error(f"미체결 주문 조회 오류: {e}")
            return {"error": f"미체결 주문 조회 중 오류가 발생했습니다: {str(e)}"}
    
    async def cancel_order(self, orderNo: str, accountNo: Optional[str] = None) -> Dict[str, Any]:
        """주문 취소"""
        try:
            # 연결 상태 확인
            if not self._kiwoom.is_connected:
                return {"error": "키움증권 API에 연결되지 않았습니다."}
            
            # 계좌 정보 확인
            account_list = self._kiwoom.get_account_list()
            if not account_list:
                return {"error": "사용 가능한 계좌가 없습니다."}

            target_account = accountNo if accountNo else account_list[0]

            # 주문 취소 실행
            result = await self._kiwoom.send_order(
                screenName="주문취소",
                screenNo="0103",
                accNo=target_account,
                order_type=3,  # 취소
                code="",      # 취소시에는 종목코드 불필요
                qty=0,        # 취소시에는 수량 불필요  
                price=0,      # 취소시에는 가격 불필요
                hogaGb="00",
                orgOrderNo=orderNo  # 원주문번호
            )

            self._logger.info(f"주문 취소 결과: {result}")

            if result.get("success", False):
                return {
                    "success": True,
                    "message": f"주문번호 {orderNo}가 취소 요청되었습니다.",
                    "orderNo": orderNo
                }
            else:
                return {
                    "error": f"주문 취소 실패: {result.get('error', '알 수 없는 오류')}",
                    "orderNo": orderNo
                }
                
        except Exception as e:
            self._logger.error(f"주문 취소 오류: {e}")
            return {"error": f"주문 취소 중 오류가 발생했습니다: {str(e)}"}
    
    async def getOrderHistory(self, accountNo: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """주문 체결 내역 조회 (최근 N일)"""
        try:
            # 연결 상태 확인
            if not self._kiwoom.is_connected:
                return {"error": "키움증권 API에 연결되지 않았습니다."}
            
            # 계좌 정보 확인  
            accountList = self._kiwoom.getAccountList()
            if not accountList:
                return {"error": "사용 가능한 계좌가 없습니다."}
            
            targetAccount = accountNo if accountNo else accountList[0]
            
            # 날짜 계산 (YYYYMMDD 형식)
            endDate = datetime.now().strftime("%Y%m%d")
            startDate = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            
            # opt10076 TR 요청 (계좌별 체결내역)
            trInputs = {
                "계좌번호": targetAccount,
                "시작일자": startDate,
                "종료일자": endDate,
                "매매구분": "0"  # 0: 전체, 1: 매도, 2: 매수
            }
            
            rawData = await self._kiwoom.requestTr("opt10076", trInputs)
            
            if not rawData:
                return {
                    "success": True,
                    "message": f"최근 {days}일간 체결 내역이 없습니다.",
                    "orders": [],
                    "totalCount": 0
                }
            
            # 체결 내역 데이터 파싱
            orderHistory = self._parseOrderHistory(rawData)
            
            return {
                "success": True,
                "message": f"최근 {days}일간 체결 내역 {len(orderHistory)}건을 조회했습니다.",
                "orders": orderHistory,
                "totalCount": len(orderHistory),
                "period": f"{startDate} ~ {endDate}",
                "accountNo": targetAccount
            }
            
        except Exception as e:
            self._logger.error(f"주문 체결 내역 조회 오류: {e}")
            return {"error": f"주문 체결 내역 조회 중 오류가 발생했습니다: {str(e)}"}
    
    def _parseOrderHistory(self, rawData: Dict[str, Any]) -> List[Dict[str, Any]]:
        """주문 체결 내역 데이터 파싱"""
        try:
            orders = []
            
            if isinstance(rawData, dict):
                rawData = [rawData]
            
            for orderData in rawData:
                if not orderData:
                    continue
                
                order = {
                    "체결번호": orderData.get("체결번호", ""),
                    "주문번호": orderData.get("주문번호", ""),
                    "종목코드": orderData.get("종목코드", "").strip(),
                    "종목명": orderData.get("종목명", "").strip(),
                    "주문구분": self._getorder_typeName(orderData.get("주문구분", "")),
                    "체결수량": self._parseInteger(orderData.get("체결수량", "0")),
                    "체결가격": self._parseInteger(orderData.get("체결가격", "0")),
                    "체결금액": self._parseInteger(orderData.get("체결금액", "0")),
                    "체결시간": orderData.get("체결시간", "").strip(),
                    "체결일자": orderData.get("체결일자", "").strip(),
                    "수수료": self._parseInteger(orderData.get("수수료", "0")),
                    "세금": self._parseInteger(orderData.get("세금", "0"))
                }
                
                # 실제 수익 계산 (수수료, 세금 포함)
                order["실수익"] = order["체결금액"] - order["수수료"] - order["세금"]
                
                orders.append(order)
            
            # 체결시간 기준 내림차순 정렬
            orders.sort(key=lambda x: f"{x['체결일자']} {x['체결시간']}", reverse=True)
            
            return orders
            
        except Exception as e:
            self._logger.error(f"주문 체결 내역 파싱 오류: {e}")
            return []