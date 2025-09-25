# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop

class LoginTest(QAxWidget):
    def __init__(self):
        super().__init__()
        try:
            self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
            self.OnEventConnect.connect(self._event_connect)
            self.login_event_loop = None
            self.is_connected = False
            print("✅ 키움 API 컨트롤 초기화 성공")
        except Exception as e:
            print(f"❌ 키움 API 컨트롤 초기화 실패: {e}")
            raise
    
    def login(self):
        print("🔐 로그인 테스트 시작...")
        self.login_event_loop = QEventLoop()
        
        try:
            ret = self.dynamicCall("CommConnect()")
            print(f"📡 CommConnect() 결과: {ret}")
            
            if ret == 0:
                print("⏳ 로그인 창 대기 중...")
                self.login_event_loop.exec_()
            else:
                print(f"❌ 로그인 요청 실패: {ret}")
        except Exception as e:
            print(f"❌ 로그인 호출 오류: {e}")
    
    def _event_connect(self, err_code):
        print(f"📞 로그인 결과: {err_code}")
        
        if err_code == 0:
            self.is_connected = True
            print("✅ 로그인 성공!")
            
            try:
                # 사용자 정보 출력
                user_name = self.dynamicCall("GetLoginInfo(QString)", "USER_NAME")
                user_id = self.dynamicCall("GetLoginInfo(QString)", "USER_ID")
                accounts = self.dynamicCall("GetLoginInfo(QString)", "ACCNO")
                
                print(f"👤 사용자: {user_name} ({user_id})")
                print(f"💳 계좌: {accounts}")
            except Exception as e:
                print(f"❌ 사용자 정보 조회 오류: {e}")
        else:
            print(f"❌ 로그인 실패: {err_code}")
            
        
        if self.login_event_loop:
            self.login_event_loop.exit()

if __name__ == "__main__":
    try:
        print("=== 키움 API 로그인 테스트 ===")
        
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        login_test = LoginTest()
        login_test.login()
        
        if login_test.is_connected:
            print("🎉 로그인 테스트 성공!")
        else:
            print("❌ 로그인 테스트 실패!")
        
    except Exception as e:
        print(f"❌ 테스트 실행 오류: {e}")
    
    input("Enter를 눌러 종료...")
