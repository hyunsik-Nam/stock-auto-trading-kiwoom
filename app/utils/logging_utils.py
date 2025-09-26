import logging
import sys
from typing import Any
from pathlib import Path

class SafeFormatter(logging.Formatter):
    """이모지 안전 처리 로그 포매터"""
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 메시지 안전 포맷팅"""
        try:
            message = super().format(record)
            return message
        except UnicodeEncodeError:
            # 이모지를 텍스트로 변환
            emojiMap = {
                '📊': '[INFO]',
                '❌': '[ERROR]', 
                '✅': '[SUCCESS]',
                '⏳': '[WAIT]',
                '🔐': '[LOGIN]',
                '💰': '[PRICE]',
                '💳': '[ACCOUNT]',
                '📡': '[REQUEST]',
                '🎉': '[COMPLETE]'
            }
            
            message = super().format(record)
            for emoji, text in emojiMap.items():
                message = message.replace(emoji, text)
            
            return message

def setupLogging() -> logging.Logger:
    """로깅 시스템 초기화"""
    logger = logging.getLogger('kiwoom_app')
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 로그 디렉토리 생성
    logDir = Path('logs')
    logDir.mkdir(exist_ok=True)
    
    # 파일 핸들러 (UTF-8 인코딩)
    fileHandler = logging.FileHandler(
        logDir / 'app.log', 
        mode='a', 
        encoding='utf-8'
    )
    fileHandler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(logging.INFO)
    
    # 안전한 포매터 적용
    formatter = SafeFormatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    fileHandler.setFormatter(formatter)
    consoleHandler.setFormatter(formatter)
    
    logger.addHandler(fileHandler)
    logger.addHandler(consoleHandler)
    
    return logger

def safePrint(*args: Any, **kwargs: Any) -> None:
    """안전한 콘솔 출력"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # 이모지를 텍스트로 변환하여 출력
        convertedArgs = []
        for arg in args:
            if isinstance(arg, str):
                converted = (arg.replace('📊', '[INFO]')
                           .replace('❌', '[ERROR]')
                           .replace('✅', '[SUCCESS]')
                           .replace('⏳', '[WAIT]')
                           .replace('🔐', '[LOGIN]')
                           .replace('💰', '[PRICE]')
                           .replace('💳', '[ACCOUNT]')
                           .replace('📡', '[REQUEST]')
                           .replace('🎉', '[COMPLETE]'))
                convertedArgs.append(converted)
            else:
                convertedArgs.append(arg)
        print(*convertedArgs, **kwargs)