import sys
import logging
from typing import Optional, Dict, Any, List, Callable
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QTimer
import uuid
import time

class TrRequestManager:
    """TR 요청 관리자"""
    
    def __init__(self):
        self._pendingRequests: Dict[str, Dict[str, Any]] = {}
        self._trConfigs: Dict[str, Dict[str, Any]] = self._initTrConfigs()
    
    def _initTrConfigs(self) -> Dict[str, Dict[str, Any]]:
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
    
    def createRequest(self, trCode: str, inputs: Dict[str, str], 
                     callback: Optional[Callable] = None) -> str:
        """TR 요청 생성"""
        requestId = f"{trCode}_{uuid.uuid4().hex[:8]}"
        
        self._pendingRequests[requestId] = {
            "trCode": trCode,
            "inputs": inputs,
            "callback": callback,
            "timestamp": time.time(),
            "completed": False,
            "result": None
        }
        
        return requestId
    
    def completeRequest(self, requestId: str, result: Dict[str, Any]) -> None:
        """요청 완료 처리"""
        if requestId in self._pendingRequests:
            request = self._pendingRequests[requestId]
            request["completed"] = True
            request["result"] = result
            
            if request["callback"]:
                request["callback"](result)
    
    def getRequest(self, requestId: str) -> Optional[Dict[str, Any]]:
        """요청 정보 조회"""
        return self._pendingRequests.get(requestId)
    
    def parseData(self, trCode: str, rawData: Dict[str, str]) -> Dict[str, Any]:
        """TR 데이터 파싱 - 키움 데이터 형식 정확히 처리"""
        config = self._trConfigs.get(trCode, {})
        outputs = config.get("outputs", {})
        
        result = {}
        for field, dataType in outputs.items():
            rawValue = rawData.get(field, "")
            
            try:
                if dataType == int:
                    # 키움 데이터 특성: +/- 부호 포함, 콤마 포함
                    cleanValue = rawValue.replace(",", "").replace("+", "").strip()
                    result[field] = int(cleanValue) if cleanValue and cleanValue != "-" else 0
                elif dataType == float:
                    # 퍼센트나 소수점 데이터 처리
                    cleanValue = rawValue.replace("%", "").replace("+", "").strip()
                    result[field] = float(cleanValue) if cleanValue and cleanValue != "-" else 0.0
                else:
                    result[field] = rawValue.strip()
            except (ValueError, AttributeError):
                result[field] = 0 if dataType in [int, float] else ""
        
        return result

