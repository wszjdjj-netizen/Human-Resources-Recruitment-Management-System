"""
AI接口客户端
兼容OpenAI格式的API调用（支持DeepSeek、通义千问、OpenAI等）
"""
import json
import re
import base64
import hashlib
import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.ai_config import UserAIProviderConfig
from app.security import normalize_public_http_url


class AIClient:
    """通用OpenAI兼容API客户端"""

    def __init__(self, endpoint: str = None, api_key: str = None, model: str = None):
        settings = get_settings()
        raw_endpoint = endpoint or settings.ai_endpoint
        self.endpoint = normalize_public_http_url(
            raw_endpoint,
            allow_private=settings.allow_private_network_urls,
            require_resolvable=True,
        )
        self.api_key = api_key or settings.ai_api_key
        self.model = model or settings.ai_model
        self._client = None

    @property
    def client(self) -> httpx.Client:
        """延迟创建HTTP客户端"""
        if self._client is None:
            self._client = httpx.Client(timeout=120.0)
        return self._client

    def chat(self, messages: list[dict], temperature: float = 0.3, max_tokens: int = 4096) -> str:
        """
        发送聊天请求并返回文本响应

        Args:
            messages: 消息列表，格式 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            temperature: 生成温度（0-1），越低越确定
            max_tokens: 最大生成token数

        Returns:
            AI返回的文本内容

        Raises:
            ValueError: 配置缺失
            httpx.HTTPError: 网络错误
        """
        if not self.api_key:
            raise ValueError("AI API密钥未配置，请在AI配置页面设置")

        url = f"{self.endpoint}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        response = self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def chat_json(self, messages: list[dict], temperature: float = 0.2) -> dict:
        """
        发送请求并解析为JSON对象

        用于简历解析、匹配打分等需要结构化输出的场景。
        """
        json_messages = list(messages)
        json_messages.append({
            "role": "system",
            "content": "最终输出必须是一个合法JSON对象，不能包含Markdown代码块、解释文字或JSON以外的内容。"
        })
        text = self.chat(json_messages, temperature=temperature)
        # 尝试提取JSON（有时AI会在JSON前后加说明文字）
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
        # 找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end + 1]
            return json.loads(json_str)
        raise ValueError(f"AI返回的内容无法解析为JSON: {text[:200]}...")

    def test_connection(self) -> dict:
        """测试API连接是否正常"""
        import time
        start = time.time()
        try:
            self.chat([
                {"role": "user", "content": "请回复：连接成功"}
            ], temperature=0, max_tokens=20)
            latency = int((time.time() - start) * 1000)
            return {"success": True, "latency": latency}
        except Exception as e:
            return {"success": False, "error": str(e)}


def _fernet() -> Fernet:
    settings = get_settings()
    key_material = settings.credential_encryption_key or settings.secret_key
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_value: str) -> str:
    if not encrypted_value:
        return ""
    try:
        return _fernet().decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("加密凭据无法解密，请重新保存配置")


def encrypt_api_key(api_key: str) -> str:
    return encrypt_secret(api_key)


def decrypt_api_key(encrypted_api_key: str) -> str:
    try:
        return decrypt_secret(encrypted_api_key)
    except ValueError:
        raise ValueError("AI密钥无法解密，请重新保存当前用户的AI配置")


def build_ai_client(provider: UserAIProviderConfig) -> AIClient:
    return AIClient(
        endpoint=provider.endpoint,
        api_key=decrypt_api_key(provider.encrypted_api_key),
        model=provider.model,
    )


def get_active_ai_provider(db: Session, user_id: int) -> UserAIProviderConfig | None:
    return db.query(UserAIProviderConfig).filter(
        UserAIProviderConfig.user_id == user_id,
        UserAIProviderConfig.is_active == 1,
    ).order_by(UserAIProviderConfig.updated_at.desc(), UserAIProviderConfig.id.desc()).first()


def get_user_ai_client(db: Session, user_id: int) -> AIClient:
    """Build an AI client from the current user's active provider."""
    provider = get_active_ai_provider(db, user_id)
    if provider:
        return build_ai_client(provider)

    settings = get_settings()
    if settings.allow_ai_env_fallback and settings.ai_api_key:
        return AIClient(
            endpoint=settings.ai_endpoint,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
        )

    raise ValueError("当前账号尚未配置AI接口，请先进入「AI配置」页面保存自己的API Key")
