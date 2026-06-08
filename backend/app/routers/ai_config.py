"""
Per-user AI configuration routes.

Each account owns its own OpenAI-compatible providers. API keys are encrypted
at rest and never returned in plain text.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.jwt_middleware import get_current_user
from app.models.ai_config import UserAIProviderConfig
from app.models.user import User
from app.services.ai_client import build_ai_client, encrypt_api_key
from app.config import get_settings
from app.security import normalize_public_http_url

router = APIRouter(
    prefix="/api/ai-config",
    tags=["AI配置"],
)

MASK_SENTINEL = "__KEEP_SAVED_KEY__"


class AIProviderConfig(BaseModel):
    id: str
    name: str
    endpoint: str
    api_key: str = ""
    model: str
    parsing_mode: str = "generic"
    is_active: bool = False
    has_key: bool = False


class AIConfigUpdate(BaseModel):
    id: str | None = Field(None, description="配置ID")
    name: str | None = Field(None, description="配置名称")
    endpoint: str = Field(..., description="API端点地址")
    api_key: str = Field("", description="API密钥。留空或传保留标记时沿用已保存密钥")
    model: str = Field(..., description="模型名称")
    parsing_mode: str | None = Field("generic", description="解析模式")


class AIConfigResponse(BaseModel):
    active_id: str
    endpoint: str
    api_key: str
    model: str
    parsing_mode: str = "generic"
    has_key: bool = False
    providers: list[AIProviderConfig] = Field(default_factory=list)


def _mask_key(has_key: bool) -> str:
    return "********" if has_key else ""


def _infer_provider_name(endpoint: str) -> str:
    endpoint = (endpoint or "").lower()
    if "deepseek" in endpoint:
        return "DeepSeek"
    if "dashscope" in endpoint or "aliyun" in endpoint:
        return "通义千问"
    if "openai" in endpoint:
        return "OpenAI"
    if "localhost" in endpoint or "127.0.0.1" in endpoint:
        return "本地模型"
    return "自定义配置"


def _normalize_provider_id(value: str | None, endpoint: str) -> str:
    import re
    raw = (value or _infer_provider_name(endpoint)).strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-")
    return normalized[:80] or "custom"


def _active_provider(db: Session, user_id: int) -> UserAIProviderConfig | None:
    return db.query(UserAIProviderConfig).filter(
        UserAIProviderConfig.user_id == user_id,
        UserAIProviderConfig.is_active == 1,
    ).order_by(UserAIProviderConfig.updated_at.desc(), UserAIProviderConfig.id.desc()).first()


def _provider_response(provider: UserAIProviderConfig, active_id: str) -> AIProviderConfig:
    has_key = bool(provider.encrypted_api_key)
    return AIProviderConfig(
        id=provider.provider_id,
        name=provider.name,
        endpoint=provider.endpoint,
        api_key=_mask_key(has_key),
        model=provider.model,
        parsing_mode=provider.parsing_mode or "generic",
        is_active=provider.provider_id == active_id,
        has_key=has_key,
    )


def _response(db: Session, user_id: int) -> AIConfigResponse:
    providers = db.query(UserAIProviderConfig).filter(
        UserAIProviderConfig.user_id == user_id,
    ).order_by(UserAIProviderConfig.is_active.desc(), UserAIProviderConfig.updated_at.desc(), UserAIProviderConfig.id.desc()).all()
    active = next((item for item in providers if item.is_active), None)
    active_id = active.provider_id if active else ""
    return AIConfigResponse(
        active_id=active_id,
        endpoint=active.endpoint if active else "",
        api_key=_mask_key(bool(active and active.encrypted_api_key)),
        model=active.model if active else "",
        parsing_mode=(active.parsing_mode if active else "generic") or "generic",
        has_key=bool(active and active.encrypted_api_key),
        providers=[_provider_response(provider, active_id) for provider in providers],
    )


@router.get("", response_model=AIConfigResponse)
def get_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _response(db, current_user.id)


@router.put("", response_model=AIConfigResponse)
def update_config(
    req: AIConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    try:
        endpoint = normalize_public_http_url(
            req.endpoint,
            allow_private=settings.allow_private_network_urls,
            require_resolvable=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not req.model.strip():
        raise HTTPException(status_code=400, detail="模型名称不能为空")

    provider_id = _normalize_provider_id(req.id, endpoint)
    existing = db.query(UserAIProviderConfig).filter(
        UserAIProviderConfig.user_id == current_user.id,
        UserAIProviderConfig.provider_id == provider_id,
    ).first()

    raw_key = req.api_key.strip()
    keep_saved_key = (not raw_key) or raw_key == MASK_SENTINEL or "*" in raw_key
    if keep_saved_key:
        if not existing or not existing.encrypted_api_key:
            raise HTTPException(status_code=400, detail="API密钥不能为空")
        encrypted_key = existing.encrypted_api_key
    else:
        encrypted_key = encrypt_api_key(raw_key)

    if existing:
        provider = existing
    else:
        provider = UserAIProviderConfig(
            user_id=current_user.id,
            provider_id=provider_id,
        )
        db.add(provider)

    provider.name = (req.name or provider.name or _infer_provider_name(endpoint)).strip()
    provider.endpoint = endpoint
    provider.encrypted_api_key = encrypted_key
    provider.model = req.model.strip()
    provider.parsing_mode = req.parsing_mode or "generic"

    db.query(UserAIProviderConfig).filter(
        UserAIProviderConfig.user_id == current_user.id,
    ).update({"is_active": 0}, synchronize_session=False)
    provider.is_active = 1
    db.commit()
    return _response(db, current_user.id)


@router.post("/activate/{provider_id}", response_model=AIConfigResponse)
def activate_config(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = db.query(UserAIProviderConfig).filter(
        UserAIProviderConfig.user_id == current_user.id,
        UserAIProviderConfig.provider_id == provider_id,
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="AI配置不存在")
    if not provider.encrypted_api_key:
        raise HTTPException(status_code=400, detail="该配置还没有保存API密钥")
    db.query(UserAIProviderConfig).filter(
        UserAIProviderConfig.user_id == current_user.id,
    ).update({"is_active": 0}, synchronize_session=False)
    provider.is_active = 1
    db.commit()
    return _response(db, current_user.id)


@router.delete("/{provider_id}", response_model=AIConfigResponse)
def delete_config(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = db.query(UserAIProviderConfig).filter(
        UserAIProviderConfig.user_id == current_user.id,
        UserAIProviderConfig.provider_id == provider_id,
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="AI配置不存在")

    was_active = bool(provider.is_active)
    db.delete(provider)
    db.flush()
    if was_active:
        next_provider = db.query(UserAIProviderConfig).filter(
            UserAIProviderConfig.user_id == current_user.id,
        ).order_by(UserAIProviderConfig.updated_at.desc(), UserAIProviderConfig.id.desc()).first()
        if next_provider:
            next_provider.is_active = 1
    db.commit()
    return _response(db, current_user.id)


@router.post("/test")
def test_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = _active_provider(db, current_user.id)
    if not provider or not provider.encrypted_api_key:
        raise HTTPException(status_code=400, detail="请先配置当前账号的AI接口")

    client = build_ai_client(provider)
    result = client.test_connection()
    if result["success"]:
        return {"success": True, "latency": result["latency"], "model": client.model}
    raise HTTPException(status_code=400, detail=f"连接失败：{result['error']}")
