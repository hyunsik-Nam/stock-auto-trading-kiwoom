# -*- coding: utf-8 -*-
import sys
import io
import os
import pickle
import threading
from pykiwoom.kiwoom import *

# 한글 출력을 위한 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# 콘솔 인코딩 설정 (Windows용)
os.system("chcp 65001 > nul")

class KiwoomSession:
    """키움 API 세션 관리 클래스"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.kiwoom = None
            self.is_connected = False
            self.session_file = "kiwoom_session.pkl"
            self.initialized = True
    
    def decode_korean_text(self, text):
        """키움 API에서 반환하는 한글 텍스트 디코딩"""
        if isinstance(text, str):
            try:
                # CP949로 인코딩된 문자열을 올바르게 디코딩
                return text.encode('latin1').decode('cp949')
            except:
                try:
                    # 다른 방법으로 시도
                    return text.encode('cp949').decode('utf-8')
                except:
                    # 모든 방법이 실패하면 원본 반환
                    return text
        return text
    
    def connect(self):
        """키움 API 연결"""
        if self.is_connected and self.kiwoom is not None:
            print("✅ 이미 연결되어 있습니다.")
            return self.kiwoom
        
        try:
            print("🔄 키움 API 연결 중...")
            self.kiwoom = Kiwoom()
            self.kiwoom.CommConnect(block=True)
            self.is_connected = True
            print("✅ 키움 API 연결 완료")
            self.save_session()
            return self.kiwoom
        except Exception as e:
            print(f"❌ 연결 실패: {e}")
            self.is_connected = False
            return None
    
    def get_kiwoom(self):
        """키움 객체 반환 (연결되지 않은 경우 자동 연결)"""
        if not self.is_connected or self.kiwoom is None:
            return self.connect()
        return self.kiwoom
    
    def disconnect(self):
        """연결 해제"""
        if self.kiwoom is not None:
            try:
                self.kiwoom.CommTerminate()
                print("🔌 키움 API 연결 해제 완료")
            except:
                pass
        
        self.kiwoom = None
        self.is_connected = False
        self.remove_session()
    
    def save_session(self):
        """세션 정보 저장"""
        try:
            session_data = {
                'is_connected': self.is_connected,
                'timestamp': __import__('time').time()
            }
            with open(self.session_file, 'wb') as f:
                pickle.dump(session_data, f)
        except Exception as e:
            print(f"⚠️ 세션 저장 실패: {e}")
    
    def load_session(self):
        """세션 정보 로드"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'rb') as f:
                    session_data = pickle.load(f)
                
                # 세션이 1시간 이내인지 확인
                current_time = __import__('time').time()
                if current_time - session_data.get('timestamp', 0) < 3600:
                    return session_data.get('is_connected', False)
        except Exception as e:
            print(f"⚠️ 세션 로드 실패: {e}")
        
        return False
    
    def remove_session(self):
        """세션 파일 제거"""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
        except Exception as e:
            print(f"⚠️ 세션 파일 제거 실패: {e}")
    
    def get_status(self):
        """연결 상태 반환"""
        return {
            'connected': self.is_connected,
            'kiwoom_object': self.kiwoom is not None,
            'session_file_exists': os.path.exists(self.session_file)
        }

# 싱글톤 인스턴스 생성
session = KiwoomSession()

def get_kiwoom():
    """키움 객체를 반환하는 편의 함수"""
    return session.get_kiwoom()