"""
平台搜人相关模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class SourcingPlatformAccount(Base):
    __tablename__ = "sourcing_platform_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String(50), nullable=False, comment="平台名称")
    account_name = Column(String(120), nullable=True, comment="账号展示名称")
    auth_type = Column(String(30), nullable=False, default="cookie", comment="cookie/oauth/manual")
    credential = Column(Text, nullable=True, comment="加密后的Cookie/OAuth Token/平台凭据")
    status = Column(String(30), nullable=False, default="未连接", comment="未连接/已连接/已失效")
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SourcingTask(Base):
    __tablename__ = "sourcing_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    name = Column(String(200), nullable=False)
    platforms = Column(String(300), nullable=False, comment="逗号分隔的平台列表")
    keywords = Column(String(500), nullable=True)
    locations = Column(String(300), nullable=True)
    min_score = Column(Integer, nullable=False, default=60)
    target_count = Column(Integer, nullable=False, default=20)
    auto_greeting = Column(Integer, nullable=False, default=0)
    greeting_template = Column(Text, nullable=True)
    status = Column(
        String(30),
        nullable=False,
        default="待运行",
        comment="待运行/待登录/待验证码/待确认发送/运行中/完成/失败",
    )
    status_detail = Column(Text, nullable=True, comment="状态补充说明")
    pending_action = Column(String(50), nullable=True, comment="login/captcha/confirm_send/manual_review")
    current_platform = Column(String(50), nullable=True, comment="当前执行平台")
    imported_count = Column(Integer, nullable=False, default=0)
    reviewed_count = Column(Integer, nullable=False, default=0)
    deduped_count = Column(Integer, nullable=False, default=0)
    contacted_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    runner_session_id = Column(String(120), nullable=True)
    runner_name = Column(String(120), nullable=True)
    runner_token_hash = Column(String(128), nullable=True)
    runner_token_expires_at = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SourcingOutreach(Base):
    __tablename__ = "sourcing_outreach"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("sourcing_tasks.id"), nullable=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    platform = Column(String(50), nullable=False)
    platform_candidate_id = Column(String(200), nullable=True, comment="平台侧候选人ID")
    profile_url = Column(String(500), nullable=True, comment="候选人平台链接")
    message = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="待发送", comment="待发送/已发送/发送失败/已跳过/已回复")
    review_status = Column(String(30), nullable=False, default="待确认", comment="待确认/已批准/已跳过")
    external_message_id = Column(String(200), nullable=True)
    external_thread_id = Column(String(200), nullable=True)
    failure_reason = Column(Text, nullable=True)
    delivery_payload = Column(Text, nullable=True, comment="发送回执或补充上下文")
    approved_by_user_id = Column(Integer, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SourcingTaskLog(Base):
    __tablename__ = "sourcing_task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("sourcing_tasks.id"), nullable=False)
    runner_session_id = Column(String(120), nullable=True)
    level = Column(String(20), nullable=False, default="info")
    stage = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SourcingTaskScreenshot(Base):
    __tablename__ = "sourcing_task_screenshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("sourcing_tasks.id"), nullable=False)
    stage = Column(String(50), nullable=True)
    caption = Column(String(300), nullable=True)
    mime_type = Column(String(50), nullable=False, default="image/png")
    file_path = Column(String(500), nullable=False)
    source_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SourcingOutreachAudit(Base):
    __tablename__ = "sourcing_outreach_audits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("sourcing_tasks.id"), nullable=False)
    outreach_id = Column(Integer, ForeignKey("sourcing_outreach.id"), nullable=True)
    actor_type = Column(String(30), nullable=False, default="system", comment="user/runner/system")
    action = Column(String(50), nullable=False, comment="created/approved/skipped/sent/failed/replied")
    detail = Column(Text, nullable=True)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
