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
        
        stockCode = self._kiwoom.get_stock_kospi(symbol)
        if not stockCode:
            return {"error": f"종목 '{symbol}'을 찾을 수 없습니다."}
        
        stock_info = await self._kiwoom.get_stock_info(stockCode)
        return stock_info
    
    async def order_stock(self, symbol: str, quantity: int, price: int, orderType: str) -> Dict[str, Any]:
        """주식 주문 처리"""
        try:
            # 연결 상태 확인
            if not self._kiwoom.is_connected:
                return {"error": "키움증권 API에 연결되지 않았습니다. 먼저 로그인을 해주세요."}
            
            # 종목코드 조회
            stockCode = self._kiwoom.get_stock_kospi(symbol)
            if not stockCode:
                return {"error": f"종목 '{symbol}'을 찾을 수 없습니다."}
            
            # 계좌 정보 확인
            accountList = self._kiwoom.get_account_list()
            if not accountList:
                return {"error": "사용 가능한 계좌가 없습니다."}
            
            primaryAccount = accountList[0]
            self._logger.info(f"주문 계좌: {primaryAccount}")
            
            # 주문 실행 (동기 메서드이므로 await 제거)
            if orderType == 'buy':
                # 거래시간 확인
                current_time = datetime.now()
                is_market_open = self._kiwoom._is_market_open(current_time)

                if is_market_open.get("status") and is_market_open.get("is_open"):
                    # 장중 거래 - 지정가 주문
                    hoga_gb = "00"  # 지정가
                    screen_name = "주식매수"
                elif is_market_open.get("status") and not is_market_open.get("is_open"):
                    # 장외 거래 - 시간외 단일가 주문
                    hoga_gb = "61"  # 시간외단일가
                    screen_name = "시간외매수"
                else:
                    return {"error": "현재는 거래 시간이 아닙니다. 거래 시간 내에 주문해 주세요."}

                self._logger.info(f"거래시간 구분: {'장중' if is_market_open else '장외'}, 호가구분: {hoga_gb}")
                result = await self._kiwoom.send_order(
                    screen_name=screen_name,
                    screen_no="0101",
                    acc_no=primaryAccount,
                    order_type=1,  # 신규매수
                    code=stockCode,
                    qty=quantity,
                    price=price,
                    hoga_gb=hoga_gb,  # 지정가
                    org_order_no=""
                )
            elif orderType == 'sell':
                result = await self._kiwoom.send_order(
                    screen_name="주식매도",
                    screen_no="0102", 
                    acc_no=primaryAccount,
                    order_type=2,  # 신규매도
                    code=stockCode,
                    qty=quantity,
                    price=price,
                    hoga_gb=hoga_gb,
                    org_order_no=""
                )
            else:
                return {"error": "orderType은 'buy' 또는 'sell'이어야 합니다."}
            
            # 결과 처리
            if result.get("return_code") == 0:
                return {
                    "success": True, 
                    "message": f"{symbol} 주식 {orderType} 주문이 접수되었습니다.",
                    "orderResult": result,
                    "stockCode": stockCode,
                    "quantity": quantity,
                    "price": price
                }
            else:
                return {
                    "error": f"주문 실패 코드: {result.get('return_code')}",
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
                "체결구분": "1",  # 0: 전체, 1: 미체결, 2: 체결
                "매매구분": "0"   # 0: 전체, 1: 매도, 2: 매수
            }
            
            rawData = await self._kiwoom.request_tr("opt10075", trInputs)
            
            if not rawData:
                return {
                    "success": True,
                    "message": "진행중인 주문이 없습니다.",
                    "orders": [],
                    "totalCount": 0
                }
            
            # 미체결 주문 데이터 파싱
            pending_orders = self._parse_pending_orders(rawData)
            
            return {
                "success": True,
                "message": f"미체결 주문 {len(pending_orders)}건을 조회했습니다.",
                "orders": pending_orders,
                "totalCount": len(pending_orders),
                "accountNo": targetAccount
            }
            
        except Exception as e:
            self._logger.error(f"미체결 주문 조회 오류: {e}")
            return {"error": f"미체결 주문 조회 중 오류가 발생했습니다: {str(e)}"}
    
    def _parse_pending_orders(self, rawData: Dict[str, Any]) -> List[Dict[str, Any]]:
        """미체결 주문 데이터 파싱"""
        try:
            orders = []
            
            # rawData가 리스트 형태인지 단일 딕셔너리인지 확인
            if isinstance(rawData, dict):
                rawData = [rawData]
            
            for orderData in rawData:
                if not orderData:
                    continue
                
                # 주문 정보 파싱
                order = {
                    "주문번호": orderData.get("주문번호", ""),
                    "종목코드": orderData.get("종목코드", "").strip(),
                    "종목명": orderData.get("종목명", "").strip(),
                    "주문구분": self._getOrderTypeName(orderData.get("주문구분", "")),
                    "주문수량": self._parseInteger(orderData.get("주문수량", "0")),
                    "주문가격": self._parseInteger(orderData.get("주문가격", "0")),
                    "미체결수량": self._parseInteger(orderData.get("미체결수량", "0")),
                    "체결수량": self._parseInteger(orderData.get("체결수량", "0")),
                    "현재가": self._parseInteger(orderData.get("현재가", "0")),
                    "주문상태": orderData.get("주문상태", "").strip(),
                    "주문시간": orderData.get("주문시간", "").strip(),
                    "원주문번호": orderData.get("원주문번호", ""),
                }
                
                # 수익률 계산
                if order["주문가격"] > 0 and order["현재가"] > 0:
                    if order["주문구분"] == "매수":
                        order["수익률"] = round(((order["현재가"] - order["주문가격"]) / order["주문가격"]) * 100, 2)
                    else:  # 매도
                        order["수익률"] = round(((order["주문가격"] - order["현재가"]) / order["현재가"]) * 100, 2)
                else:
                    order["수익률"] = 0.0
                
                # 미체결 금액 계산
                order["미체결금액"] = order["미체결수량"] * order["주문가격"]
                
                orders.append(order)
            
            # 주문시간 기준 내림차순 정렬 (최신 주문이 먼저)
            orders.sort(key=lambda x: x["주문시간"], reverse=True)
            
            return orders
            
        except Exception as e:
            self._logger.error(f"미체결 주문 파싱 오류: {e}")
            return []
    
    def _getOrderTypeName(self, orderType: str) -> str:
        """주문구분 코드를 한국어명으로 변환"""
        orderTypeMap = {
            "1": "매도",
            "2": "매수", 
            "+매도": "매도",
            "+매수": "매수",
            "-매도": "매도취소",
            "-매수": "매수취소"
        }
        return orderTypeMap.get(orderType.strip(), orderType)
    
    def _parseInteger(self, value: str) -> int:
        """문자열을 정수로 안전하게 변환"""
        try:
            # 키움 API 특성: +/- 부호, 콤마 제거
            cleanValue = str(value).replace(",", "").replace("+", "").strip()
            return int(cleanValue) if cleanValue and cleanValue != "-" else 0
        except (ValueError, TypeError):
            return 0
    
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
                orderType=3,  # 취소
                code="",      # 취소시에는 종목코드 불필요
                qty=0,        # 취소시에는 수량 불필요  
                price=0,      # 취소시에는 가격 불필요
                hogaGb="00",
                orgOrderNo=orderNo  # 원주문번호
            )
            
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
                    "주문구분": self._getOrderTypeName(orderData.get("주문구분", "")),
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