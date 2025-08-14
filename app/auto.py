import sys
import time
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

# PyQt5 임포트
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QEventLoop, QTimer, QThread, pyqtSignal
from PyQt5.QtTest import QTest

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
                'test_mode': True,  # 테스트 모드 추가
                'ignore_market_time': False,  # 장 시간 무시 옵션
                'trading_mode': 'test'  # normal, test, 24hour
            },
            'risk': {
                'max_position_ratio': 0.1,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.07,
                'max_daily_loss': 0.02,
                'max_daily_trades': 10
            },
            'api': {
                'account_password': '',
                'cert_password': '',
                'auto_login': True
            }
        }
        self.save_config(default_config)
        return default_config
    
    def save_config(self, config: Dict):
        """설정 파일 저장"""
        if yaml is None:
            # yaml이 없으면 JSON으로 저장
            with open(str(self.config_path).replace('.yaml', '.json'), 'w', encoding='utf-8') as f:
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
        # 메인 로거
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
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
    
    def log_trade(self, trade_info: Dict):
        """거래 로그"""
        message = f"TRADE - {trade_info.get('action', '')} {trade_info.get('code', '')} " \
                 f"{trade_info.get('quantity', 0)}주 @{trade_info.get('price', 0)}"
        self.info(message)
    
    def log_signal(self, signal_info: Dict):
        """신호 로그"""
        message = f"SIGNAL - {signal_info.get('action', '')} {signal_info.get('code', '')} " \
                 f"신뢰도: {signal_info.get('confidence', 0):.2f}"
        self.info(message)

# ==================== 데이터 관리 ====================
class DataManager:
    def __init__(self):
        self.real_data = {}  # 실시간 데이터
        self.price_data = {}  # 가격 데이터 (OHLCV)
        self.account_data = {}  # 계좌 정보
        self.holdings = {}  # 보유 종목
        
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
        
        # 가격 데이터 히스토리 업데이트
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
        if code not in self.price_data or len(self.price_data[code]) < period + 1:
            return 50.0  # 기본값
        
        prices = [data['price'] for data in self.price_data[code][-period-1:]]
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_moving_average(self, code: str, period: int = 20) -> float:
        """이동평균 계산"""
        if code not in self.price_data or len(self.price_data[code]) < period:
            return 0.0
        
        prices = [data['price'] for data in self.price_data[code][-period:]]
        return np.mean(prices)

# ==================== 매매 전략 ====================
class Strategy:
    def __init__(self, name: str, params: Dict):
        self.name = name
        self.params = params
    
    def generate_signal(self, code: str, data_manager: DataManager) -> Dict:
        """매매 신호 생성 - 하위 클래스에서 구현"""
        return {'action': 'HOLD', 'confidence': 0.0}

class RSIStrategy(Strategy):
    def __init__(self, params: Dict):
        super().__init__("RSI_Strategy", params)
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

class StrategyEngine:
    def __init__(self):
        self.strategies = []
        self.signals = {}
    
    def add_strategy(self, strategy: Strategy):
        """전략 추가"""
        self.strategies.append(strategy)
    
    def generate_signals(self, code: str, data_manager: DataManager) -> Dict:
        """모든 전략에서 신호 생성"""
        signals = {}
        
        for strategy in self.strategies:
            signal = strategy.generate_signal(code, data_manager)
            signals[strategy.name] = signal
        
        # 신호 통합 로직 (여기서는 첫 번째 전략 사용)
        if signals:
            return list(signals.values())[0]
        
        return {'action': 'HOLD', 'confidence': 0.0}

