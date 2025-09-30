import sys
import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QTimer
import uuid
import time
from app.utils.logging_utils import setupLogging
import datetime

logger = setupLogging()

class OrderManager:
    """주문 관리자 - 비동기 주문 처리"""
    
    def __init__(self):
        self._pending_orders: Dict[str, Dict[str, Any]] = {}
        self._order_queue: asyncio.Queue = asyncio.Queue()
        self._order_lock: asyncio.Lock = asyncio.Lock()
        self._max_concurrent_orders = 5  # 동시 처리 가능한 주문 수
        self._current_orders = 0
        
    def create_order_request(self, order_data: Dict[str, Any]) -> str:
        """주문 요청 생성"""
        order_id = f"ORDER_{uuid.uuid4().hex[:8]}"
        
        self._pending_orders[order_id] = {
            "order_id": order_id,
            "order_data": order_data,
            "timestamp": time.time(),
            "status": "pending",
            "result": None,
            "future": asyncio.Future()
        }
        
        return order_id
    
    async def submit_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """주문 제출 - 비동기 처리"""
        order_id = self.create_order_request(order_data)
        order_request = self._pending_orders[order_id]
        
        # 주문 큐에 추가
        await self._order_queue.put(order_request)
        
        # 결과 대기
        try:
            result = await order_request["future"]
            return result
        except Exception as e:
            logger.error(f"주문 처리 오류: {e}")
            return {"error": str(e), "order_id": order_id}
    
    def complete_order(self, order_id: str, result: Dict[str, Any]) -> None:
        """주문 완료 처리"""
        if order_id in self._pending_orders:
            order_request = self._pending_orders[order_id]
            order_request["status"] = "completed"
            order_request["result"] = result
            
            if not order_request["future"].done():
                order_request["future"].set_result(result)

    def fail_order(self, order_id: str, error: str) -> None:
        """주문 실패 처리"""
        if order_id in self._pending_orders:
            order_request = self._pending_orders[order_id]
            order_request["status"] = "failed"
            order_request["result"] = {"error": error}
            
            if not order_request["future"].done():
                order_request["future"].set_result({"error": error, "order_id": order_id})

class TrRequestManager:
    """TR 요청 관리자"""
    
    def __init__(self):
        self._pending_requests: Dict[str, Dict[str, Any]] = {}
        self._tr_configs: Dict[str, Dict[str, Any]] = self._init_tr_configs()
    
    def _init_tr_configs(self) -> Dict[str, Dict[str, Any]]:
        """TR 설정 초기화 - 키움 공식 문서 기준"""
        return {
            "opt10001": {
                "name": "주식기본정보",
                "inputs": ["종목코드"],
                "outputs": {
                    "종목명": str,
                    "현재가": int,
                    "기준가": int,
                    "전일종가": int,
                    "시가": int,
                    "고가": int,
                    "저가": int,
                    "상한가": int,
                    "하한가": int,
                    "전일대비": int,
                    "등락률": float,
                    "거래량": int,
                    "거래대금": int,
                    "액면가": int,
                    "시가총액": int,
                    "상장주수": int,
                    "PER": float,
                    "EPS": int,
                    "ROE": float,
                    "PBR": float,
                    "EV": float,
                    "BPS": int,
                    "매출액": int,
                    "영업이익": int,
                    "당기순이익": int,
                    "250최고": int,
                    "250최저": int,
                    "시가총액규모": str,
                    "지수업종대분류": str,
                    "지수업종중분류": str,
                    "지수업종소분류": str,
                    "제조업": str,
                    "매출액증가율": float,
                    "영업이익증가율": float,
                    "순이익증가율": float,
                    "ROE증가율": float,
                    "매출액적자": str,
                    "영업이익적자": str,
                    "순이익적자": str
                }
            }
        }
    
    def create_request(self, tr_code: str, inputs: Dict[str, str], 
                     callback: Optional[Callable] = None) -> str:
        """TR 요청 생성"""
        request_id = f"{tr_code}_{uuid.uuid4().hex[:8]}"
        
        self._pending_requests[request_id] = {
            "tr_code": tr_code,
            "inputs": inputs,
            "callback": callback,
            "timestamp": time.time(),
            "completed": False,
            "result": None
        }
        
        return request_id
    
    def complete_request(self, request_id: str, result: Dict[str, Any]) -> None:
        """요청 완료 처리"""
        if request_id in self._pending_requests:
            request = self._pending_requests[request_id]
            request["completed"] = True
            request["result"] = result
            
            if request["callback"]:
                request["callback"](result)
    
    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """요청 정보 조회"""
        return self._pending_requests.get(request_id)
    
    def parse_data(self, tr_code: str, raw_data: Dict[str, str]) -> Dict[str, Any]:
        """TR 데이터 파싱 - 키움 데이터 형식 정확히 처리"""
        config = self._tr_configs.get(tr_code, {})
        outputs = config.get("outputs", {})
        
        result = {}
        for field, data_type in outputs.items():
            raw_value = raw_data.get(field, "")
            
            try:
                if data_type == int:
                    # 키움 데이터 특성: +/- 부호 포함, 콤마 포함
                    clean_value = raw_value.replace(",", "").replace("+", "").strip()
                    result[field] = int(clean_value) if clean_value and clean_value != "-" else 0
                elif data_type == float:
                    # 퍼센트나 소수점 데이터 처리
                    clean_value = raw_value.replace("%", "").replace("+", "").strip()
                    result[field] = float(clean_value) if clean_value and clean_value != "-" else 0.0
                else:
                    result[field] = raw_value.strip()
            except (ValueError, AttributeError):
                result[field] = 0 if data_type in [int, float] else ""
        
        return result

