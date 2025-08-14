# -*- coding: utf-8 -*-
"""
간단한 시뮬레이션 실행 스크립트
"""
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from simulation import main
    
    print("🎮 주식 자동매매 시뮬레이터 시작")
    print("=" * 50)
    print("📌 이 프로그램은 실제 거래 없이 매매 알고리즘을 테스트합니다")
    print("📌 가상의 데이터로 RSI 전략을 시뮬레이션합니다")
    print("📌 Ctrl+C를 눌러 언제든지 종료할 수 있습니다")
    print("=" * 50)
    
    main()
    
except ImportError as e:
    print(f"❌ 모듈 import 오류: {e}")
    print("simulation.py 파일이 같은 폴더에 있는지 확인해주세요.")
    
except Exception as e:
    print(f"❌ 실행 오류: {e}")
    
finally:
    print("\n👋 시뮬레이터를 종료합니다.")
    input("Enter를 눌러 창을 닫으세요...")