# ==================== 리스크 관리 ====================
class RiskManager:
    def __init__(self, config: Dict):
        self.max_position_ratio = config.get('max_position_ratio', 0.1)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.03)
        self.take_profit_pct = config.get('take_profit_pct', 0.07)
        self.max_daily_loss = config.get('max_daily_loss', 0.02)
        self.max_daily_trades = config.get('max_daily_trades', 10)
        
        self.daily_trades = 0
        self.daily_pnl = 0.0
    
    def check_risk_limits(self, signal: Dict, account_balance: float) -> bool:
        """리스크 한계 체크"""
        # 일일 거래 횟수 체크
        if self.daily_trades >= self.max_daily_trades:
            return False
        
        # 일일 손실 한계 체크
        if self.daily_pnl < -self.max_daily_loss * account_balance:
            return False
        
        # 신뢰도 체크
        if signal.get('confidence', 0) < 0.5:
            return False
        
        return True
    
    def calculate_position_size(self, signal: Dict, account_balance: float, current_price: float) -> int:
        """포지션 크기 계산"""
        if signal['action'] != 'BUY':
            return 0
        
        # 최대 투자 금액
        max_investment = account_balance * self.max_position_ratio
        
        # 신뢰도 기반 조정
        confidence_factor = signal.get('confidence', 0.5)
        adjusted_investment = max_investment * confidence_factor
        
        # 주식 수 계산
        quantity = int(adjusted_investment / current_price)
        
        return max(0, quantity)
    
    def should_stop_loss(self, entry_price: float, current_price: float, position_type: str) -> bool:
        """손절매 체크"""
        if position_type == 'LONG':
            loss_ratio = (entry_price - current_price) / entry_price
        else:
            loss_ratio = (current_price - entry_price) / entry_price
        
        return loss_ratio >= self.stop_loss_pct
    
    def should_take_profit(self, entry_price: float, current_price: float, position_type: str) -> bool:
        """익절 체크"""
        if position_type == 'LONG':
            profit_ratio = (current_price - entry_price) / entry_price
        else:
            profit_ratio = (entry_price - current_price) / entry_price
        
        return profit_ratio >= self.take_profit_pct

# ==================== 주문 관리 ====================
class OrderManager:
    def __init__(self, api, logger: Logger):
        self.api = api
        self.logger = logger
        self.pending_orders = {}
        self.positions = {}
        self.order_sequence = 0
    
    def send_buy_order(self, code: str, quantity: int, price: int) -> str:
        """매수 주문"""
        self.order_sequence += 1
        order_id = f"BUY_{self.order_sequence}"
        
        try:
            # 키움 API 매수 주문
            ret = self.api.send_order(
                "매수", order_id, self.api.account_num, 1, code, quantity, price, "00", ""
            )
            
            if ret == 0:
                self.pending_orders[order_id] = {
                    'code': code,
                    'action': 'BUY',
                    'quantity': quantity,
                    'price': price,
                    'timestamp': datetime.now()
                }
                self.logger.log_trade({
                    'action': 'BUY_ORDER',
                    'code': code,
                    'quantity': quantity,
                    'price': price
                })
                return order_id
            
        except Exception as e:
            self.logger.error(f"매수 주문 실패: {code}, {e}")
        
        return ""
    
    def send_sell_order(self, code: str, quantity: int, price: int) -> str:
        """매도 주문"""
        self.order_sequence += 1
        order_id = f"SELL_{self.order_sequence}"
        
        try:
            # 키움 API 매도 주문
            ret = self.api.send_order(
                "매도", order_id, self.api.account_num, 2, code, quantity, price, "00", ""
            )
            
            if ret == 0:
                self.pending_orders[order_id] = {
                    'code': code,
                    'action': 'SELL',
                    'quantity': quantity,
                    'price': price,
                    'timestamp': datetime.now()
                }
                self.logger.log_trade({
                    'action': 'SELL_ORDER',
                    'code': code,
                    'quantity': quantity,
                    'price': price
                })
                return order_id
            
        except Exception as e:
            self.logger.error(f"매도 주문 실패: {code}, {e}")
        
        return ""
    
    def update_position(self, code: str, action: str, quantity: int, price: float):
        """포지션 업데이트"""
        if code not in self.positions:
            self.positions[code] = {'quantity': 0, 'avg_price': 0}
        
        position = self.positions[code]
        
        if action == 'BUY':
            total_value = position['quantity'] * position['avg_price'] + quantity * price
            position['quantity'] += quantity
            position['avg_price'] = total_value / position['quantity'] if position['quantity'] > 0 else 0
        elif action == 'SELL':
            position['quantity'] -= quantity
            if position['quantity'] <= 0:
                position['quantity'] = 0
                position['avg_price'] = 0

