# -*- coding: utf-8 -*-
from kiwoom_session import get_session

# 세션 가져오기 (없으면 자동으로 로그인)
session = get_session()
kiwoom = session.get_kiwoom()

# 세션 정보 출력
session_info = session.get_session_info()
if session_info["connected"]:
    print(f"🔄 기존 세션 사용 중 (세션 시간: {session_info['session_duration_minutes']:.1f}분)")
else:
    print("🆕 새로운 세션 생성됨")

print("\n" + "="*50)
print("📊 계좌 정보")
print("="*50)

# 계좌 정보 조회
account_num = session.get_login_info("ACCOUNT_CNT")     # 전체 계좌수
accounts = session.get_login_info("ACCNO")              # 전체 계좌 리스트
user_id = session.get_login_info("USER_ID")             # 사용자 ID
user_name = session.get_login_info("USER_NAME")         # 사용자명
keyboard = session.get_login_info("KEY_BSECGB")         # 키보드보안 해지여부
firewall = session.get_login_info("FIREW_SECGB")        # 방화벽 설정 여부

print(f"💰 전체 계좌수: {account_num}")
print(f"📝 계좌 리스트: {accounts}")
print(f"👤 사용자 ID: {user_id}")
print(f"👨‍💼 사용자명: {user_name}")
print(f"🔐 키보드보안: {keyboard}")
print(f"🛡️ 방화벽 설정: {firewall}")
print("="*50)
