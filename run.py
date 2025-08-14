# -*- coding: utf-8 -*-
import sys
import io
import os
from kiwoom_session import get_kiwoom, session

# 한글 출력을 위한 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# 콘솔 인코딩 설정 (Windows용)
os.system("chcp 65001 > nul")

print("🔄 세션 확인 중...")
kiwoom = get_kiwoom()

if kiwoom is None:
    print("❌ 키움 API 연결 실패")
    exit(1)

print("\n" + "="*50)
print("📊 계좌 정보")
print("="*50)

account_num = kiwoom.GetLoginInfo("ACCOUNT_CNT")        # 전체 계좌수
accounts = kiwoom.GetLoginInfo("ACCNO")                 # 전체 계좌 리스트
user_id = kiwoom.GetLoginInfo("USER_ID")                # 사용자 ID
user_name = kiwoom.GetLoginInfo("USER_NAME")            # 사용자명
keyboard = kiwoom.GetLoginInfo("KEY_BSECGB")            # 키보드보안 해지여부
firewall = kiwoom.GetLoginInfo("FIREW_SECGB")           # 방화벽 설정 여부

# 사용자명 인코딩 문제 해결
user_name_decoded = session.decode_korean_text(user_name)

print(f"💰 전체 계좌수: {account_num}")
print(f"📝 계좌 리스트: {accounts}")
print(f"👤 사용자 ID: {user_id}")
print(f"👨‍💼 사용자명: {user_name_decoded}")
print(f"🔐 키보드보안: {keyboard}")
print(f"🛡️ 방화벽 설정: {firewall}")
print("="*50)

print(f"\n📊 세션 상태: {session.get_status()}")