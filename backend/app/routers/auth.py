"""
认证路由：注册、登录、获取用户信息
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse, UserUpdateRequest
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.middleware.jwt_middleware import get_current_user
from app.security import check_rate_limit, get_client_ip, validate_password_strength

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.jwt_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
    )


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """用户注册"""
    settings = get_settings()
    client_ip = get_client_ip(request)
    check_rate_limit(
        f"register:{client_ip}",
        limit=settings.auth_register_rate_limit,
        window_seconds=settings.auth_register_rate_window_seconds,
        detail="注册尝试过于频繁，请稍后再试",
    )
    invite_code = (req.invite_code or "").strip()
    required_invite = (settings.registration_invite_code or "").strip()
    if required_invite and invite_code != required_invite:
        raise HTTPException(status_code=403, detail="注册邀请码不正确")
    if not settings.allow_public_registration and not required_invite:
        raise HTTPException(status_code=403, detail="当前系统已关闭公开注册，请联系管理员开通账号")

    # 检查用户名是否已存在
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    email = str(req.email).strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    validate_password_strength(req.password)

    # 创建用户
    user = User(
        username=req.username,
        email=email,
        hashed_password=hash_password(req.password),
        company_name=req.company_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 生成Token
    token = create_access_token(user.id, user.username)
    _set_auth_cookie(response, token)

    return TokenResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        company_name=user.company_name,
        token=""
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """用户登录（支持用户名或邮箱）"""
    ident = req.username.strip()
    settings = get_settings()
    client_ip = get_client_ip(request)
    check_rate_limit(
        f"login:{client_ip}:{ident.lower()}",
        limit=settings.auth_login_rate_limit,
        window_seconds=settings.auth_login_rate_window_seconds,
        detail="登录尝试过于频繁，请稍后再试",
    )
    user = db.query(User).filter(
        (User.username == ident) | (User.email == ident)
    ).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(user.id, user.username)
    _set_auth_cookie(response, token)

    return TokenResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        company_name=user.company_name,
        token=""
    )


@router.post("/logout")
def logout(response: Response):
    _clear_auth_cookie(response)
    return {"message": "已退出登录"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        company_name=current_user.company_name
    )


@router.put("/me", response_model=UserResponse)
def update_me(
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新当前登录用户资料"""
    return _update_current_user(req, db, current_user)


@router.post("/me/update", response_model=UserResponse)
def update_me_compat(
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新当前登录用户资料（兼容不支持PUT的代理/缓存环境）"""
    return _update_current_user(req, db, current_user)


def _update_current_user(req: UserUpdateRequest, db: Session, current_user: User) -> UserResponse:
    username = req.username.strip()
    email = str(req.email).strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if not email:
        raise HTTPException(status_code=400, detail="邮箱不能为空")
    company_name = req.company_name.strip() if req.company_name else None

    if db.query(User).filter(User.username == username, User.id != current_user.id).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.query(User).filter(User.email == email, User.id != current_user.id).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    if req.new_password:
        if not req.current_password:
            raise HTTPException(status_code=400, detail="修改密码需要输入当前密码")
        if not verify_password(req.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="当前密码不正确")
        validate_password_strength(req.new_password)
        current_user.hashed_password = hash_password(req.new_password)

    current_user.username = username
    current_user.email = email
    current_user.company_name = company_name
    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        company_name=current_user.company_name
    )
