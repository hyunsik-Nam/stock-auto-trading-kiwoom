# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QTimer
from typing import List, Optional, Dict, Any, Callable
import uuid
import time

class TrRequestManager:
    """TR 요청 관리자"""
    
    def __init__(self):
        self._pendingRequests: Dict[str, Dict[str, Any]] = {}
        self._trConfigs: Dict[str, Dict[str, Any]] = self._initTrConfigs()
    
    def _initTrConfigs(self) -> Dict[str, Dict[str, Any]]:
        """TR 설정 초기화"""
        return {
            "opt10001": {
                "name": "주식기본정보",
                "inputs": ["종목코드"],
                "outputs": {
                    "종목명": str,
                    "현재가": int,
                    "전일종가": int,
                    "전일대비": int,
                    "등락률": float,
                    "거래량": int,
                    "시가": int,
                    "고가": int,
                    "저가": int
                }
            },
            "opt10080": {
                "name": "주식분봉차트조회",
                "inputs": ["종목코드", "틱범위", "수정주가구분"],
                "outputs": {
                    "체결시간": str,
                    "현재가": int,
                    "거래량": int,
                    "누적거래량": int
                }
            },
            "opw00001": {
                "name": "예수금상세현황요청",
                "inputs": ["계좌번호"],
                "outputs": {
                    "예수금": int,
                    "D+2추정예수금": int,
                    "유가잔고평가액": int
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
        """TR 데이터 파싱"""
        config = self._trConfigs.get(trCode, {})
        outputs = config.get("outputs", {})
        
        result = {}
        for field, dataType in outputs.items():
            rawValue = rawData.get(field, "")
            
            try:
                if dataType == int:
                    result[field] = int(rawValue.replace(",", "")) if rawValue else 0
                elif dataType == float:
                    result[field] = float(rawValue) if rawValue else 0.0
                else:
                    result[field] = rawValue.strip()
            except (ValueError, AttributeError):
                result[field] = 0 if dataType in [int, float] else ""
        
        return result

class LoginTest(QAxWidget):
    def __init__(self):
        super().__init__()
        try:
            self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
            self.OnEventConnect.connect(self._eventConnect)
            self.OnReceiveTrData.connect(self._receiveTrData)
            self._loginEventLoop = None
            self._isConnected = False
            self._trManager = TrRequestManager()
            self._currentRequestId: Optional[str] = None
            self._requestEventLoop: Optional[QEventLoop] = None
            self._timeoutTimer: Optional[QTimer] = None
            print("✅ 키움 API 컨트롤 초기화 성공")
        except Exception as e:
            print(f"❌ 키움 API 컨트롤 초기화 실패: {e}")
            raise
    
    def login(self) -> bool:
        """로그인 실행"""
        print("🔐 로그인 테스트 시작...")
        self._loginEventLoop = QEventLoop()
        
        try:
            ret = self.dynamicCall("CommConnect()")
            print(f"📡 CommConnect() 결과: {ret}")
            
            if ret == 0:
                print("⏳ 로그인 창 대기 중...")
                self._loginEventLoop.exec_()
            else:
                print(f"❌ 로그인 요청 실패: {ret}")
            
            return self._isConnected
        except Exception as e:
            print(f"❌ 로그인 호출 오류: {e}")
            return False
    
    def _eventConnect(self, errCode: int) -> None:
        """로그인 결과 처리"""
        print(f"📞 로그인 결과: {errCode}")
        
        if errCode == 0:
            self._isConnected = True
            print("✅ 로그인 성공!")
            
            try:
                userName = self.dynamicCall("GetLoginInfo(QString)", "USER_NAME")
                userId = self.dynamicCall("GetLoginInfo(QString)", "USER_ID")
                accounts = self.dynamicCall("GetLoginInfo(QString)", "ACCNO")
                
                print(f"👤 사용자: {userName} ({userId})")
                print(f"💳 계좌: {accounts}")
            except Exception as e:
                print(f"❌ 사용자 정보 조회 오류: {e}")
        else:
            print(f"❌ 로그인 실패: {errCode}")
        
        if self._loginEventLoop:
            self._loginEventLoop.exit()
    
    def requestTr(self, trCode: str, inputs: Dict[str, str], 
                  callback: Optional[Callable] = None, 
                  timeout: int = 10) -> Optional[Dict[str, Any]]:
        """범용 TR 요청 메서드"""
        try:
            if not self._isConnected:
                print("❌ 키움 API에 로그인되지 않음")
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
                print(f"📡 {trCode} 요청 성공, 응답 대기 중...")
                self._requestEventLoop.exec_()
                
                # 타이머 정리
                if self._timeoutTimer:
                    self._timeoutTimer.stop()
                    self._timeoutTimer = None
                
                # 결과 반환
                request = self._trManager.getRequest(self._currentRequestId)
                return request["result"] if request else None
            else:
                print(f"❌ {trCode} 요청 실패: {ret}")
                return None
                
        except Exception as e:
            print(f"❌ TR 요청 오류: {e}")
            return None
        finally:
            self._currentRequestId = None
            if self._timeoutTimer:
                self._timeoutTimer.stop()
                self._timeoutTimer = None
    
    def _onRequestTimeout(self) -> None:
        """요청 타임아웃 처리"""
        print("⏰ TR 요청 타임아웃")
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
                print(f"❌ TR 에러 코드: {errorCode}, 메시지: {msg1}")
                return
            
            print(f"✅ TR 데이터 수신: {rqName} ({trCode})")
            
            # 데이터 추출
            rawData = self._extractRawData(trCode, recordName)
            
            # 데이터 파싱
            parsedData = self._trManager.parseData(trCode, rawData)
            
            # 요청 완료 처리
            if self._currentRequestId and rqName == self._currentRequestId:
                self._trManager.completeRequest(self._currentRequestId, parsedData)
            
            print(f"📊 파싱된 데이터: {parsedData}")
            
        except Exception as e:
            print(f"❌ TR 데이터 처리 오류: {e}")
        finally:
            if self._requestEventLoop and self._requestEventLoop.isRunning():
                self._requestEventLoop.exit()
    
    def _extractRawData(self, trCode: str, recordName: str) -> Dict[str, str]:
        """원시 데이터 추출"""
        rawData = {}
        config = self._trManager._trConfigs.get(trCode, {})
        outputs = config.get("outputs", {})
        
        actualRecordName = recordName if recordName.strip() else ""
        
        for fieldName in outputs.keys():
            try:
                value = self.dynamicCall(
                    "CommGetData(QString, QString, QString, int, QString)",
                    trCode, "", actualRecordName, 0, fieldName
                ).strip()
                rawData[fieldName] = value
            except Exception as e:
                print(f"⚠️ {fieldName} 데이터 추출 실패: {e}")
                rawData[fieldName] = ""
        
        return rawData
    
    # 편의 메서드들
    def getStockInfo(self, stockCode: str) -> Optional[Dict[str, Any]]:
        """주식 기본정보 조회"""
        print("주식 기본정보 조회")
        return self.requestTr("opt10001", {"종목코드": stockCode})
    
    def getStockMinuteChart(self, stockCode: str, minutes: str = "1") -> Optional[Dict[str, Any]]:
        """주식 분봉 차트 조회"""
        return self.requestTr("opt10080", {
            "종목코드": stockCode,
            "틱범위": minutes,
            "수정주가구분": "1"
        })
    
    def getAccountBalance(self, accountNo: str) -> Optional[Dict[str, Any]]:
        """예수금 조회"""
        return self.requestTr("opw00001", {"계좌번호": accountNo})
    
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
            print(f"❌ 코스피 종목 조회 오류: {e}")
            return None

if __name__ == "__main__":
    try:
        print("=== 키움 API 범용 핸들러 테스트 ===")
        
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        loginTest = LoginTest()
        
        if loginTest.login():
            print("🎉 로그인 성공!")
            
            # 삼성전자 종목코드 조회
            stockCode = loginTest.getStockKospi("삼성전자")
            if stockCode:
                print(f"🏢 삼성전자 종목코드: {stockCode}")
                
                # 주식 기본정보 조회
                stockInfo = loginTest.getStockInfo(stockCode)
                if stockInfo:
                    print(f"📊 주식정보: {stockInfo['종목명']} - {stockInfo['현재가']:,}원 ({stockInfo['등락률']}%)")
                
                # 콜백 사용 예시
                def priceCallback(data):
                    print(f"🔔 콜백 데이터: {data['종목명']} - {data['현재가']:,}원")
                
                loginTest.requestTr("opt10001", {"종목코드": stockCode}, callback=priceCallback)
                
            else:
                print("❌ 삼성전자 종목코드를 찾을 수 없음")
        else:
            print("❌ 로그인 실패!")
        
    except Exception as e:
        print(f"❌ 테스트 실행 오류: {e}")
    
    input("Enter를 눌러 종료...")