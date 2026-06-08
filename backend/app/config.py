"""
应用配置管理
从 .env 文件和环境变量中读取配置
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    environment: str = "development"

    # 数据库
    database_url: str = "sqlite:///./recruitment.db"

    # JWT
    secret_key: str = "change-this-to-a-random-secret-key"
    credential_encryption_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    allow_public_registration: bool = False
    registration_invite_code: str = ""
    auth_login_rate_limit: int = 8
    auth_login_rate_window_seconds: int = 300
    auth_register_rate_limit: int = 5
    auth_register_rate_window_seconds: int = 3600

    # AI接口（兼容OpenAI格式）
    ai_endpoint: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""
    ai_model: str = "deepseek-chat"
    allow_ai_env_fallback: bool = False
    allow_private_network_urls: bool = False

    # 上传文件
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20
    max_runner_screenshot_size_mb: int = 5
    runner_token_ttl_minutes: int = 30

    # CORS配置
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 公网后端地址。部署到线上并使用本地 runner 时必须配置为实际域名，
    # 例如 https://api.example.com；留空时按当前请求地址推断。
    public_backend_url: str = ""

    # Cookie / frontend security hints
    frontend_origin: str = ""
    auth_cookie_name: str = "recruitment_access_token"
    secure_cookies: bool = True
    cookie_samesite: str = "lax"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
