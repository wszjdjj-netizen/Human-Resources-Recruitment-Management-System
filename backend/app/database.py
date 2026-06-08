"""
数据库连接管理
使用 SQLAlchemy 2.0 引擎和会话工厂
"""
import socket
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()


def _resolve_ipv4(hostname: str) -> str | None:
    """Resolve hostname to an IPv4 address for environments without IPv6."""
    try:
        addrs = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        if addrs:
            return addrs[0][4][0]
    except Exception:
        pass
    return None


# 创建数据库引擎
# SQLite需要check_same_thread=False以支持FastAPI异步调用
if "sqlite" in settings.database_url:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=False,  # 生产环境关闭SQL日志
    )
else:
    connect_args = {}
    url = urlparse(settings.database_url)
    hostname = url.hostname
    if hostname:
        ipv4 = _resolve_ipv4(hostname)
        if ipv4:
            connect_args["hostaddr"] = ipv4
    engine = create_engine(settings.database_url, connect_args=connect_args, echo=False)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """所有ORM模型的基类"""
    pass


def get_db():
    """
    数据库会话依赖注入
    在FastAPI路由中使用: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库：创建所有表
    在应用启动时调用
    """
    from app import models  # noqa: F401 - import all models before create_all
    Base.metadata.create_all(bind=engine)
    _apply_runtime_migrations()
    _encrypt_existing_plaintext_platform_credentials()


def _apply_runtime_migrations():
    """为既有 SQLite 库补齐新增字段。"""
    if "sqlite" not in settings.database_url:
        return

    inspector = inspect(engine)

    table_columns = {
        "candidates": {
            "source_platform": "ALTER TABLE candidates ADD COLUMN source_platform VARCHAR(50)",
            "source_uid": "ALTER TABLE candidates ADD COLUMN source_uid VARCHAR(200)",
            "source_profile_url": "ALTER TABLE candidates ADD COLUMN source_profile_url VARCHAR(500)",
            "dedupe_fingerprint": "ALTER TABLE candidates ADD COLUMN dedupe_fingerprint VARCHAR(64)",
            "sourcing_task_id": "ALTER TABLE candidates ADD COLUMN sourcing_task_id INTEGER",
            "last_sourced_at": "ALTER TABLE candidates ADD COLUMN last_sourced_at DATETIME",
        },
        "sourcing_tasks": {
            "status_detail": "ALTER TABLE sourcing_tasks ADD COLUMN status_detail TEXT",
            "pending_action": "ALTER TABLE sourcing_tasks ADD COLUMN pending_action VARCHAR(50)",
            "current_platform": "ALTER TABLE sourcing_tasks ADD COLUMN current_platform VARCHAR(50)",
            "reviewed_count": "ALTER TABLE sourcing_tasks ADD COLUMN reviewed_count INTEGER NOT NULL DEFAULT 0",
            "deduped_count": "ALTER TABLE sourcing_tasks ADD COLUMN deduped_count INTEGER NOT NULL DEFAULT 0",
            "runner_session_id": "ALTER TABLE sourcing_tasks ADD COLUMN runner_session_id VARCHAR(120)",
            "runner_name": "ALTER TABLE sourcing_tasks ADD COLUMN runner_name VARCHAR(120)",
            "runner_token_hash": "ALTER TABLE sourcing_tasks ADD COLUMN runner_token_hash VARCHAR(128)",
            "runner_token_expires_at": "ALTER TABLE sourcing_tasks ADD COLUMN runner_token_expires_at DATETIME",
            "last_heartbeat": "ALTER TABLE sourcing_tasks ADD COLUMN last_heartbeat DATETIME",
            "started_at": "ALTER TABLE sourcing_tasks ADD COLUMN started_at DATETIME",
            "completed_at": "ALTER TABLE sourcing_tasks ADD COLUMN completed_at DATETIME",
        },
        "sourcing_outreach": {
            "platform_candidate_id": "ALTER TABLE sourcing_outreach ADD COLUMN platform_candidate_id VARCHAR(200)",
            "profile_url": "ALTER TABLE sourcing_outreach ADD COLUMN profile_url VARCHAR(500)",
            "review_status": "ALTER TABLE sourcing_outreach ADD COLUMN review_status VARCHAR(30) NOT NULL DEFAULT '待确认'",
            "external_message_id": "ALTER TABLE sourcing_outreach ADD COLUMN external_message_id VARCHAR(200)",
            "external_thread_id": "ALTER TABLE sourcing_outreach ADD COLUMN external_thread_id VARCHAR(200)",
            "failure_reason": "ALTER TABLE sourcing_outreach ADD COLUMN failure_reason TEXT",
            "delivery_payload": "ALTER TABLE sourcing_outreach ADD COLUMN delivery_payload TEXT",
            "approved_by_user_id": "ALTER TABLE sourcing_outreach ADD COLUMN approved_by_user_id INTEGER",
            "approved_at": "ALTER TABLE sourcing_outreach ADD COLUMN approved_at DATETIME",
        },
        "user_ai_provider_configs": {
            "user_id": "ALTER TABLE user_ai_provider_configs ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0",
            "provider_id": "ALTER TABLE user_ai_provider_configs ADD COLUMN provider_id VARCHAR(80) NOT NULL DEFAULT 'default'",
            "name": "ALTER TABLE user_ai_provider_configs ADD COLUMN name VARCHAR(120) NOT NULL DEFAULT '默认配置'",
            "endpoint": "ALTER TABLE user_ai_provider_configs ADD COLUMN endpoint VARCHAR(500) NOT NULL DEFAULT ''",
            "encrypted_api_key": "ALTER TABLE user_ai_provider_configs ADD COLUMN encrypted_api_key TEXT NOT NULL DEFAULT ''",
            "model": "ALTER TABLE user_ai_provider_configs ADD COLUMN model VARCHAR(120) NOT NULL DEFAULT ''",
            "parsing_mode": "ALTER TABLE user_ai_provider_configs ADD COLUMN parsing_mode VARCHAR(30) NOT NULL DEFAULT 'generic'",
            "is_active": "ALTER TABLE user_ai_provider_configs ADD COLUMN is_active INTEGER NOT NULL DEFAULT 0",
            "created_at": "ALTER TABLE user_ai_provider_configs ADD COLUMN created_at DATETIME",
            "updated_at": "ALTER TABLE user_ai_provider_configs ADD COLUMN updated_at DATETIME",
        },
    }

    with engine.begin() as conn:
        for table_name, column_sql in table_columns.items():
            existing_tables = set(inspector.get_table_names())
            if table_name not in existing_tables:
                continue
            existing_columns = {item["name"] for item in inspector.get_columns(table_name)}
            for column_name, sql in column_sql.items():
                if column_name not in existing_columns:
                    conn.execute(text(sql))


def _encrypt_existing_plaintext_platform_credentials():
    """Encrypt platform credentials saved by older versions."""
    try:
        from app.models.sourcing import SourcingPlatformAccount
        from app.services.ai_client import encrypt_secret
    except Exception:
        return

    db = SessionLocal()
    try:
        rows = db.query(SourcingPlatformAccount).filter(
            SourcingPlatformAccount.credential.isnot(None)
        ).all()
        changed = False
        for row in rows:
            credential = row.credential or ""
            if credential and not credential.startswith("gAAAAA"):
                row.credential = encrypt_secret(credential)
                changed = True
        if changed:
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
