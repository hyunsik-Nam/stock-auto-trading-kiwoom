# -*- coding: utf-8 -*-
import sys
import time
import logging
# numpy 임포트 (없으면 기본 연산 사용)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    print("⚠️ numpy가 설치되지 않았습니다. 기본 연산을 사용합니다.")
    NUMPY_AVAILABLE = False
    import random
    import math
    
    # numpy 대체 클래스
    class np:
        class random:
            @staticmethod
            def uniform(low, high):
                return random.uniform(low, high)
            
            @staticmethod
            def randint(low, high):
                return random.randint(low, high)
        
        @staticmethod
        def diff(arr):
            return [arr[i+1] - arr[i] for i in range(len(arr)-1)]
        
        @staticmethod
        def where(condition, x, y):
            result = []
            for i in range(len(condition)):
                if condition[i]:
                    result.append(x[i] if hasattr(x, '__getitem__') else x)
                else:
                    result.append(y[i] if hasattr(y, '__getitem__') else y)
            return result
        
        @staticmethod
        def mean(arr):
            return sum(arr) / len(arr) if len(arr) > 0 else 0
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

# PyQt5 임포트 (선택적)
try:
    from PyQt5.QAxContainer import QAxWidget
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QEventLoop, QTimer, QThread, pyqtSignal
    from PyQt5.QtTest import QTest
    PYQT_AVAILABLE = True
except ImportError:
    print("⚠️ PyQt5가 설치되지 않았습니다. 시뮬레이션 모드로만 실행됩니다.")
    PYQT_AVAILABLE = False

# yaml 임포트 (없으면 기본 설정 사용)
try:
    import yaml
except ImportError:
    print("⚠️ PyYAML이 설치되지 않았습니다. 기본 설정을 사용합니다.")
    yaml = None

