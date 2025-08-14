# -*- coding: utf-8 -*-
import sys
import io
import os

# 한글 출력을 위한 인코딩 설정
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')
except:
    pass

# 콘솔 인코딩 설정 (Windows용)
os.system("chcp 65001 > nul")

print("="*50)
print("🧪 한글 인코딩 테스트")
print("="*50)
print("✅ 한글이 정상적으로 출력됩니다!")
print("📊 키움증권 API 연동 준비 완료")
print("💰 주식 거래 시스템")
print("🔄 세션 관리 시스템")
print("📈 종목 정보 조회")
print("👤 사용자: 홍길동")
print("🏢 회사: 삼성전자")
print("="*50)

# 이모지와 한글 혼합 테스트
test_data = {
    "사용자명": "홍길동",
    "계좌번호": "1234567890",
    "보유종목": ["삼성전자", "LG전자", "SK하이닉스"],
    "상태": "정상"
}

print("\n📋 테스트 데이터:")
for key, value in test_data.items():
    print(f"  {key}: {value}")

print("\n✅ 한글 인코딩 테스트 완료!")