class KiwoomComponent(QAxWidget):
    _instance: Optional['KiwoomComponent'] = None
    _initialized: bool = False
    _qApplication: Optional[QApplication] = None

    def __new__(cls):
        if cls._instance is None:
            cls._initializeQApplicationClass()
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def _initializeQApplicationClass(cls) -> None:
        """클래스 레벨에서 QApplication 초기화"""
        if cls._qApplication is None:
            app = QApplication.instance()
            if app is None:
                cls._qApplication = QApplication(sys.argv)
                cls._qApplication.setQuitOnLastWindowClosed(False)
                print("✅ QApplication 초기화 완료")
            else:
                cls._qApplication = app

    def __init__(self):
        if not self._initialized:
            super().__init__()
            try:
                self._logger = logging.getLogger(__name__)
                self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
                self.OnEventConnect.connect(self._eventConnect)
                self.OnReceiveTrData.connect(self._receiveTrData)
                self._loginEventLoop = None
                self._isConnected = False
                self._trManager = TrRequestManager()
                self._currentRequestId: Optional[str] = None
                self._requestEventLoop: Optional[QEventLoop] = None
                self._timeoutTimer: Optional[QTimer] = None
                self._userInfo: Dict[str, str] = {}
                KiwoomComponent._initialized = True
                self._logger.info("✅ 키움 API 컨트롤 초기화 성공")
            except Exception as e:
                self._logger.error(f"❌ 키움 API 컨트롤 초기화 실패: {e}")
                raise

    async def login(self) -> bool:
        """키움 API 로그인"""
        try:
            self._logger.info("🔐 키움 API 로그인 시작")
            
            if self._isConnected:
                self._logger.info("이미 로그인 상태입니다")
                return True

            self._loginEventLoop = QEventLoop()
            ret = self.dynamicCall("CommConnect()")
            self._logger.info(f"📡 CommConnect() 결과: {ret}")
            
            if ret == 0:
                self._logger.info("⏳ 로그인 창 대기 중...")
                self._loginEventLoop.exec_()
                return self._isConnected
            else:
                self._logger.error(f"❌ 로그인 요청 실패: {ret}")
                return False
                
        except Exception as e:
            self._logger.error(f"❌ 로그인 호출 오류: {e}")
            return False

    def _eventConnect(self, errCode: int) -> None:
        """로그인 결과 이벤트 처리"""
        self._logger.info(f"📞 로그인 결과: {errCode}")
        
        try:
            if errCode == 0:
                self._isConnected = True
                self._logger.info("✅ 로그인 성공!")
                self._collectUserInfo()
            else:
                self._isConnected = False
                self._logger.error(f"❌ 로그인 실패: {errCode}")
        except Exception as e:
            self._logger.error(f"❌ 로그인 이벤트 처리 오류: {e}")
        finally:
            if self._loginEventLoop:
                self._loginEventLoop.exit()

    def _collectUserInfo(self) -> None:
        """사용자 정보 수집"""
        try:
            self._userInfo = {
                "userName": self.dynamicCall("GetLoginInfo(QString)", "USER_NAME"),
                "userId": self.dynamicCall("GetLoginInfo(QString)", "USER_ID"),
                "accounts": self.dynamicCall("GetLoginInfo(QString)", "ACCNO")
            }
            
            self._logger.info(f"👤 사용자: {self._userInfo['userName']} ({self._userInfo['userId']})")
            self._logger.info(f"💳 계좌: {self._userInfo['accounts']}")
            
        except Exception as e:
            self._logger.error(f"❌ 사용자 정보 조회 오류: {e}")

    async def requestTr(self, trCode: str, inputs: Dict[str, str], 
                       callback: Optional[Callable] = None, 
                       timeout: int = 10) -> Optional[Dict[str, Any]]:
        """범용 TR 요청 메서드"""
        try:
            if not self._isConnected:
                self._logger.error("❌ 키움 API에 로그인되지 않음")
                return None
            
            # 입력값 설정
            for key, value in inputs.items():
                self.dynamicCall("SetInputValue(QString, QString)", key, value)
            
            # 요청 생성
            self._currentRequestId = self._trManager.createRequest(trCode, inputs, callback)
            
            # 이벤트 루프 및 타이머 설정
            self._requestEventLoop = QEventLoop()
            self._timeoutTimer = QTimer()
            self._timeoutTimer.setSingleShot(True)
            self._timeoutTimer.timeout.connect(self._onRequestTimeout)
            self._timeoutTimer.start(timeout * 1000)
            
            # TR 요청
            screenNo = f"{int(time.time()) % 10000:04d}"
            ret = self.dynamicCall(
                "CommRqData(QString, QString, int, QString)",
                self._currentRequestId,
                trCode,
                0,
                screenNo
            )
            
            if ret == 0:
                self._logger.info(f"📡 {trCode} 요청 성공, 응답 대기 중...")
                self._requestEventLoop.exec_()
                
                # 타이머 정리
                if self._timeoutTimer:
                    self._timeoutTimer.stop()
                    self._timeoutTimer = None
                
                # 결과 반환
                request = self._trManager.getRequest(self._currentRequestId)
                return request["result"] if request else None
            else:
                self._logger.error(f"❌ {trCode} 요청 실패: {ret}")
                return None
                
        except Exception as e:
            self._logger.error(f"❌ TR 요청 오류: {e}")
            return None
        finally:
            self._currentRequestId = None
            if self._timeoutTimer:
                self._timeoutTimer.stop()
                self._timeoutTimer = None
    
    def _onRequestTimeout(self) -> None:
        """요청 타임아웃 처리"""
        self._logger.warning("⏰ TR 요청 타임아웃")
        if self._requestEventLoop:
            self._requestEventLoop.exit()
    
    def _receiveTrData(self, screenNo, rqName, trCode, recordName, prevNext, dataLen, errCode, msg1, msg2):
        """범용 TR 데이터 수신 처리"""
        try:
            # errCode 처리
            errorCode = 0
            if isinstance(errCode, str):
                errorCode = int(errCode) if errCode.strip() else 0
            else:
                errorCode = int(errCode)
            
            if errorCode != 0:
                self._logger.error(f"❌ TR 에러 코드: {errorCode}, 메시지: {msg1}")
                return
            
            self._logger.info(f"✅ TR 데이터 수신: {rqName} ({trCode})")
            
            # 데이터 추출
            rawData = self._extractRawData(trCode, recordName)
            
            # 원시 데이터 디버깅
            self._logger.info(f"🔍 원시 데이터 샘플:")
            for key, value in list(rawData.items())[:5]:
                self._logger.info(f"  {key}: '{value}'")
            
            # 데이터 파싱
            parsedData = self._trManager.parseData(trCode, rawData)
            
            # 요청 완료 처리
            if self._currentRequestId and rqName == self._currentRequestId:
                self._trManager.completeRequest(self._currentRequestId, parsedData)
            
            # 주요 데이터만 로깅
            if trCode == "opt10001":
                self._logger.info(f"📊 {parsedData.get('종목명', '')}: {parsedData.get('현재가', 0):,}원 ({parsedData.get('등락률', 0.0):+.2f}%)")
            
        except Exception as e:
            self._logger.error(f"❌ TR 데이터 처리 오류: {e}")
        finally:
            if self._requestEventLoop and self._requestEventLoop.isRunning():
                self._requestEventLoop.exit()
    
    def _extractRawData(self, trCode: str, recordName: str) -> Dict[str, str]:
        """원시 데이터 추출 - 모든 가능한 필드 추출"""
        rawData = {}
        
        # opt10001의 경우 정확한 필드명 사용
        if trCode == "opt10001":
            fieldNames = [
                "종목명", "현재가", "기준가", "전일종가", "시가", "고가", "저가",
                "상한가", "하한가", "전일대비", "등락률", "거래량", "거래대금",
                "액면가", "시가총액", "상장주수", "PER", "EPS", "ROE", "PBR"
            ]
        else:
            # 다른 TR의 경우 설정에서 가져오기
            config = self._trManager._trConfigs.get(trCode, {})
            fieldNames = list(config.get("outputs", {}).keys())
        
        actualRecordName = recordName if recordName.strip() else ""
        
        for fieldName in fieldNames:
            try:
                value = self.dynamicCall(
                    "CommGetData(QString, QString, QString, int, QString)",
                    trCode, "", actualRecordName, 0, fieldName
                ).strip()
                rawData[fieldName] = value
                
                # 디버깅: 주요 필드 원시값 출력
                if fieldName in ["종목명", "현재가", "전일대비", "등락률"]:
                    self._logger.debug(f"  원시 {fieldName}: '{value}'")
                    
            except Exception as e:
                self._logger.warning(f"⚠️ {fieldName} 데이터 추출 실패: {e}")
                rawData[fieldName] = ""
        
        return rawData
    
    # 편의 메서드들
    async def getStockInfo(self, stockCode: str) -> Optional[Dict[str, Any]]:
        """주식 기본정보 조회"""
        self._logger.info(f"📈 주식 기본정보 조회: {stockCode}")
        return await self.requestTr("opt10001", {"종목코드": stockCode})
    
    def getStockKospi(self, stock: str) -> Optional[str]:
        """코스피 주식 코드 조회"""
        try:
            kospi = self.dynamicCall("GetCodeListByMarket(QString)", "0")
            codes = kospi.split(';')
            
            for code in codes:
                code = code.strip()
                if code:
                    stockName = self.dynamicCall("GetMasterCodeName(QString)", code)
                    if stockName == stock:
                        return code
            return None
        except Exception as e:
            self._logger.error(f"❌ 코스피 종목 조회 오류: {e}")
            return None

    @property
    def isConnected(self) -> bool:
        """연결 상태 확인"""
        return self._isConnected

    @property
    def userInfo(self) -> Dict[str, str]:
        """사용자 정보 반환"""
        return self._userInfo.copy()

    def getAccountList(self) -> List[str]:
        """계좌 목록 반환"""
        if self._userInfo.get("accounts"):
            return self._userInfo["accounts"].split(";")[:-1]
        return []

# 싱글톤 인스턴스 생성
kiwoomComponent = KiwoomComponent()