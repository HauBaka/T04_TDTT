from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from api.health import health_router
from api.discover import discover_router
from api.auth import auth_router
from api.user import user_router
from api.collection import collection_router
from core.database import firebase_manager
from core.exceptions import AppException
from mock_data.virtual_review import virtual_review_manager
from externals.PhoBERT import PhoBERT
from externals.SemanticModel import semantic_model_client
from loguru import logger

import core.http_client as http_client
import httpx
# Khởi tạo các thành phần cần thiết
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo Firebase
    firebase_manager.initialize() 
    # Khởi tạo Virtual Review 
    try:
        virtual_review_manager.initialize("mock_data/user_reviews.csv")
    except FileNotFoundError as e:
        logger.error(f"Error initializing virtual review manager: {e}")

    # Khởi tạo PhoBERT
    PhoBERT.load_model()
    # Khởi tạo Semantic Model
    semantic_model_client.load_model()
    # Khởi tạo HTTP client
    http_client._http_client = httpx.AsyncClient(timeout=10.0)
    yield

    if http_client._http_client:
        await http_client._http_client.aclose()

app = FastAPI(lifespan=lifespan)
# Đăng ký router
app.include_router(health_router, tags=["health"])
app.include_router(discover_router, tags=["discover"])
app.include_router(auth_router, tags=["auth"])
app.include_router(user_router, tags=["user"])
app.include_router(collection_router, tags=["collection"])
# Xử lý các lỗi
@app.exception_handler(AppException) # Xử lý lỗi ứng dụng
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"AppException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
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
            "status_code": 500,
            "message": "An unexpected error occurred.",
            "data": None
        }
    )
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    clean_errors = []
    for error in exc.errors():
        clean_errors.append({
            "field": " -> ".join([str(x) for x in error.get("loc", [])]),
            "message": error.get("msg")
        })

    return JSONResponse(
        status_code=422,
        content={
            "status_code": 422,
            "message": "Validation Error",
            "errors": clean_errors
        }
    )
# default route
@app.get("/", status_code=200)
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello World"}