from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 모든 라우터 임포트 (Spring Boot의 Controller 스캔과 같음)
from app.router import kiwoom_router as kiwoom

# FastAPI 앱 생성
app = FastAPI(
    title="Finance Model API",
    description="Spring Boot 스타일의 FastAPI 프로젝트",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🎯 모든 라우터 등록 (Spring Boot의 자동 컨트롤러 스캔과 같은 효과)
app.include_router(kiwoom.router, prefix="/api/v1/kiwoom", tags=["키움 증권"])


@app.get("/")
def root():
    return {
        "message": "🚀 전체 프로젝트가 실행되고 있습니다!!!!!!!!!!",
        "available_endpoints": {
            "kiwoom": "/api/v1/kiwoom"
        },
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "message": "모든 서비스가 정상 작동 중입니다"}

# 직접 실행 지원
if __name__ == "__main__":
    print("🚀 Spring Boot 스타일 FastAPI 서버 시작...")
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