class KiwoomComponent(QAxWidget):
    _instance: Optional['KiwoomComponent'] = None
    _initialized: bool = False
    _q_application: Optional[QApplication] = None

    def __new__(cls):
        if cls._instance is None:
            cls._initialize_q_application_class()
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def _initialize_q_application_class(cls) -> None:
        """클래스 레벨에서 QApplication 초기화"""
        if cls._q_application is None:
            app = QApplication.instance()
            if app is None:
                cls._q_application = QApplication(sys.argv)
                cls._q_application.setQuitOnLastWindowClosed(False)
                logger.info("QApplication 초기화 완료")
            else:
                cls._q_application = app

    def __init__(self):
        if not self._initialized:
            super().__init__()
            try:
                self._logger = logger
                self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
                self.OnEventConnect.connect(self._event_connect)
                self.OnReceiveTrData.connect(self._receive_tr_data)
                self.OnReceiveMsg.connect(self._receive_msg)
                self.OnReceiveChejanData.connect(self._receive_chejan_data)
                self._login_event_loop = None
                self._is_connected = False
                self._tr_manager = TrRequestManager()
                self._order_manager = OrderManager()
                self._current_request_id: Optional[str] = None
                self._request_event_loop: Optional[QEventLoop] = None
                self._timeout_timer: Optional[QTimer] = None
                self._user_info: Dict[str, str] = {}
                self._order_results: Dict[str, Dict[str, Any]] = {}
                
                # 주문 처리 워커 시작
                asyncio.create_task(self._order_processor())
                
                KiwoomComponent._initialized = True
                self._logger.info("키움 API 컨트롤 초기화 성공")
            except Exception as e:
                self._logger.error(f"키움 API 컨트롤 초기화 실패: {e}")
                raise

    async def _order_processor(self) -> None:
        """주문 처리 워커 - 백그라운드에서 주문 큐 처리"""
        while True:
            try:
                # 주문 큐에서 주문 요청 가져오기
                order_request = await self._order_manager._order_queue.get()
                
                # 동시 주문 수 제한 확인
                async with self._order_manager._order_lock:
                    if self._order_manager._current_orders >= self._order_manager._max_concurrent_orders:
                        await asyncio.sleep(0.1)  # 잠시 대기
                        continue
                    
                    self._order_manager._current_orders += 1
                
                # 주문 실행
                try:
                    result = await self._execute_order(order_request)
                    self._order_manager.complete_order(order_request["order_id"], result)
                except Exception as e:
                    self._order_manager.fail_order(order_request["order_id"], str(e))
                finally:
                    async with self._order_manager._order_lock:
                        self._order_manager._current_orders -= 1
                
            except Exception as e:
                self._logger.error(f"주문 처리 워커 오류: {e}")
                await asyncio.sleep(1)

    async def _execute_order(self, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """실제 주문 실행"""
        order_data = order_request["order_data"]
        
        try:
            # SendOrder 호출 (동기 메서드)
            ret = self.SendOrder(
                order_data["screen_name"],
                order_data["screen_no"],
                order_data["acc_no"],
                order_data["order_type"],
                order_data["code"],
                order_data["qty"],
                order_data["price"],
                order_data["hoga_gb"],
                order_data["org_order_no"]
            )
            
            if ret == 0:
                self._logger.info(f"주문 전송 성공: {order_data['code']}, {order_data['qty']}주")
                
                # 주문 결과 대기 (최대 10초)
                order_id = order_request["order_id"]
                timeout = 10
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    if order_id in self._order_results:
                        result = self._order_results[order_id]
                        del self._order_results[order_id]  # 메모리 정리
                        return {
                            "success": True,
                            "order_id": order_id,
                            "message": "주문이 성공적으로 접수되었습니다",
                            "order_result": result
                        }
                    await asyncio.sleep(0.1)
                
                # 타임아웃 시 기본 성공 응답
                return {
                    "success": True,
                    "order_id": order_id,
                    "message": "주문이 접수되었습니다 (결과 확인 중)",
                    "return_code": ret
                }
            else:
                return {
                    "success": False,
                    "error": f"주문 전송 실패 코드: {ret}",
                    "return_code": ret
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"주문 실행 오류: {str(e)}"
            }

    async def login(self) -> bool:
        """키움 API 로그인"""
        try:
            self._logger.info("키움 API 로그인 시작")
            
            if self._is_connected:
                self._logger.info("이미 로그인 상태입니다")
                return True

            self._login_event_loop = QEventLoop()
            ret = self.dynamicCall("CommConnect()")
            self._logger.info(f"CommConnect() 결과: {ret}")
            
            if ret == 0:
                self._logger.info("로그인 창 대기 중...")
                self._login_event_loop.exec_()
                return self._is_connected
            else:
                self._logger.error(f"로그인 요청 실패: {ret}")
                return False
                
        except Exception as e:
            self._logger.error(f"로그인 호출 오류: {e}")
            return False

    def _event_connect(self, err_code: int) -> None:
        """로그인 결과 이벤트 처리"""
        self._logger.info(f"로그인 결과: {err_code}")
        
        try:
            if err_code == 0:
                self._is_connected = True
                self._logger.info("로그인 성공!")
                self._collect_user_info()
            else:
                self._is_connected = False
                self._logger.error(f"로그인 실패: {err_code}")
        except Exception as e:
            self._logger.error(f"로그인 이벤트 처리 오류: {e}")
        finally:
            if self._login_event_loop:
                self._login_event_loop.exit()

    def _collect_user_info(self) -> None:
        """사용자 정보 수집"""
        try:
            self._user_info = {
                "user_name": self.dynamicCall("GetLoginInfo(QString)", "USER_NAME"),
                "user_id": self.dynamicCall("GetLoginInfo(QString)", "USER_ID"),
                "accounts": self.dynamicCall("GetLoginInfo(QString)", "ACCNO")
            }
            
            self._logger.info(f"사용자: {self._user_info['user_name']} ({self._user_info['user_id']})")
            self._logger.info(f"계좌: {self._user_info['accounts']}")
            
        except Exception as e:
            self._logger.error(f"사용자 정보 조회 오류: {e}")

    async def request_tr(self, tr_code: str, inputs: Dict[str, str], 
                       callback: Optional[Callable] = None, 
                       timeout: int = 10) -> Optional[Dict[str, Any]]:
        """범용 TR 요청 메서드"""
        try:
            if not self._is_connected:
                self._logger.error("키움 API에 로그인되지 않음")
                return None
            
            # 입력값 설정
            for key, value in inputs.items():
                self.dynamicCall("SetInputValue(QString, QString)", key, value)
            
            # 요청 생성
            self._current_request_id = self._tr_manager.create_request(tr_code, inputs, callback)
            
            # 이벤트 루프 및 타이머 설정
            self._request_event_loop = QEventLoop()
            self._timeout_timer = QTimer()
            self._timeout_timer.setSingleShot(True)
            self._timeout_timer.timeout.connect(self._on_request_timeout)
            self._timeout_timer.start(timeout * 1000)
            
            # TR 요청
            screen_no = f"{int(time.time()) % 10000:04d}"
            ret = self.dynamicCall(
                "CommRqData(QString, QString, int, QString)",
                self._current_request_id,
                tr_code,
                0,
                screen_no
            )
            
            if ret == 0:
                self._logger.info(f"{tr_code} 요청 성공, 응답 대기 중...")
                self._request_event_loop.exec_()
                
                # 타이머 정리
                if self._timeout_timer:
                    self._timeout_timer.stop()
                    self._timeout_timer = None
                
                # 결과 반환
                request = self._tr_manager.get_request(self._current_request_id)
                return request["result"] if request else None
            else:
                self._logger.error(f"{tr_code} 요청 실패: {ret}")
                return None
                
        except Exception as e:
            self._logger.error(f"TR 요청 오류: {e}")
            return None
        finally:
            self._current_request_id = None
            if self._timeout_timer:
                self._timeout_timer.stop()
                self._timeout_timer = None

    def _receive_msg(self, screen_no: str, rq_name: str, tr_code: str, msg: str) -> None:
        """주문 메시지 수신 이벤트"""
        self._logger.info(f"주문 메시지: {msg} (화면번호: {screen_no})")
        
        # 주문 결과를 대기 중인 주문에 연결
        for order_id, order_data in self._order_manager._pending_orders.items():
            if order_data["order_data"]["screen_no"] == screen_no:
                self._order_results[order_id] = {"message": msg, "screen_no": screen_no}
                break

    def _receive_chejan_data(self, gubun: str, item_cnt: int, fid_list: str) -> None:
        """체결 데이터 수신 이벤트"""
        try:
            if gubun == "0":  # 주문체결
                order_no = self.dynamicCall("GetChejanData(int)", 9203)
                stock_code = self.dynamicCall("GetChejanData(int)", 9001)
                stock_name = self.dynamicCall("GetChejanData(int)", 302)
                order_status = self.dynamicCall("GetChejanData(int)", 913)
                order_qty = self.dynamicCall("GetChejanData(int)", 900)
                order_price = self.dynamicCall("GetChejanData(int)", 901)
                
                self._logger.info(f"주문체결: {stock_name}({stock_code}) {order_status} {order_qty}주 {order_price}원")
                
        except Exception as e:
            self._logger.error(f"체결 데이터 처리 오류: {e}")

    def _on_request_timeout(self) -> None:
        """요청 타임아웃 처리"""
        self._logger.warning("TR 요청 타임아웃")
        if self._request_event_loop:
            self._request_event_loop.exit()

    def _receive_tr_data(self, screen_no, rq_name, tr_code, record_name, prev_next, data_len, err_code, msg1, msg2):
        """범용 TR 데이터 수신 처리"""
        try:
            # err_code 처리
            error_code = 0
            if isinstance(err_code, str):
                error_code = int(err_code) if err_code.strip() else 0
            else:
                error_code = int(err_code)
            
            if error_code != 0:
                self._logger.error(f"TR 에러 코드: {error_code}, 메시지: {msg1}")
                return
            
            self._logger.info(f"TR 데이터 수신: {rq_name} ({tr_code})")
            
            # 데이터 추출
            raw_data = self._extract_raw_data(tr_code, record_name)
            
            # 원시 데이터 디버깅
            self._logger.info("원시 데이터 샘플:")
            for key, value in list(raw_data.items())[:5]:
                self._logger.info(f"  {key}: '{value}'")
            
            # 데이터 파싱
            parsed_data = self._tr_manager.parse_data(tr_code, raw_data)
            
            # 요청 완료 처리
            if self._current_request_id and rq_name == self._current_request_id:
                self._tr_manager.complete_request(self._current_request_id, parsed_data)
            
            # 주요 데이터만 로깅
            if tr_code == "opt10001":
                stock_name = parsed_data.get('종목명', '')
                current_price = parsed_data.get('현재가', 0)
                change_rate = parsed_data.get('등락률', 0.0)
                self._logger.info(f"{stock_name}: {current_price:,}원 ({change_rate:+.2f}%)")
            
        except Exception as e:
            self._logger.error(f"TR 데이터 처리 오류: {e}")
        finally:
            if self._request_event_loop and self._request_event_loop.isRunning():
                self._request_event_loop.exit()

    def _extract_raw_data(self, tr_code: str, record_name: str) -> Dict[str, str]:
        """원시 데이터 추출 - 모든 가능한 필드 추출"""
        raw_data = {}
        
        # opt10001의 경우 정확한 필드명 사용
        if tr_code == "opt10001":
            field_names = [
                "종목명", "현재가", "기준가", "전일종가", "시가", "고가", "저가",
                "상한가", "하한가", "전일대비", "등락률", "거래량", "거래대금",
                "액면가", "시가총액", "상장주수", "PER", "EPS", "ROE", "PBR"
            ]
        else:
            # 다른 TR의 경우 설정에서 가져오기
            config = self._tr_manager._tr_configs.get(tr_code, {})
            field_names = list(config.get("outputs", {}).keys())
        
        actual_record_name = record_name if record_name.strip() else ""
        
        for field_name in field_names:
            try:
                value = self.dynamicCall(
                    "CommGetData(QString, QString, QString, int, QString)",
                    tr_code, "", actual_record_name, 0, field_name
                ).strip()
                raw_data[field_name] = value
                
                # 디버깅: 주요 필드 원시값 출력
                if field_name in ["종목명", "현재가", "전일대비", "등락률"]:
                    self._logger.debug(f"  원시 {field_name}: '{value}'")
                    
            except Exception as e:
                self._logger.warning(f"{field_name} 데이터 추출 실패: {e}")
                raw_data[field_name] = ""
        
        return raw_data

    # 편의 메서드들
    async def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """주식 기본정보 조회"""
        self._logger.info(f"주식 기본정보 조회: {stock_code}")
        return await self.request_tr("opt10001", {"종목코드": stock_code})

    def get_stock_kospi(self, stock: str) -> Optional[str]:
        """코스피 주식 코드 조회"""
        try:
            kospi = self.dynamicCall("GetCodeListByMarket(QString)", "0")
            codes = kospi.split(';')
            
            for code in codes:
                code = code.strip()
                if code:
                    stock_name = self.dynamicCall("GetMasterCodeName(QString)", code)
                    if stock_name == stock:
                        return code
            return None
        except Exception as e:
            self._logger.error(f"코스피 종목 조회 오류: {e}")
            return None

    async def send_order(self, screen_name: str, screen_no: str, acc_no: str, 
                        order_type: int, code: str, qty: int, price: int, 
                        hoga_gb: str, org_order_no: str) -> Dict[str, Any]:
        """비동기 주식 주문 전송"""
        try:
            if not self._is_connected:
                return {"success": False, "error": "키움 API에 로그인되지 않았습니다"}
            
            order_data = {
                "screen_name": screen_name,
                "screen_no": screen_no,
                "acc_no": acc_no,
                "order_type": order_type,
                "code": code,
                "qty": qty,
                "price": price,
                "hoga_gb": hoga_gb,
                "org_order_no": org_order_no
            }
            
            # 비동기 주문 제출
            result = await self._order_manager.submit_order(order_data)
            return result
            
        except Exception as e:
            self._logger.error(f"주문 전송 오류: {e}")
            return {"success": False, "error": str(e)}

    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected

    @property
    def user_info(self) -> Dict[str, str]:
        """사용자 정보 반환"""
        return self._user_info.copy()

    def get_account_list(self) -> List[str]:
        """계좌 목록 반환"""
        if self._user_info.get("accounts"):
            return self._user_info["accounts"].split(";")[:-1]
        return []
    
    def _is_market_open(self, current_time: Optional[time.struct_time] = None) -> Dict[str, Any]:
        """장 운영 시간 확인 - 타입 안전성 개선"""
        try:
            # 현재 시간 처리
            if current_time is None:
                now = datetime.datetime.now()
            elif isinstance(current_time, datetime.datetime):
                now = current_time
            elif isinstance(current_time, time.struct_time):
                now = datetime.datetime(*current_time[0:6])  # struct_time은 튜플처럼 인덱싱 가능
            else:
                self._logger.warning(f"예상치 못한 시간 타입: {type(current_time)}, 현재 시간 사용")
                now = datetime.datetime.now()
            
            # 주말 확인 (토요일=5, 일요일=6)
            if now.weekday() >= 5:
                return {"status": False, "message": "주말 - 장 마감", "is_open": False}
            
            # 장 운영 시간: 09:00 ~ 15:30
            marketOpen = now.replace(hour=9, minute=0, second=0, microsecond=0)
            marketClose = now.replace(hour=15, minute=30, second=0, microsecond=0)

            return {"status": True, "message": "장 운영 중", "is_open": marketOpen <= now <= marketClose}

        except Exception as e:
            self._logger.error(f"장 운영 시간 확인 오류: {e}")
            # 오류 발생시 현재 시간 기준으로 재시도
            return self._isMarketOpen(None)

    def _get_market_status(self) -> Dict[str, Any]:
        """상세한 장 상태 정보 반환"""
        
        now = datetime.datetime.now()
        
        # 기본 상태 정보
        status = {
            "is_open": False,
            "is_weekend": now.weekday() >= 5,
            "current_time": now.strftime("%H:%M:%S"),
            "status_message": "",
            "next_open_time": None,
            "next_close_time": None
        }
        
        if status["is_weekend"]:
            status["status_message"] = "주말 - 장 마감"
            # 다음 월요일 09:00
            days_until_monday = 7 - now.weekday()
            next_monday = now + datetime.timedelta(days=days_until_monday)
            status["next_open_time"] = next_monday.replace(hour=9, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
            return status
        
        # 장 운영 시간 설정
        market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        pre_market = now.replace(hour=8, minute=0, second=0, microsecond=0)
        after_market = now.replace(hour=18, minute=0, second=0, microsecond=0)
        
        if now < pre_market:
            status["status_message"] = "장전 시간"
            status["next_open_time"] = market_open.strftime("%Y-%m-%d %H:%M:%S")
        elif pre_market <= now < market_open:
            status["status_message"] = "장전 준비시간"
            status["next_open_time"] = market_open.strftime("%Y-%m-%d %H:%M:%S")
        elif market_open <= now <= market_close:
            status["is_open"] = True
            status["status_message"] = "정규장 운영중"
            status["next_close_time"] = market_close.strftime("%Y-%m-%d %H:%M:%S")
        elif market_close < now <= after_market:
            status["status_message"] = "장후 시간"
            # 다음 거래일 09:00
            next_day = now + datetime.timedelta(days=1)
            if next_day.weekday() >= 5:  # 금요일 다음날이면 월요일로
                days_to_add = 7 - next_day.weekday()
                next_day = next_day + datetime.timedelta(days=days_to_add)
            status["next_open_time"] = next_day.replace(hour=9, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        else:
            status["status_message"] = "장 마감"
            # 다음 거래일 09:00
            next_day = now + datetime.timedelta(days=1)
            if next_day.weekday() >= 5:
                days_to_add = 7 - next_day.weekday()
                next_day = next_day + datetime.timedelta(days=days_to_add)
            status["next_open_time"] = next_day.replace(hour=9, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        
        return status

    def check_market_operation(self) -> bool:
        """키움 API를 통한 실제 장 운영 상태 확인"""
        try:
            if not self._is_connected:
                self._logger.warning("키움 API 미연결 상태 - 시간 기반 판단 사용")
                return self._is_market_open()
            
            # 키움 API 장 운영 상태 조회 (GetCodeListByMarket 응답으로 간접 확인)
            kospi_codes = self.dynamicCall("GetCodeListByMarket(QString)", "0")
            
            if kospi_codes and len(kospi_codes.split(';')) > 100:
                # 코드 리스트가 정상적으로 조회되면 API가 활성 상태
                time_based_status = self._is_market_open()
                market_status = self._get_market_status()
                
                self._logger.info(f"장 운영 상태: {market_status['status_message']} ({market_status['current_time']})")
                return time_based_status
            else:
                self._logger.warning("키움 API 응답 이상 - 시간 기반 판단 사용")
                return self._is_market_open()
                
        except Exception as e:
            self._logger.error(f"장 운영 상태 확인 오류: {e}")
            return self._is_market_open()
# 싱글톤 인스턴스 생성
kiwoom_component = KiwoomComponent()