# ==================== 설정 관리 ====================
class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """설정 파일 로드"""
        if self.config_path.exists():
            if yaml is not None:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # yaml이 없으면 JSON 파일 확인
                json_path = str(self.config_path).replace('.yaml', '.json')
                if Path(json_path).exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
        
        # 기본 설정 생성
        default_config = {
            'trading': {
                'universe': ['005930', '000660', '035420'],  # 삼성전자, SK하이닉스, NAVER
                'strategies': [{
                    'name': 'RSI_Strategy',
                    'params': {'period': 14, 'oversold': 30, 'overbought': 70}
                }],
                'auto_trading': True,
                'market_start_time': '09:00:00',
                'market_end_time': '15:30:00',
                'test_mode': True,
                'ignore_market_time': True,  # 시뮬레이션에서는 항상 True
                'trading_mode': 'simulation'  # simulation 모드 추가
            },
            'risk': {
                'max_position_ratio': 0.1,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.07,
                'max_daily_loss': 0.02,
                'max_daily_trades': 10
            },
            'simulation': {
                'initial_balance': 10000000,  # 1천만원
                'data_interval': 3,  # 3초마다 데이터 생성
                'price_volatility': 0.015  # 1.5% 변동성
            }
        }
        self.save_config(default_config)
        return default_config
    
    def save_config(self, config: Dict):
        """설정 파일 저장"""
        if yaml is None:
            # yaml이 없으면 JSON으로 저장
            json_path = str(self.config_path).replace('.yaml', '.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        else:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

# ==================== 로깅 시스템 ====================
class Logger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.setup_logger()
    
    def setup_logger(self):
        """로거 설정"""
        self.logger = logging.getLogger('TradingSystem')
        self.logger.setLevel(logging.INFO)
        
        # 파일 핸들러
        log_file = self.log_dir / f"trading_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 핸들러 추가
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        self.logger.info(message)
        
    def error(self, message: str):
        self.logger.error(message)
        
    def warning(self, message: str):
        self.logger.warning(message)

# ==================== 시뮬레이션 데이터 생성기 ====================
class SimulationDataGenerator:
    def __init__(self, codes: List[str]):
        self.codes = codes
        self.prices = {}
        
        # 초기 가격 설정 (실제 주가 근사치)
        initial_prices = {
            '005930': 75000,  # 삼성전자
            '000660': 140000,  # SK하이닉스
            '035420': 180000   # NAVER
        }
        
        for code in codes:
            self.prices[code] = initial_prices.get(code, 50000)
    
    def generate_price_data(self, code: str, volatility: float = 0.02) -> Dict:
        """랜덤 주가 데이터 생성"""
        if code not in self.prices:
            self.prices[code] = 50000
        
        # 랜덤 변동률 (-2% ~ +2%)
        change_rate = np.random.uniform(-volatility, volatility)
        new_price = int(self.prices[code] * (1 + change_rate))
        
        # 가격 업데이트
        self.prices[code] = new_price
        
        # 거래량도 랜덤 생성
        volume = np.random.randint(10000, 500000)
        
        return {
            'current_price': new_price,
            'volume': volume,
            'change_rate': change_rate * 100
        }

# ==================== 데이터 관리 ====================
class DataManager:
    def __init__(self):
        self.real_data = {}
        self.price_data = {}
        
    def update_real_price(self, code: str, data: Dict):
        """실시간 시세 업데이트"""
        if code not in self.real_data:
            self.real_data[code] = {}
        
        self.real_data[code].update({
            'current_price': data.get('current_price', 0),
            'volume': data.get('volume', 0),
            'change_rate': data.get('change_rate', 0),
            'timestamp': datetime.now()
        })
        
        self.update_price_history(code, data.get('current_price', 0))
    
    def update_price_history(self, code: str, price: float):
        """가격 히스토리 업데이트"""
        if code not in self.price_data:
            self.price_data[code] = []
        
        self.price_data[code].append({
            'price': price,
            'timestamp': datetime.now()
        })
        
        # 최근 1000개 데이터만 유지
        if len(self.price_data[code]) > 1000:
            self.price_data[code] = self.price_data[code][-1000:]
    
    def get_current_price(self, code: str) -> float:
        """현재가 조회"""
        return self.real_data.get(code, {}).get('current_price', 0)
    
    def calculate_rsi(self, code: str, period: int = 14) -> float:
        """RSI 계산"""
        try:
            if code not in self.price_data or len(self.price_data[code]) < period + 1:
                return 50.0
            
            prices = [data['price'] for data in self.price_data[code][-period-1:]]
            deltas = np.diff(prices)
            
            # 상승/하락 분리
            gains = []
            losses = []
            
            for delta in deltas:
                if delta > 0:
                    gains.append(delta)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(-delta)
            
            avg_gain = np.mean(gains) if gains else 0
            avg_loss = np.mean(losses) if losses else 0
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            print(f"❌ RSI 계산 오류 ({code}): {e}")
            return 50.0

# ==================== 매매 전략 ====================
class RSIStrategy:
    def __init__(self, params: Dict):
        self.name = "RSI_Strategy"
        self.params = params
        self.period = params.get('period', 14)
        self.oversold = params.get('oversold', 30)
        self.overbought = params.get('overbought', 70)
    
    def generate_signal(self, code: str, data_manager: DataManager) -> Dict:
        """RSI 기반 신호 생성"""
        rsi = data_manager.calculate_rsi(code, self.period)
        current_price = data_manager.get_current_price(code)
        
        if rsi < self.oversold:
            return {
                'action': 'BUY',
                'confidence': (self.oversold - rsi) / self.oversold,
                'price': current_price,
                'rsi': rsi,
                'reason': f'RSI({rsi:.1f}) < {self.oversold} (과매도)'
            }
        elif rsi > self.overbought:
            return {
                'action': 'SELL',
                'confidence': (rsi - self.overbought) / (100 - self.overbought),
                'price': current_price,
                'rsi': rsi,
                'reason': f'RSI({rsi:.1f}) > {self.overbought} (과매수)'
            }
        
        return {
            'action': 'HOLD',
            'confidence': 0.0,
            'price': current_price,
            'rsi': rsi,
            'reason': f'RSI({rsi:.1f}) 중립구간'
        }

# ==================== 시뮬레이션 트레이딩 시스템 ====================
class SimulationTrader:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = Config(config_path)
        self.logger = Logger()
        
        # 시뮬레이션 설정
        self.trading_universe = self.config.config['trading']['universe']
        self.data_generator = SimulationDataGenerator(self.trading_universe)
        self.data_manager = DataManager()
        
        # 전략 초기화
        strategy_params = self.config.config['trading']['strategies'][0]['params']
        self.strategy = RSIStrategy(strategy_params)
        
        # 포트폴리오 정보
        self.balance = self.config.config.get('simulation', {}).get('initial_balance', 10000000)
        self.positions = {}  # {code: {'quantity': int, 'avg_price': float}}
        
        # 주가 데이터 (실제 종목명)
        self.stock_names = {
            '005930': '삼성전자',
            '000660': 'SK하이닉스',
            '035420': 'NAVER'
        }
        
        self.is_running = False
    
    def start_simulation(self):
        """시뮬레이션 시작"""
        print("🎮 시뮬레이션 모드 시작")
        print(f"💰 초기 자금: {self.balance:,}원")
        print(f"📈 거래 종목: {len(self.trading_universe)}개")
        
        for code in self.trading_universe:
            name = self.stock_names.get(code, code)
            print(f"  - {code}: {name}")
        
        print("=" * 60)
        
        self.is_running = True
        self.run_simulation()
    
    def run_simulation(self):
        """시뮬레이션 실행"""
        data_interval = self.config.config.get('simulation', {}).get('data_interval', 3)
        volatility = self.config.config.get('simulation', {}).get('price_volatility', 0.015)
        
        print(f"📊 시뮬레이션 실행 중... (Ctrl+C로 중단)")
        print(f"⏱️ 데이터 간격: {data_interval}초")
        print(f"📈 변동성: {volatility*100:.1f}%")
        print("=" * 60)
        
        try:
            iteration = 0
            while self.is_running:
                iteration += 1
                print(f"\n🔄 시뮬레이션 #{iteration}")
                
                for code in self.trading_universe:
                    try:
                        # 랜덤 데이터 생성
                        data = self.data_generator.generate_price_data(code, volatility)
                        
                        # 데이터 업데이트
                        self.data_manager.update_real_price(code, data)
                        
                        # 콘솔 출력
                        self.display_price_data(code, data)
                        
                        # 매매 신호 처리
                        self.process_trading_signal(code)
                        
                    except Exception as e:
                        print(f"❌ {code} 처리 오류: {e}")
                        continue
                
                # 포트폴리오 현황 출력 (10회마다)
                if iteration % 5 == 0:
                    self.display_portfolio()
                
                time.sleep(data_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 사용자가 시뮬레이션을 중단했습니다.")
        except Exception as e:
            print(f"\n❌ 시뮬레이션 오류: {e}")
        finally:
            self.stop_simulation()
    
    def display_price_data(self, code: str, data: Dict):
        """가격 데이터 출력"""
        name = self.stock_names.get(code, code)
        timestamp = datetime.now().strftime("%H:%M:%S")
        change_rate = data['change_rate']
        change_symbol = "📈" if change_rate > 0 else "📉" if change_rate < 0 else "➡️"
        
        print(f"[{timestamp}] {change_symbol} {name}({code})")
        print(f"  💰 현재가: {data['current_price']:,}원 ({change_rate:+.2f}%)")
        print(f"  📊 거래량: {data['volume']:,}주")
        print("-" * 50)
    
    def process_trading_signal(self, code: str):
        """매매 신호 처리"""
        try:
            signal = self.strategy.generate_signal(code, self.data_manager)
            name = self.stock_names.get(code, code)
            
            if signal['action'] == 'HOLD':
                return
            
            # 매매 신호 출력
            action_symbol = "🟢 BUY" if signal['action'] == 'BUY' else "🔴 SELL"
            print(f"\n🚨 매매 신호 발생!")
            print(f"📈 종목: {name} ({code})")
            print(f"⚡ 신호: {action_symbol}")
            print(f"💪 신뢰도: {signal.get('confidence', 0):.2f}")
            print(f"💰 가격: {signal.get('price', 0):,}원")
            print(f"📊 RSI: {signal.get('rsi', 0):.1f}")
            print(f"📝 사유: {signal.get('reason', '')}")
            
            # 매매 실행
            self.execute_trade(code, signal)
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ 매매 신호 처리 오류 ({code}): {e}")
    
    def execute_trade(self, code: str, signal: Dict):
        """매매 실행"""
        price = int(signal.get('price', 0))
        name = self.stock_names.get(code, code)
        
        if signal['action'] == 'BUY':
            # 매수 가능 금액 계산 (자금의 10%)
            max_investment = self.balance * 0.1
            quantity = int(max_investment / price)
            
            if quantity > 0 and self.balance >= quantity * price:
                cost = quantity * price
                self.balance -= cost
                
                # 포지션 업데이트
                if code not in self.positions:
                    self.positions[code] = {'quantity': 0, 'avg_price': 0}
                
                position = self.positions[code]
                total_value = position['quantity'] * position['avg_price'] + cost
                position['quantity'] += quantity
                position['avg_price'] = total_value / position['quantity']
                
                print(f"✅ 매수 체결: {name} {quantity:,}주 @{price:,}원")
                print(f"   총 투자금액: {cost:,}원")
                self.logger.info(f"매수: {code} {quantity}주 @{price}")
        
        elif signal['action'] == 'SELL':
            if code in self.positions and self.positions[code]['quantity'] > 0:
                position = self.positions[code]
                quantity = position['quantity']
                avg_price = position['avg_price']
                
                revenue = quantity * price
                self.balance += revenue
                
                # 손익 계산
                profit_loss = (price - avg_price) * quantity
                profit_rate = (price - avg_price) / avg_price * 100
                
                # 포지션 정리
                self.positions[code] = {'quantity': 0, 'avg_price': 0}
                
                profit_symbol = "📈" if profit_loss > 0 else "📉"
                print(f"✅ 매도 체결: {name} {quantity:,}주 @{price:,}원")
                print(f"   {profit_symbol} 손익: {profit_loss:+,}원 ({profit_rate:+.2f}%)")
                self.logger.info(f"매도: {code} {quantity}주 @{price} 손익: {profit_loss:+,}")
    
    def display_portfolio(self):
        """포트폴리오 현황 출력"""
        try:
            total_value = self.balance
            total_position_value = 0
            
            print(f"\n💼 포트폴리오 현황 ({datetime.now().strftime('%H:%M:%S')})")
            print(f"💰 현금: {self.balance:,}원")
            
            for code, position in self.positions.items():
                if position['quantity'] > 0:
                    name = self.stock_names.get(code, code)
                    current_price = self.data_manager.get_current_price(code)
                    if current_price > 0:
                        position_value = position['quantity'] * current_price
                        total_position_value += position_value
                        
                        # 손익 계산
                        profit_loss = (current_price - position['avg_price']) * position['quantity']
                        profit_rate = (current_price - position['avg_price']) / position['avg_price'] * 100
                        profit_symbol = "📈" if profit_loss > 0 else "📉" if profit_loss < 0 else "➡️"
                        
                        print(f"📊 {name}: {position['quantity']:,}주 @{current_price:,}원")
                        print(f"   {profit_symbol} 평가손익: {profit_loss:+,}원 ({profit_rate:+.2f}%)")
            
            total_value = self.balance + total_position_value
            initial_balance = self.config.config.get('simulation', {}).get('initial_balance', 10000000)
            total_profit = total_value - initial_balance
            total_profit_rate = (total_profit / initial_balance) * 100
            
            profit_symbol = "📈" if total_profit > 0 else "📉" if total_profit < 0 else "➡️"
            print(f"� 총 자산: {total_value:,}원")
            print(f"{profit_symbol} 총 손익: {total_profit:+,}원 ({total_profit_rate:+.2f}%)")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ 포트폴리오 출력 오류: {e}")
            print("=" * 60)
    
    def stop_simulation(self):
        """시뮬레이션 중단"""
        self.is_running = False
        print("📊 최종 포트폴리오:")
        self.display_portfolio()

def main():
    """메인 실행"""
    try:
        print("=== 주식 자동매매 시뮬레이터 ===")
        
        # 설정 파일 확인/생성
        config_path = "config.yaml"
        if not Path(config_path).exists():
            print("📝 설정 파일을 생성합니다...")
            Config(config_path)
            print(f"✅ {config_path} 파일이 생성되었습니다.")
        
        trader = SimulationTrader(config_path)
        
        print("시뮬레이션을 시작하려면 Enter를 누르세요...")
        input()
        
        trader.start_simulation()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