# ==================== 키움 API 연결 ====================
class KiwoomAPI(QAxWidget):
    def __init__(self):
        super().__init__()
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        
        # 이벤트 연결
        self.OnEventConnect.connect(self._event_connect)
        self.OnReceiveRealData.connect(self._receive_real_data)
        self.OnReceiveChejanData.connect(self._receive_chejan_data)
        
        # 상태 변수
        self.is_connected = False
        self.account_num = None
        self.login_event_loop = None
        
        # 콜백 함수들
        self.real_data_callback = None
        self.chejan_data_callback = None
        
    def comm_connect(self):
        """로그인"""
        print("🔐 키움 OpenAPI 로그인 창을 띄우는 중...")
        
        # 로그인 이벤트 루프 생성
        self.login_event_loop = QEventLoop()
        
        # 로그인 요청
        ret = self.dynamicCall("CommConnect()")
        print(f"📡 CommConnect() 호출 결과: {ret}")
        
        if ret == 0:
            print("⏳ 로그인 창이 표시되어야 합니다. 로그인을 진행해주세요...")
            # 이벤트 루프 실행 (로그인 완료까지 대기)
            self.login_event_loop.exec_()
        else:
            print(f"❌ 로그인 요청 실패: {ret}")
            self.is_connected = False
    
    def _event_connect(self, err_code):
        """로그인 이벤트"""
        print(f"📞 로그인 이벤트 수신: {err_code}")
        
        if err_code == 0:
            self.is_connected = True
            print("✅ 로그인 성공!")
            
            try:
                # 계좌번호 조회
                account_list = self.dynamicCall("GetLoginInfo(QString)", "ACCNO")
                print(f"📋 전체 계좌 리스트: {account_list}")
                
                # 계좌 리스트 파싱
                accounts = [acc.strip() for acc in account_list.split(';') if acc.strip()]
                
                # 81092112가 포함된 계좌 찾기
                self.account_num = None
                for account in accounts:
                    if '81092112' in account:
                        self.account_num = account
                        break
                
                # 해당 계좌를 찾지 못한 경우 첫 번째 계좌 사용
                if self.account_num is None and len(accounts) > 0:
                    self.account_num = accounts[0]
                
                print(f"💳 사용할 계좌번호: {self.account_num}")
                
                # 사용자 정보 조회
                user_name = self.dynamicCall("GetLoginInfo(QString)", "USER_NAME")
                user_id = self.dynamicCall("GetLoginInfo(QString)", "USER_ID")
                print(f"👤 사용자: {user_name} ({user_id})")
                
            except Exception as e:
                print(f"⚠️ 계좌 정보 조회 오류: {e}")
                
        else:
            self.is_connected = False
            error_messages = {
                -100: "사용자 정보교환 실패",
                -101: "서버접속 실패", 
                -102: "버전처리 실패"
            }
            error_msg = error_messages.get(err_code, f"알 수 없는 오류 ({err_code})")
            print(f"❌ 로그인 실패: {error_msg}")
        
        # 이벤트 루프 종료
        if hasattr(self, 'login_event_loop') and self.login_event_loop.isRunning():
            self.login_event_loop.exit()
    
    def get_code_list_by_market(self, market_type):
        """시장별 종목 리스트"""
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_type)
        return code_list.split(';')[:-1]
    
    def get_master_code_name(self, code):
        """종목명 조회"""
        return self.dynamicCall("GetMasterCodeName(QString)", code)
    
    def set_real_reg(self, screen_no, code_list, fid_list, real_type):
        """실시간 등록"""
        ret = self.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                              screen_no, code_list, fid_list, real_type)
        return ret
    
    def _receive_real_data(self, code, real_type, real_data):
        """실시간 데이터 수신"""
        if real_type == "주식체결":
            try:
                current_price = abs(int(self.dynamicCall("GetCommRealData(QString, int)", code, 10)))
                volume = int(self.dynamicCall("GetCommRealData(QString, int)", code, 15))
                change_rate = float(self.dynamicCall("GetCommRealData(QString, int)", code, 12))
                
                # 종목명 조회
                stock_name = self.get_master_code_name(code)
                
                # 콘솔 출력 추가
                timestamp = datetime.now().strftime("%H:%M:%S")
                change_symbol = "📈" if change_rate > 0 else "📉" if change_rate < 0 else "➡️"
                
                print(f"[{timestamp}] {change_symbol} {stock_name}({code})")
                print(f"  💰 현재가: {current_price:,}원 ({change_rate:+.2f}%)")
                print(f"  📊 거래량: {volume:,}주")
                print("-" * 50)
                
                data = {
                    'current_price': current_price,
                    'volume': volume,
                    'change_rate': change_rate
                }
                
                if self.real_data_callback:
                    self.real_data_callback(code, data)
                    
            except Exception as e:
                print(f"❌ 실시간 데이터 처리 오류: {e}")
    
    def send_order(self, rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no):
        """주문 전송"""
        return self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                               [rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no])
    
    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        """체결 데이터 수신"""
        if self.chejan_data_callback:
            self.chejan_data_callback(gubun, item_cnt, fid_list)

