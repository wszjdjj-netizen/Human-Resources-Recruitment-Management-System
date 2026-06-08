"""
FastAPI 应用入口
启动命令: uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
import logging
import logging.handlers
from pathlib import Path
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.database import init_db
from app.routers import auth, positions, resumes, candidates, match, ai_config, sourcing, workflow, interviews
from app.security import origin_allowed, referer_allowed

# 日志配置
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            LOG_DIR / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        ),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表，AI配置按用户从数据库读取。"""
    validate_startup_security(settings, allowed_origins)
    init_db()
    yield


app = FastAPI(
    title="招聘管理系统 API",
    description="智能简历筛选与人才池管理系统",
    version="1.0.0",
    lifespan=lifespan,
)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，避免泄露系统内部信息"""
    logger.error(f"未处理的异常: {type(exc).__name__}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "服务器内部错误，请稍后重试"
        }
    )


settings = get_settings()

allowed_origins = settings.cors_origins.split(',') if hasattr(settings, 'cors_origins') and settings.cors_origins else [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
allowed_origins = [origin.strip().rstrip("/") for origin in allowed_origins if origin.strip()]


def validate_startup_security(settings, allowed_origins: list[str]) -> None:
    if not settings.is_production:
        return

    errors = []
    default_secrets = {
        "change-this-to-a-random-secret-key",
        "your-secret-key-change-in-production",
        "replace-with-a-random-secret-key",
    }
    if not settings.secret_key or settings.secret_key in default_secrets or len(settings.secret_key) < 32:
        errors.append("SECRET_KEY 必须换成至少32位的随机强密钥")
    if not settings.credential_encryption_key or len(settings.credential_encryption_key) < 32:
        errors.append("CREDENTIAL_ENCRYPTION_KEY 必须配置至少32位的独立随机密钥")
    if settings.allow_ai_env_fallback:
        errors.append("生产环境不建议开启 ALLOW_AI_ENV_FALLBACK")
    if settings.allow_private_network_urls:
        errors.append("生产环境必须关闭 ALLOW_PRIVATE_NETWORK_URLS")
    if not settings.secure_cookies:
        errors.append("生产环境必须开启 SECURE_COOKIES")
    if settings.cookie_samesite.lower() not in {"lax", "strict"}:
        errors.append("生产环境 COOKIE_SAMESITE 建议设置为 lax 或 strict")
    if not allowed_origins or any(origin == "*" for origin in allowed_origins):
        errors.append("生产环境 CORS_ORIGINS 必须配置为明确域名，不能使用 *")
    if any(origin.startswith("http://") and "localhost" not in origin and "127.0.0.1" not in origin for origin in allowed_origins):
        errors.append("生产环境 CORS_ORIGINS 必须使用 https 域名")

    if errors:
        raise RuntimeError("生产环境安全配置不完整：" + "；".join(errors))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def set_security_headers(response: Response) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    return set_security_headers(response)


@app.middleware("http")
async def enforce_csrf_origin(request: Request, call_next):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return await call_next(request)
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    if not request.cookies.get(settings.auth_cookie_name):
        return await call_next(request)

    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    if origin_allowed(origin, allowed_origins) or referer_allowed(referer, allowed_origins):
        return await call_next(request)
    return set_security_headers(JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "请求来源校验失败，请刷新页面后重试"},
    ))


@app.get("/api/health")
def health_check():
    """健康检查端点"""
    return {"status": "ok", "message": "招聘管理系统运行中"}

# 注册所有路由
app.include_router(auth.router)
app.include_router(positions.router)
app.include_router(resumes.router)
app.include_router(candidates.router)
app.include_router(match.router)
app.include_router(ai_config.router)
app.include_router(sourcing.router)
app.include_router(workflow.router)  # 独立工作流匹配（与平台搜人分离）
app.include_router(interviews.router)  # 面试管理与 AI 总结（demo）
