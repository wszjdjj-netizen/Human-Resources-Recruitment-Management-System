"""
认证相关的Pydantic模型
"""
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: EmailStr = Field(..., max_length=100, description="邮箱")
    password: str = Field(..., min_length=8, max_length=100, description="密码")
    company_name: str | None = Field(None, max_length=100, description="公司名称(选填)")
    invite_code: str | None = Field(None, max_length=100, description="注册邀请码")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str
    company_name: str | None = None


class UserUpdateRequest(BaseModel):
    """当前用户资料更新请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: EmailStr = Field(..., max_length=100, description="邮箱")
    company_name: str | None = Field(None, max_length=100, description="公司名称")
    current_password: str | None = Field(None, max_length=100, description="当前密码")
    new_password: str | None = Field(None, min_length=8, max_length=100, description="新密码")


class TokenResponse(BaseModel):
    """登录/注册后返回的Token"""
    id: int
    username: str
    email: str
    company_name: str | None = None
    token: str