# ==================== 메인 트레이딩 매니저 ====================
class TradingManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = Config(config_path)
        self.logger = Logger()
        
        # 컴포넌트 초기화
        self.api = KiwoomAPI()
        self.data_manager = DataManager()
        self.strategy_engine = StrategyEngine()
        self.order_manager = OrderManager(self.api, self.logger)
        self.risk_manager = RiskManager(self.config.config['risk'])
        
        # 상태 변수
        self.is_trading = False
        self.trading_universe = self.config.config['trading']['universe']
        
        # 콜백 설정
        self.api.real_data_callback = self.handle_real_data
        self.api.chejan_data_callback = self.handle_chejan_data
        
        # 전략 로드
        self.load_strategies()
        
        # 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_positions)
        self.timer.start(5000)  # 5초마다
    
    def load_strategies(self):
        """전략 로드"""
        strategies_config = self.config.config['trading']['strategies']
        
        for strategy_config in strategies_config:
            name = strategy_config['name']
            params = strategy_config['params']
            
            if name == 'RSI_Strategy':
                strategy = RSIStrategy(params)
                self.strategy_engine.add_strategy(strategy)
                self.logger.info(f"전략 로드됨: {name}")
    
    def start_trading(self):
        """트레이딩 시작"""
        try:
            trading_mode = self.config.config['trading'].get('trading_mode', 'normal')
            
            print(f"\n{'='*60}")
            print(f"🚀 자동매매 시스템 시작")
            print(f"{'='*60}")
            
            if trading_mode == 'test':
                print(f"🧪 테스트 모드 - 실제 주문 없음, 시뮬레이션만 실행")
            elif trading_mode == '24hour':
                print(f"🌍 24시간 모드 - 장 시간 무관하게 거래")
            else:
                print(f"📊 정상 모드 - 장 시간에만 거래 (09:00~15:30)")
            
            print(f"📈 거래 종목: {len(self.trading_universe)}개")
            print(f"{'='*60}")
            
            # 1. API 연결 및 로그인
            print("\n🔐 키움 API 로그인 시작...")
            self.logger.info("키움 API 연결 중...")
            
            # API 연결 시도
            self.api.comm_connect()
            
            # 연결 결과 확인
            if not self.api.is_connected:
                print("❌ API 연결 실패 - 프로그램을 종료합니다.")
                self.logger.error("API 연결 실패")
                return False
            
            print("✅ API 연결 완료!")
            
            # 계좌 정보 확인
            if not self.api.account_num:
                print("❌ 계좌 정보를 찾을 수 없습니다.")
                return False
            
            # 2. 종목 정보 확인
            print(f"\n📋 거래 종목 정보:")
            for code in self.trading_universe:
                name = self.api.get_master_code_name(code)
                print(f"  - {code}: {name}")
            
            # 3. 실시간 데이터 등록
            print(f"\n📡 실시간 데이터 등록 중...")
            self.register_real_data()
            
            # 4. 트레이딩 시작
            self.is_trading = True
            print(f"\n🎯 자동매매 시스템 가동 완료!")
            print(f"💡 모드: {trading_mode}")
            print(f"📊 실시간 데이터 수신 대기 중...")
            print(f"{'='*60}\n")
            
            self.logger.info(f"자동매매 시작 - {trading_mode} 모드")
            return True
            
        except Exception as e:
            print(f"❌ 트레이딩 시작 실패: {e}")
            self.logger.error(f"트레이딩 시작 실패: {e}")
            return False
    
    def register_real_data(self):
        """실시간 데이터 등록"""
        try:
            # 종목 리스트를 세미콜론으로 구분된 문자열로 변환
            code_list = ';'.join(self.trading_universe)
            
            # 실시간 데이터 등록 (주식체결: 10-현재가, 15-거래량, 12-등락률)
            ret = self.api.set_real_reg("1000", code_list, "10;15;12", "1")
            
            if ret == 0:
                self.logger.info(f"실시간 데이터 등록 성공: {len(self.trading_universe)}개 종목")
                for code in self.trading_universe:
                    name = self.api.get_master_code_name(code)
                    self.logger.info(f"  - {code}: {name}")
            else:
                self.logger.error("실시간 데이터 등록 실패")
                
        except Exception as e:
            self.logger.error(f"실시간 데이터 등록 오류: {e}")
    
    def handle_real_data(self, code: str, data: Dict):
        """실시간 데이터 처리"""
        try:
            # 데이터 업데이트
            self.data_manager.update_real_price(code, data)
            
            # 장 시간 체크
            trading_mode = self.config.config['trading'].get('trading_mode', 'normal')
            
            if not self.is_market_time():
                if trading_mode == 'normal':
                    return  # 정상 모드에서는 장 시간 외 거래 안함
                else:
                    print(f"⚠️ 장 시간 외이지만 {trading_mode} 모드로 계속 진행")
            
            # 트레이딩 신호 생성
            if self.is_trading:
                self.process_trading_signal(code)
                
        except Exception as e:
            self.logger.error(f"실시간 데이터 처리 오류: {e}")
    
    def process_trading_signal(self, code: str):
        """매매 신호 처리"""
        try:
            # 신호 생성
            signal = self.strategy_engine.generate_signals(code, self.data_manager)
            
            # 종목명 조회
            stock_name = self.api.get_master_code_name(code)
            trading_mode = self.config.config['trading'].get('trading_mode', 'normal')
            
            # 테스트 모드 표시
            mode_indicator = ""
            if trading_mode == 'test':
                mode_indicator = "🧪[TEST] "
            elif trading_mode == '24hour':
                mode_indicator = "🌍[24H] "
            
            if signal['action'] == 'HOLD':
                # HOLD 신호도 표시 (테스트 모드에서)
                if trading_mode != 'normal':
                    print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] {mode_indicator}{stock_name}({code}) - HOLD (RSI: {signal.get('rsi', 0):.1f})")
                return
            
            # 매매 신호 콘솔 출력
            action_symbol = "🟢 BUY" if signal['action'] == 'BUY' else "🔴 SELL"
            print(f"\n🚨 {'='*50}")
            print(f"🚨 {mode_indicator}매매 신호 발생!")
            print(f"🚨 {'='*50}")
            print(f"📈 종목: {stock_name} ({code})")
            print(f"⚡ 신호: {action_symbol}")
            print(f"💪 신뢰도: {signal.get('confidence', 0):.2f}")
            print(f"💰 가격: {signal.get('price', 0):,}원")
            print(f"📊 RSI: {signal.get('rsi', 0):.1f}")
            print(f"📝 사유: {signal.get('reason', '')}")
            print(f"🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if trading_mode == 'test':
                print(f"🧪 테스트 모드 - 실제 주문은 전송되지 않습니다")
            elif trading_mode == '24hour':
                print(f"🌍 24시간 모드 - 장 시간 외 거래")
            
            print(f"🚨 {'='*50}\n")
            
            # 로그 기록
            self.logger.log_signal({
                'code': code,
                'action': signal['action'],
                'confidence': signal.get('confidence', 0),
                'reason': signal.get('reason', ''),
                'mode': trading_mode
            })
            
            # 리스크 체크
            account_balance = 10000000  # 임시값
            if not self.risk_manager.check_risk_limits(signal, account_balance):
                print(f"⚠️ 리스크 한계로 인한 거래 제외: {stock_name}({code})")
                self.logger.warning(f"리스크 한계로 인한 거래 제외: {code}")
                return
            
            # 주문 실행 (테스트 모드에서는 시뮬레이션)
            self.execute_signal(code, signal, account_balance)
            
        except Exception as e:
            self.logger.error(f"매매 신호 처리 오류: {e}")
    
    def execute_signal(self, code: str, signal: Dict, account_balance: float):
        """신호 실행"""
        try:
            current_price = int(signal.get('price', 0))
            stock_name = self.api.get_master_code_name(code)
            trading_mode = self.config.config['trading'].get('trading_mode', 'normal')
            
            if signal['action'] == 'BUY':
                # 매수 수량 계산
                quantity = self.risk_manager.calculate_position_size(
                    signal, account_balance, current_price
                )
                
                if quantity > 0:
                    print(f"💳 매수 주문 {'시뮬레이션' if trading_mode == 'test' else '전송'} 중...")
                    print(f"  📈 종목: {stock_name}({code})")
                    print(f"  📊 수량: {quantity:,}주")
                    print(f"  💰 가격: {current_price:,}원")
                    print(f"  💵 총금액: {quantity * current_price:,}원")
                    
                    if trading_mode == 'test':
                        # 테스트 모드 - 시뮬레이션만
                        print(f"🧪 [TEST] 매수 주문 시뮬레이션 완료!")
                        self.logger.info(f"[TEST] 매수 시뮬레이션: {code} {quantity}주 @{current_price}")
                        
                        # 테스트용 포지션 업데이트
                        self.order_manager.update_position(code, 'BUY', quantity, current_price)
                    else:
                        # 실제 주문 전송
                        order_id = self.order_manager.send_buy_order(code, quantity, current_price)
                        if order_id:
                            print(f"✅ 매수 주문 성공! (주문번호: {order_id})")
                            self.logger.info(f"매수 주문 전송: {code} {quantity}주 @{current_price}")
                        else:
                            print(f"❌ 매수 주문 실패!")
            
            elif signal['action'] == 'SELL':
                # 보유 수량 확인
                position = self.order_manager.positions.get(code, {})
                quantity = position.get('quantity', 0)
                
                if quantity > 0:
                    print(f"💳 매도 주문 {'시뮬레이션' if trading_mode == 'test' else '전송'} 중...")
                    print(f"  📉 종목: {stock_name}({code})")
                    print(f"  📊 수량: {quantity:,}주")
                    print(f"  💰 가격: {current_price:,}원")
                    print(f"  💵 총금액: {quantity * current_price:,}원")
                    
                    # 손익 계산
                    avg_price = position.get('avg_price', 0)
                    profit_loss = (current_price - avg_price) * quantity
                    profit_rate = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
                    
                    profit_symbol = "📈" if profit_loss > 0 else "📉"
                    print(f"  {profit_symbol} 손익: {profit_loss:+,}원 ({profit_rate:+.2f}%)")
                    
                    if trading_mode == 'test':
                        # 테스트 모드 - 시뮬레이션만
                        print(f"🧪 [TEST] 매도 주문 시뮬레이션 완료!")
                        self.logger.info(f"[TEST] 매도 시뮬레이션: {code} {quantity}주 @{current_price}")
                        
                        # 테스트용 포지션 업데이트
                        self.order_manager.update_position(code, 'SELL', quantity, current_price)
                    else:
                        # 실제 주문 전송
                        order_id = self.order_manager.send_sell_order(code, quantity, current_price)
                        if order_id:
                            print(f"✅ 매도 주문 성공! (주문번호: {order_id})")
                            self.logger.info(f"매도 주문 전송: {code} {quantity}주 @{current_price}")
                        else:
                            print(f"❌ 매도 주문 실패!")
                else:
                    print(f"⚠️ 보유 수량 없음: {stock_name}({code})")
            
        except Exception as e:
            print(f"❌ 신호 실행 오류: {e}")
            self.logger.error(f"신호 실행 오류: {e}")
    
    def handle_chejan_data(self, gubun: str, item_cnt: int, fid_list: str):
        """체결 데이터 처리"""
        try:
            if gubun == "0":  # 주문체결
                # 체결 정보 파싱 (실제 구현 시 FID 데이터 파싱 필요)
                self.logger.info("주문 체결 발생")
            
        except Exception as e:
            self.logger.error(f"체결 데이터 처리 오류: {e}")
    
    def check_positions(self):
        """포지션 체크 (손절매/익절)"""
        try:
            for code, position in self.order_manager.positions.items():
                if position['quantity'] == 0:
                    continue
                
                current_price = self.data_manager.get_current_price(code)
                if current_price == 0:
                    continue
                
                entry_price = position['avg_price']
                
                # 손절매 체크
                if self.risk_manager.should_stop_loss(entry_price, current_price, 'LONG'):
                    self.logger.warning(f"손절매 신호: {code}")
                    self.order_manager.send_sell_order(
                        code, position['quantity'], int(current_price)
                    )
                
                # 익절 체크
                elif self.risk_manager.should_take_profit(entry_price, current_price, 'LONG'):
                    self.logger.info(f"익절 신호: {code}")
                    self.order_manager.send_sell_order(
                        code, position['quantity'], int(current_price)
                    )
            
        except Exception as e:
            self.logger.error(f"포지션 체크 오류: {e}")

    def is_market_time(self) -> bool:
        """장 시간 체크"""
        trading_mode = self.config.config['trading'].get('trading_mode', 'normal')
        ignore_market_time = self.config.config['trading'].get('ignore_market_time', False)
        
        # 장 시간 무시 모드
        if ignore_market_time or trading_mode == '24hour':
            print(f"🌍 24시간 모드 활성화 - 장 시간 체크 무시")
            return True
        
        # 테스트 모드
        if trading_mode == 'test':
            print(f"🧪 테스트 모드 활성화 - 장 시간 체크 무시")
            return True
        
        # 정상 모드 - 장 시간 체크
        now = datetime.now()
        
        # 주말 체크
        if now.weekday() >= 5:  # 토요일(5), 일요일(6)
            print(f"📅 주말이므로 거래 불가 ({now.strftime('%A')})")
            return False
        
        # 시간 체크
        current_time = now.time()
        market_start = datetime.strptime(
            self.config.config['trading']['market_start_time'], '%H:%M:%S'
        ).time()
        market_end = datetime.strptime(
            self.config.config['trading']['market_end_time'], '%H:%M:%S'
        ).time()
        
        is_market_open = market_start <= current_time <= market_end
        
        if not is_market_open:
            print(f"⏰ 장 시간 외 ({current_time.strftime('%H:%M:%S')}) - 거래 불가")
            print(f"   장 시간: {market_start.strftime('%H:%M:%S')} ~ {market_end.strftime('%H:%M:%S')}")
        
        return is_market_open
    
    def stop_trading(self):
        """트레이딩 중단"""
        self.is_trading = False
        self.logger.info("자동매매 중단")

# ==================== 메인 애플리케이션 ====================
class MainApplication:
    def __init__(self):
        # Qt 애플리케이션을 먼저 생성
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # 창이 닫혀도 종료하지 않음
        
        # 트레이딩 매니저는 나중에 초기화
        self.trading_manager = None
    
    def run(self):
        """메인 실행"""
        try:
            print("=== 키움 OpenAPI+ 자동매매 시스템 ===")
            print("🚀 시스템 초기화 중...")
            
            # 트레이딩 매니저 초기화 (Qt 애플리케이션 생성 후)
            self.trading_manager = TradingManager()
            
            print("시작하려면 Enter를 누르세요...")
            input()
            
            # 트레이딩 시작
            success = self.trading_manager.start_trading()
            
            if not success:
                print("❌ 시스템 시작 실패")
                return
            
            print("🔄 시스템 실행 중... 종료하려면 Ctrl+C를 누르세요...")
            
            # Qt 이벤트 루프 실행
            self.app.exec_()
            
        except KeyboardInterrupt:
            print("\n🛑 사용자가 프로그램 종료를 요청했습니다.")
            if self.trading_manager:
                self.trading_manager.stop_trading()
        except Exception as e:
            print(f"❌ 메인 실행 오류: {e}")
            if self.trading_manager:
                self.trading_manager.logger.error(f"메인 실행 오류: {e}")
        finally:
            print("👋 프로그램을 종료합니다.")

if __name__ == "__main__":
    try:
        # 설정 파일이 없으면 생성
        config_path = "config.yaml"
        if not Path(config_path).exists():
            print("📝 설정 파일을 생성합니다...")
            Config(config_path)
            print(f"✅ {config_path} 파일이 생성되었습니다.")
            print("💡 설정을 수정 후 다시 실행하세요.")
            input("Enter를 눌러 종료...")
            sys.exit(0)
        
        # 메인 애플리케이션 실행
        app = MainApplication()
        app.run()
        
    except Exception as e:
        print(f"❌ 프로그램 실행 오류: {e}")
        input("Enter를 눌러 종료...")
        sys.exit(1)