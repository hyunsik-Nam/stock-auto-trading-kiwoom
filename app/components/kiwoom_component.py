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
        self._screen_counter = 2000
        # self._order_queue: asyncio.Queue = asyncio.Queue()
        # self._order_lock: asyncio.Lock = asyncio.Lock()
        # self._max_concurrent_orders = 5  # 동시 처리 가능한 주문 수
        # self._current_orders = 0
        
    def create_order_request(self, code: str) -> Dict[str, Any]:
        """주문 요청 생성"""
        order_id = f"ORDER_{uuid.uuid4().hex[:8]}"
        
                # 고유 스크린 번호 생성
        screen_no = str(self._screen_counter)

        self._screen_counter += 1
        if self._screen_counter > 9999:
            self._screen_counter = 2000

        return {
            "order_id": order_id,
            "screen_no": screen_no,
            "code": code,
            "timestamp": time.time(),
            "event_loop": QEventLoop(),
            "timeout_timer": QTimer(),
            "status": "pending",
            "completed": False,
            "result": None
        }
    
    # async def submit_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
    #     """주문 제출 - 비동기 처리"""
    #     order_id = self.create_order_request(order_data)
    #     order_request = self._pending_orders[order_id]
    #     logger.info(f"주문 요청 생성: {order_id} - {order_data}")
    #     # 주문 큐에 추가
    #     await self._order_queue.put(order_request)
        
    #     logger.info(f"주문 큐에 추가됨: {order_id}")
    #     # 결과 대기
    #     try:
    #         result = await order_request["future"]
    #         logger.info(f"주문 처리 완료: {order_id} - {result}")
    #         return result
    #     except Exception as e:
    #         logger.error(f"주문 처리 오류: {e}")
    #         return {"error": str(e), "order_id": order_id}
    
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
        self._screen_counter = 1000
    
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
            },
            "opt10075": {
            "name": "미체결요청",
            "inputs": ["계좌번호", "체결구분", "매매구분"],
            "outputs": {
                "계좌번호": str,
                "주문번호": str,
                "종목코드": str,
                "주문상태": str,
                "종목명": str,
                "업무구분": str,
                "주문구분": str,
                "주문가격": int,
                "주문수량": int,
                "시간": str,
                "미체결수량": int,
                "체결가": int,
                "체결량": int,
                "현재가": int,
                "매매구분": str,
                "단위체결가": int,
                "단위체결량": int,
            }
            },
        }
    
    def create_request(self, request_id: str,tr_code: str, inputs: Dict[str, str], 
                     callback: Optional[Callable] = None) -> str:
        """TR 요청 생성"""
        
        request_id = f"{tr_code}_{uuid.uuid4().hex[:8]}"

        # 고유 스크린 번호 생성
        screen_no = str(self._screen_counter)

        self._screen_counter += 1
        if self._screen_counter > 9999:
            self._screen_counter = 1000

        return {
            "request_id": request_id,
            "tr_code": tr_code,
            "screen_no": screen_no,
            "inputs": inputs,
            "callback": callback,
            "timestamp": time.time(),
            "event_loop": QEventLoop(),
            "timeout_timer": QTimer(),
            "completed": False,
            "result": None
        }
    
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
                self._pending_tr_requests: Dict[str, Dict[str, Any]] = {}  # 요청 매핑 테이블 추가
                self._pending_orders: Dict[str, Dict[str, Any]] = {}  # 주문 매핑 테이블 추가
                
                # 주문 처리 워커 시작
                # asyncio.create_task(self._order_processor())
                
                KiwoomComponent._initialized = True
                logger.info("키움 API 컨트롤 초기화 성공")
            except Exception as e:
                logger.error(f"키움 API 컨트롤 초기화 실패: {e}")
                raise


    def _get_error_message(self, error_code: int) -> str:
        """키움 API 에러 코드를 한국어 메시지로 변환"""
        error_messages = {
            -200: "시세조회 과부하",
            -201: "REQUEST_INPUT_st Failed", 
            -202: "시세조회 초과 200회",
            -203: "주문조회 초과",
            -300: "주문전송 실패",
            -301: "계좌비밀번호 없음",
            -302: "타이틀 없음",
            -308: "주문전송 과부하"
        }
        return error_messages.get(error_code, f"알 수 없는 오류 (코드: {error_code})")
    
    def login(self) -> bool:
        """키움 API 로그인"""
        try:
            logger.info("키움 API 로그인 시작")
            
            if self._is_connected:
                logger.info("이미 로그인 상태입니다")
                return True

            self._login_event_loop = QEventLoop()
            ret = self.dynamicCall("CommConnect()")
            logger.info(f"CommConnect() 결과: {ret}")
            
            if ret == 0:
                logger.info("로그인 창 대기 중...")
                self._login_event_loop.exec_()
                return self._is_connected
            else:
                logger.error(f"로그인 요청 실패: {ret}")
                return False
                
        except Exception as e:
            logger.error(f"로그인 호출 오류: {e}")
            return False

    def _event_connect(self, err_code: int) -> None:
        """로그인 결과 이벤트 처리"""
        logger.info(f"로그인 결과: {err_code}")
        
        try:
            if err_code == 0:
                self._is_connected = True
                logger.info("로그인 성공!")
                self._collect_user_info()
            else:
                self._is_connected = False
                logger.error(f"로그인 실패: {err_code}")
        except Exception as e:
            logger.error(f"로그인 이벤트 처리 오류: {e}")
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
            
            logger.info(f"사용자: {self._user_info['user_name']} ({self._user_info['user_id']})")
            logger.info(f"계좌: {self._user_info['accounts']}")
            
        except Exception as e:
            logger.error(f"사용자 정보 조회 오류: {e}")

    async def request_tr(self, tr_code: str, inputs: Dict[str, str], 
                       callback: Optional[Callable] = None, 
                       timeout: int = 10) -> Optional[Dict[str, Any]]:
        """개선된 TR 요청 메서드 - 고유 식별자 사용"""
        try:
            if not self._is_connected:
                logger.error("키움 API에 로그인되지 않음")
                return None
            
            # 입력값 설정
            for key, value in inputs.items():
                self.dynamicCall("SetInputValue(QString, QString)", key, value)
            
            
            # 요청 정보 저장
            request_info = self._tr_manager.create_request(tr_code, inputs, callback)

            # 요청 매핑 테이블에 저장
            self._pending_tr_requests[request_info.get("request_id")] = request_info
            
            # 타이머 설정
            request_info["timeout_timer"].setSingleShot(True)
            request_info["timeout_timer"].timeout.connect(
                lambda: self._handle_tr_timeout(request_info.get("request_id"))
            )
            request_info["timeout_timer"].start(timeout * 1000)
            
            # TR 요청 전송
            ret = self.dynamicCall(
                "CommRqData(QString, QString, int, QString)",
                request_info.get("request_id"),  # 고유 요청 ID 사용
                tr_code,
                "0",
                request_info.get("screen_no")
            )
            
            if ret == 0:
                logger.info(f"{tr_code} 요청 전송 성공: {request_info.get('request_id')}")
                
                # 이벤트 루프에서 대기
                request_info["event_loop"].exec_()
                
                # 결과 반환
                result = request_info.get("result")
                self._cleanup_tr_request(request_info.get("request_id"))
                return result
            else:
                logger.error(f"{tr_code} 요청 실패: {ret}")
                self._cleanup_tr_request(request_info.get("request_id"))
                return None
                
        except Exception as e:
            logger.error(f"TR 요청 오류: {e}")
            if 'request_info' in locals():
                self._cleanup_tr_request(request_info.get("request_id"))
            return None



    def _on_request_timeout(self) -> None:
        """요청 타임아웃 처리"""
        logger.warning("TR 요청 타임아웃")
        if self._request_event_loop:
            self._request_event_loop.exit()

    def _receive_tr_data(self, screen_no, rq_name, tr_code, record_name, prev_next, data_len, err_code, msg1, msg2):
        """개선된 TR 데이터 수신 처리 - 고유 ID 매핑"""
        try:
            # 요청 매핑 테이블에서 해당 요청 찾기
            request_info = self._pending_tr_requests.get(rq_name)

            if not request_info:
                logger.warning(f"매핑되지 않은 TR 응답: {rq_name}")
                return
            
            # 이미 완료된 요청인지 확인
            if request_info["completed"]:
                logger.warning(f"이미 완료된 요청의 중복 응답: {rq_name}")
                return
            
            # 에러 코드 확인
            error_code = int(err_code) if isinstance(err_code, str) and err_code.strip() else int(err_code or 0)
            
            if error_code != 0:
                logger.error(f"TR 에러 - 요청: {rq_name}, 코드: {error_code}, 메시지: {msg1}")
                request_info["result"] = {"error": f"TR 에러: {error_code} - {msg1}"}
            else:
                # 데이터 추출 및 파싱
                raw_data = self._extract_raw_data(tr_code, record_name or "")
                
                request_info["result"] = raw_data
                logger.info(f"TR 데이터 처리 완료: {rq_name}")
            
            # 요청 완료 처리
            request_info["completed"] = True
            
            # 콜백 실행
            if request_info["callback"]:
                try:
                    request_info["callback"](request_info["result"])
                except Exception as e:
                    logger.error(f"콜백 실행 오류: {e}")
            
            # 이벤트 루프 종료
            if request_info["event_loop"].isRunning():
                request_info["event_loop"].exit()
                
        except Exception as e:
            logger.error(f"TR 데이터 처리 오류: {e}")
            # 에러 발생 시에도 이벤트 루프 종료
            if rq_name in self._pending_tr_requests:
                request_info = self._pending_tr_requests[rq_name]
                if request_info["event_loop"].isRunning():
                    request_info["event_loop"].exit()

    def _handle_tr_timeout(self, request_id: str) -> None:
        """TR 요청 타임아웃 처리"""
        logger.warning(f"TR 요청 타임아웃: {request_id}")
        
        request_info = self._pending_tr_requests.get(request_id)
        if request_info and not request_info["completed"]:
            request_info["result"] = {"error": "요청 타임아웃"}
            request_info["completed"] = True
            
            if request_info["event_loop"].isRunning():
                request_info["event_loop"].exit()
    
    def _cleanup_tr_request(self, request_id: str) -> None:
        """TR 요청 정리"""
        request_info = self._pending_tr_requests.get(request_id)
        if request_info:
            # 타이머 정리
            if request_info["timeout_timer"]:
                request_info["timeout_timer"].stop()
            
            # 매핑 테이블에서 제거
            del self._pending_tr_requests[request_id]
            logger.debug(f"TR 요청 정리 완료: {request_id}")

    def _extract_raw_data(self, tr_code: str, record_name: str) -> Dict[str, str]:
        """원시 데이터 추출 - 모든 가능한 필드 추출"""
        raw_data = []
        
        config = self._tr_manager._tr_configs.get(tr_code, {})
        logger.info(f"config {config}")
        field_names = list(config.get("outputs", {}).keys())
        
        nCnt = self.dynamicCall("GetRepeatCnt(QString, QString)", tr_code, "");
        logger.info(f"nCnt : {nCnt}")

        for i in range(max(1, nCnt)):
            for field_name in field_names:
                try:
                    value = self.dynamicCall(
                        "GetCommData(QString, QString, int, QString)",
                        str(tr_code),
                        str(record_name) if record_name else "", 
                        int(i), 
                        str(field_name)
                    )
                    logger.info(f"field_name : {field_name}, tr_code : {tr_code}, record_name : {record_name}")
                    logger.info(f"value : {value}")
                        # None 체크 및 문자열 정제
                    clean_value = value.strip() if value else ""

                    # 배열 형태로 데이터 구성
                    while len(raw_data) <= i:
                        raw_data.append({})

                    raw_data[i][field_name] = clean_value
                        
                except Exception as e:
                    logger.warning(f"{field_name} 데이터 추출 실패: {e}")
                    raw_data[f"{field_name}_{i}"] = ""

        return raw_data

    # 편의 메서드들
    async def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """주식 기본정보 조회"""
        logger.info(f"주식 기본정보 조회: {stock_code}")
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
            logger.error(f"코스피 종목 조회 오류: {e}")
            return None



    def send_order_sync(self, screen_name: str, acc_no: str, 
                       order_type: int, code: str, qty: int, price: int, 
                       hoga_gb: str, org_order_no: str, timeout: int = 10) -> Dict[str, Any]:
        """동기식 주문 전송 - QEventLoop로 결과 대기"""
        try:
            if not self._is_connected:
                return {"success": False, "error": "키움 API에 로그인되지 않았습니다"}

            # 주문 매핑 정보 저장
            order_mapping = self._order_manager.create_order_request(code)
            
            logger.info(f"order_mapping {order_mapping}")
            logger.info(f"order_mapping {order_mapping.get('order_id')}")
            logger.info(f"order_mapping {order_mapping['order_id']}")
            self._pending_orders[order_mapping.get('order_id')] = order_mapping
            
            # 타임아웃 설정
            order_mapping.get('timeout_timer').setSingleShot(True)
            order_mapping.get('timeout_timer').timeout.connect(lambda: self._handle_order_timeout(order_mapping.get('order_id')))
            order_mapping.get('timeout_timer').start(timeout * 1000)

            logger.info(f"주문 전송: {code} {qty}주, 주문ID: {order_mapping.get('order_id')}")

            logger.info(f"screen_name: {screen_name}, screen_no: {order_mapping.get('screen_no')}, acc_no: {acc_no}, order_type: {order_type}, code: {code}, qty: {qty}, price: {price}, hoga_gb: {hoga_gb}, org_order_no: {org_order_no}")
            # SendOrder 호출
            ret = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)", 
                [screen_name, order_mapping.get('screen_no'), acc_no, order_type, code, qty, price, hoga_gb, org_order_no]
            )
            logger.info(f"ret {ret}")
            
            if ret == 0:
                logger.info(f"주문 전송 성공 - 결과 대기 중: {order_mapping.get('order_id')}")
                
                # QEventLoop로 결과 대기
                order_mapping['event_loop'].exec_()

                logger.info(f"이벤트루프 종료")

                # 결과 반환
                logger.info(f"order_mapping {order_mapping}")
                result = order_mapping.get("result", {"error": "결과 없음"})
                self._cleanup_order_request(order_mapping.get('order_id'))
                return result
                
            else:
                error_msg = self._get_error_message(ret)
                self._cleanup_order_request(order_mapping.get('order_id'))
                return {
                    "success": False,
                    "error": f"주문 전송 실패: {error_msg} (코드: {ret})",
                    "return_code": ret
                }
                
        except Exception as e:
            logger.error(f"주문 전송 오류: {e}")
            if 'order_mapping' in locals():
                self._cleanup_order_request(order_mapping.get('order_id'))
            return {"success": False, "error": str(e)}
        
    def _receive_msg(self, screen_no: str, rq_name: str, tr_code: str, msg: str) -> None:
        """주문 메시지 수신 - QEventLoop 종료 처리"""
        logger.info(f"📨 주문 메시지: {msg} (화면번호: {screen_no})")
        logger.info(f"_pending_orders: {self._pending_orders}")
        

        # 해당 화면번호의 주문 찾기
        for order_id, order_info in self._pending_orders.items():
            if (order_info.get("screen_no") == screen_no and 
                not order_info.get("completed", False)):

                logger.info("@@2")
                # 결과 저장
                result = {
                    "success": True,
                    "order_id": order_id,
                    "type": "message",
                    "message": msg,
                    "screen_no": screen_no,
                    "timestamp": time.time()
                }
                order_info["result"] = result
                order_info["completed"] = True
                
                # QEventLoop 종료
                event_loop = order_info["event_loop"]
                if event_loop and event_loop.isRunning():
                    event_loop.exit()
                    logger.info(f"✅ 주문 메시지 수신 완료: {order_id}")
                
                break

    def _receive_chejan_data(self, gubun: str, item_cnt: int, fid_list: str) -> None:
        """체결 데이터 수신 - QEventLoop 종료 처리"""
        try:
            logger.info(f"🔥 체결 데이터 수신! 구분: {gubun}")
            
            if gubun == "0":  # 주문체결
                # 체결 데이터 추출
                order_no = self._safe_get_chejan_data(9203, "주문번호")
                stock_code = self._safe_get_chejan_data(9001, "종목코드")
                stock_name = self._safe_get_chejan_data(302, "종목명")
                order_status = self._safe_get_chejan_data(913, "주문상태")
                order_qty = self._safe_get_chejan_data(900, "주문수량")
                order_price = self._safe_get_chejan_data(901, "주문가격")
                exec_qty = self._safe_get_chejan_data(911, "체결수량")
                exec_price = self._safe_get_chejan_data(910, "체결가")
                
                logger.info(f"체결 정보: {stock_name}({stock_code}) {order_status} {exec_qty}주 @ {exec_price}원")
                
                # 해당 종목의 주문 찾기
                for order_id, order_info in self._pending_orders.items():
                    if (order_info.get("code") == stock_code and 
                        not order_info.get("completed", False)):
                        
                        # 체결 결과 저장
                        result = {
                            "success": True,
                            "order_id": order_id,
                            "type": "chejan",
                            "order_no": order_no,
                            "stock_code": stock_code,
                            "stock_name": stock_name,
                            "order_status": order_status,
                            "order_qty": order_qty,
                            "order_price": order_price,
                            "exec_qty": exec_qty,
                            "exec_price": exec_price,
                            "timestamp": time.time()
                        }
                        order_info["result"] = result
                        order_info["completed"] = True
                        
                        # QEventLoop 종료
                        event_loop = order_info["event_loop"]
                        if event_loop and event_loop.isRunning():
                            event_loop.exit()
                            logger.info(f"✅ 체결 데이터 수신 완료: {order_id}")
                        
                        break
                        
        except Exception as e:
            logger.error(f"체결 데이터 처리 오류: {e}")

    def _safe_get_chejan_data(self, fid: int, field_name: str) -> str:
        """안전한 체결 데이터 추출"""
        try:
            value = self.dynamicCall("GetChejanData(int)", fid)
            return str(value).strip() if value else ""
        except Exception as e:
            logger.warning(f"{field_name}({fid}) 추출 실패: {e}")
            return ""

    def _handle_order_timeout(self, order_id: str) -> None:
        """주문 타임아웃 처리"""
        logger.warning(f"주문 결과 대기 타임아웃: {order_id}")
        
        order_info = self._pending_orders.get(order_id)
        if order_info and not order_info.get("completed", False):
            # 타임아웃 결과 설정
            result = {
                "success": True,
                "order_id": order_id,
                "message": "주문이 접수되었습니다 (결과 확인 중)",
                "timeout": True,
                "timestamp": time.time()
            }
            order_info["result"] = result
            order_info["completed"] = True
            
            # QEventLoop 종료
            event_loop = order_info["event_loop"]
            if event_loop and event_loop.isRunning():
                event_loop.exit()

    def _cleanup_order_request(self, order_id: str) -> None:
        """주문 요청 정리"""
        order_info = self._pending_orders.get(order_id)
        if order_info:
            if order_info.get("timeout_timer"):
                order_info.get("timeout_timer").stop()
            
            # 매핑 테이블에서 제거
            del self._pending_orders[order_id]
            logger.debug(f"주문 요청 정리 완료: {order_id}")

    async def send_order(self, screen_name: str, acc_no: str, 
                        order_type: int, code: str, qty: int, price: int, 
                        hoga_gb: str, org_order_no: str) -> Dict[str, Any]:
        """비동기 주식 주문 전송"""
        try:
            if not self._is_connected:
                return {"success": False, "error": "키움 API에 로그인되지 않았습니다"}
            
            result = self.send_order_sync(screen_name, acc_no, order_type, code, qty, price, hoga_gb, org_order_no)
            logger.info(f"send_order result {result}")
            return result
        
        except Exception as e:
            logger.error(f"주문 전송 오류: {e}")
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
                logger.warning(f"예상치 못한 시간 타입: {type(current_time)}, 현재 시간 사용")
                now = datetime.datetime.now()
            
            # 주말 확인 (토요일=5, 일요일=6)
            if now.weekday() >= 5:
                return {"status": False, "message": "주말 - 장 마감", "is_open": False}
            
            # 장 운영 시간: 09:00 ~ 15:30
            marketOpen = now.replace(hour=9, minute=0, second=0, microsecond=0)
            marketClose = now.replace(hour=15, minute=30, second=0, microsecond=0)

            return {"status": True, "message": "장 운영 중", "is_open": marketOpen <= now <= marketClose}

        except Exception as e:
            logger.error(f"장 운영 시간 확인 오류: {e}")
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
                logger.warning("키움 API 미연결 상태 - 시간 기반 판단 사용")
                return self._is_market_open()
            
            # 키움 API 장 운영 상태 조회 (GetCodeListByMarket 응답으로 간접 확인)
            kospi_codes = self.dynamicCall("GetCodeListByMarket(QString)", "0")
            
            if kospi_codes and len(kospi_codes.split(';')) > 100:
                # 코드 리스트가 정상적으로 조회되면 API가 활성 상태
                time_based_status = self._is_market_open()
                market_status = self._get_market_status()
                
                logger.info(f"장 운영 상태: {market_status['status_message']} ({market_status['current_time']})")
                return time_based_status
            else:
                logger.warning("키움 API 응답 이상 - 시간 기반 판단 사용")
                return self._is_market_open()
                
        except Exception as e:
            logger.error(f"장 운영 상태 확인 오류: {e}")
            return self._is_market_open()
# 싱글톤 인스턴스 생성
kiwoom_component = KiwoomComponent()