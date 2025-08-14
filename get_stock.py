# -*- coding: utf-8 -*-
import sys
import io
from pykiwoom.kiwoom import *

# 한글 출력을 위한 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# 콘솔 인코딩 설정 (Windows용)
import os
os.system("chcp 65001 > nul")

print("키움 API 연결 중...")
kiwoom = Kiwoom()
kiwoom.CommConnect(block=True)
print("✅ 로그인 완료")

print("\n" + "="*50)
print("📈 종목 정보")
print("="*50)

# 삼성전자 종목명 조회
name = kiwoom.GetMasterCodeName("005930")
print(f"🏢 삼성전자 (005930): {name}")

# 시장별 종목 리스트 조회
print("\n📊 시장별 종목 현황:")
kospi = kiwoom.GetCodeListByMarket('0')
kosdaq = kiwoom.GetCodeListByMarket('10')
etf = kiwoom.GetCodeListByMarket('8')

print(f"📈 KOSPI 종목 수: {len(kospi)}개")
print(f"📈 KOSDAQ 종목 수: {len(kosdaq)}개")
print(f"📈 ETF 종목 수: {len(etf)}개")

print("\n" + "="*50)