# -*- coding: utf-8 -*-
"""
간단한 주식 자동매매 시뮬레이터
"""
import time
import random
from datetime import datetime

class SimpleTrader:
    def __init__(self):
        # 초기 설정
        self.balance = 10000000  # 1천만원
        self.positions = {}
        self.stocks = {
            '005930': {'name': '삼성전자', 'price': 75000},
            '000660': {'name': 'SK하이닉스', 'price': 140000},
            '035420': {'name': 'NAVER', 'price': 180000}
        }
        self.price_history = {code: [] for code in self.stocks.keys()}
        
    def generate_price(self, code):
        """랜덤 주가 생성"""
        current_price = self.stocks[code]['price']
        # -2% ~ +2% 변동
        change = random.uniform(-0.02, 0.02)
        new_price = int(current_price * (1 + change))
        
        self.stocks[code]['price'] = new_price
        self.price_history[code].append(new_price)
        
        # 최근 20개만 유지
        if len(self.price_history[code]) > 20:
            self.price_history[code] = self.price_history[code][-20:]
        
        return {
            'price': new_price,
            'change': change * 100,
            'volume': random.randint(1000, 10000)
        }
    
    def calculate_rsi(self, code, period=14):
        """RSI 계산"""
        prices = self.price_history[code]
        if len(prices) < period:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-diff)
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def check_signal(self, code):
        """매매 신호 확인"""
        rsi = self.calculate_rsi(code)
        price = self.stocks[code]['price']
        
        if rsi < 30:  # 과매도
            return {
                'action': 'BUY',
                'rsi': rsi,
                'price': price,
                'reason': f'RSI({rsi:.1f}) < 30 (과매도)'
            }
        elif rsi > 70:  # 과매수
            return {
                'action': 'SELL',
                'rsi': rsi,
                'price': price,
                'reason': f'RSI({rsi:.1f}) > 70 (과매수)'
            }
        else:
            return {
                'action': 'HOLD',
                'rsi': rsi,
                'price': price,
                'reason': f'RSI({rsi:.1f}) 중립'
            }
    
    def execute_trade(self, code, signal):
        """매매 실행"""
        name = self.stocks[code]['name']
        price = signal['price']
        
        if signal['action'] == 'BUY':
            # 자금의 10%로 매수
            investment = self.balance * 0.1
            quantity = int(investment / price)
            
            if quantity > 0 and self.balance >= quantity * price:
                cost = quantity * price
                self.balance -= cost
                
                if code not in self.positions:
                    self.positions[code] = {'quantity': 0, 'avg_price': 0}
                
                pos = self.positions[code]
                total_value = pos['quantity'] * pos['avg_price'] + cost
                pos['quantity'] += quantity
                pos['avg_price'] = total_value / pos['quantity']
                
                print(f"✅ 매수: {name} {quantity:,}주 @{price:,}원 (투자: {cost:,}원)")
                
        elif signal['action'] == 'SELL':
            if code in self.positions and self.positions[code]['quantity'] > 0:
                pos = self.positions[code]
                quantity = pos['quantity']
                revenue = quantity * price
                self.balance += revenue
                
                profit = (price - pos['avg_price']) * quantity
                profit_rate = (price - pos['avg_price']) / pos['avg_price'] * 100
                
                self.positions[code] = {'quantity': 0, 'avg_price': 0}
                
                symbol = "📈" if profit > 0 else "📉"
                print(f"✅ 매도: {name} {quantity:,}주 @{price:,}원")
                print(f"   {symbol} 손익: {profit:+,}원 ({profit_rate:+.2f}%)")
    
    def display_status(self):
        """현재 상태 출력"""
        total_value = self.balance
        
        print(f"\n💼 포트폴리오 현황 ({datetime.now().strftime('%H:%M:%S')})")
        print(f"💰 현금: {self.balance:,}원")
        
        for code, pos in self.positions.items():
            if pos['quantity'] > 0:
                name = self.stocks[code]['name']
                price = self.stocks[code]['price']
                value = pos['quantity'] * price
                total_value += value
                
                profit = (price - pos['avg_price']) * pos['quantity']
                profit_rate = (price - pos['avg_price']) / pos['avg_price'] * 100
                symbol = "📈" if profit > 0 else "📉"
                
                print(f"📊 {name}: {pos['quantity']:,}주 @{price:,}원")
                print(f"   {symbol} 평가손익: {profit:+,}원 ({profit_rate:+.2f}%)")
        
        initial = 10000000
        total_profit = total_value - initial
        total_rate = (total_profit / initial) * 100
        profit_symbol = "📈" if total_profit > 0 else "📉"
        
        print(f"💎 총 자산: {total_value:,}원")
        print(f"{profit_symbol} 총 손익: {total_profit:+,}원 ({total_rate:+.2f}%)")
        print("=" * 50)
    
    def run(self):
        """시뮬레이션 실행"""
        print("🎮 간단한 주식 자동매매 시뮬레이터")
        print("💰 초기 자금: 10,000,000원")
        print("📈 거래 종목: 삼성전자, SK하이닉스, NAVER")
        print("📊 전략: RSI (과매도 30, 과매수 70)")
        print("⏱️ 3초마다 데이터 생성")
        print("=" * 50)
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"\n🔄 시뮬레이션 #{iteration}")
                
                for code in self.stocks.keys():
                    # 가격 데이터 생성
                    data = self.generate_price(code)
                    name = self.stocks[code]['name']
                    
                    # 가격 출력
                    symbol = "📈" if data['change'] > 0 else "📉" if data['change'] < 0 else "➡️"
                    print(f"{symbol} {name}({code}): {data['price']:,}원 ({data['change']:+.2f}%)")
                    
                    # 매매 신호 확인
                    signal = self.check_signal(code)
                    
                    if signal['action'] != 'HOLD':
                        action_symbol = "🟢" if signal['action'] == 'BUY' else "🔴"
                        print(f"🚨 {action_symbol} {signal['action']} 신호!")
                        print(f"   📊 {signal['reason']}")
                        
                        # 매매 실행
                        self.execute_trade(code, signal)
                
                # 5회마다 포트폴리오 출력
                if iteration % 5 == 0:
                    self.display_status()
                
                time.sleep(3)
                
        except KeyboardInterrupt:
            print(f"\n🛑 시뮬레이션 중단 (총 {iteration}회 실행)")
            self.display_status()
            print("👋 시뮬레이터를 종료합니다.")

if __name__ == "__main__":
    try:
        trader = SimpleTrader()
        print("시작하려면 Enter를 누르세요...")
        input()
        trader.run()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        input("Enter를 눌러 종료...")
