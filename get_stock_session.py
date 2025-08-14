# -*- coding: utf-8 -*-
from kiwoom_session import get_session

# 세션 가져오기 (이미 로그인되어 있으면 재사용)
session = get_session()
kiwoom = session.get_kiwoom()

# 세션 정보 출력
session_info = session.get_session_info()
if session_info["connected"]:
    print(f"🔄 기존 세션 사용 중 (세션 시간: {session_info['session_duration_minutes']:.1f}분)")
else:
    print("🆕 새로운 세션 생성됨")

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

# 상위 10개 종목만 출력 (전체를 출력하면 너무 길어짐)
print(f"\n📝 KOSPI 상위 10개 종목: {kospi[:10]}")
print(f"📝 KOSDAQ 상위 10개 종목: {kosdaq[:10]}")
print(f"📝 ETF 상위 10개 종목: {etf[:10]}")

print("\n" + "="*50)
