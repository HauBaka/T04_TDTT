from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from api.health import health_router
from api.discover import discover_router
from core.database import firebase_manager
from core.exceptions import AppException
from loguru import logger

# Khởi tạo các thành phần cần thiết
@asynccontextmanager
async def lifespan(app: FastAPI):
    firebase_manager.initialize() 
    yield

app = FastAPI(lifespan=lifespan)
# Đăng ký router
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(discover_router, prefix="/api/v1", tags=["discover"])
# Xử lý các lỗi
@app.exception_handler(AppException) # Xử lý lỗi ứng dụng
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"AppException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "data": None
        }
    )
@app.exception_handler(Exception) # Xử lý lỗi không mong muốn
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An unexpected error occurred.",
            "data": None
        }
    )
@app.exception_handler(RequestValidationError) # Xử lý lỗi validation
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Invalid input data.",
            "data": exc.errors()
        }
    )
# default route
@app.get("/", status_code=200)
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello World"}

