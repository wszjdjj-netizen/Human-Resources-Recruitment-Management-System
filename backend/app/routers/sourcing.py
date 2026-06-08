"""
平台搜人路由

生产形态：
- 网站负责创建任务、审批外联、查看日志/截图
- 本地 browser runner 负责登录平台、搜索、抓取候选人并回传
"""
from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.middleware.jwt_middleware import get_current_user
from app.models.position import Position
from app.models.sourcing import (
    SourcingOutreach,
    SourcingOutreachAudit,
    SourcingPlatformAccount,
    SourcingTask,
    SourcingTaskLog,
    SourcingTaskScreenshot,
)
from app.models.user import User
from app.schemas.sourcing import (
    OutreachReviewRequest,
    PlatformAccount,
    PlatformAccountUpsert,
    RunnerCandidateBatchResult,
    RunnerCandidateBatchUpsert,
    RunnerOutreachDeliveryUpdate,
    RunnerScreenshotCreate,
    RunnerTaskContext,
    RunnerTaskLogCreate,
    RunnerTaskStatusUpdate,
    SourcingTaskCreate,
    SourcingTaskDetail,
    SourcingTaskResponse,
    TaskLaunchResponse,
)
from app.services.sourcing_runtime import (
    OUTREACH_REVIEW_APPROVED,
    OUTREACH_REVIEW_PENDING,
    OUTREACH_REVIEW_SKIPPED,
    OUTREACH_STATUS_FAILED,
    OUTREACH_STATUS_PENDING,
    OUTREACH_STATUS_REPLIED,
    OUTREACH_STATUS_SKIPPED,
    OUTREACH_STATUS_SENT,
    TASK_STATUS_DONE,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_RUNNING,
    TASK_STATUS_WAIT_CAPTCHA,
    TASK_STATUS_WAIT_CONFIRM,
    TASK_STATUS_WAIT_LOGIN,
    build_runner_context,
    build_task_detail,
    issue_runner_token,
    normalize_platforms,
    record_outreach_audit,
    record_task_log,
    save_task_screenshot,
    serialize_platform_account,
    serialize_task,
    set_task_status,
    split_platforms,
    task_counts,
    verify_runner_token,
    import_runner_candidates,
)
from app.services.ai_client import encrypt_secret

router = APIRouter(prefix="/api/sourcing", tags=["平台搜人"])

PLATFORMS = ["BOSS直聘", "猎聘", "领英", "脉脉"]


def _get_position_or_404(position_id: int, db: Session, current_user: User) -> Position:
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id,
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    return position


def _get_task_or_404(task_id: int, db: Session, current_user: User) -> SourcingTask:
    task = db.query(SourcingTask).filter(
        SourcingTask.id == task_id,
        SourcingTask.user_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="搜人任务不存在")
    return task


def _get_runner_task_dependency(
    task_id: int,
    authorization: str | None = Header(None),
    x_runner_token: str | None = Header(None),
    x_runner_session_id: str | None = Header(None),
    db: Session = Depends(get_db),
) -> SourcingTask:
    raw_token = _extract_runner_token(authorization, x_runner_token)
    task = db.query(SourcingTask).filter(SourcingTask.id == task_id).first()
    if not task or not verify_runner_token(task, raw_token, x_runner_session_id):
        raise HTTPException(status_code=401, detail="runner token 无效")
    return task


def _extract_runner_token(authorization: str | None, x_runner_token: str | None) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if x_runner_token:
        return x_runner_token.strip()
    raise HTTPException(status_code=401, detail="缺少 runner token")


def _json_dump(payload: dict | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False)


def _public_backend_base_url(request: Request) -> str:
    settings = get_settings()
    configured = (settings.public_backend_url or "").strip().rstrip("/")
    if configured:
        return configured
    return str(request.base_url).rstrip("/")


LOCAL_RUNNER_URL = "http://127.0.0.1:18765/launch"

RUNNER_PACKAGE_FILES = [
    ("start-local-runner.bat", "start-local-runner.bat"),
    ("register-runner-protocol.bat", "register-runner-protocol.bat"),
    ("register-runner-protocol.ps1", "register-runner-protocol.ps1"),
    ("backend/runner-requirements.txt", "backend/runner-requirements.txt"),
    ("backend/app/__init__.py", "backend/app/__init__.py"),
    ("backend/app/local_runner/__init__.py", "backend/app/local_runner/__init__.py"),
    ("backend/app/local_runner/main.py", "backend/app/local_runner/main.py"),
    ("backend/app/local_runner/runtime.py", "backend/app/local_runner/runtime.py"),
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _runner_package_readme() -> str:
    return """招聘系统本地执行器

用途：
- 平台搜人必须在使用者自己的电脑上打开浏览器执行，适合处理 BOSS 直聘等平台的登录、验证码和风控。
- 线上网站负责创建任务、审批、日志、截图和入库；本地执行器负责真实浏览器操作。

第一次使用：
1. 解压整个 zip，不要只拖出单个 bat 文件。
2. 双击 start-local-runner.bat。
3. 首次启动会自动安装 Python 依赖和 Playwright Chromium，可能需要几分钟。
4. 如果想在网页里点“一键唤起执行器”，再双击一次 register-runner-protocol.bat。
5. 不要删除 register-runner-protocol.ps1，它是 register-runner-protocol.bat 注册协议时需要调用的辅助文件。

日常使用：
1. 登录线上招聘系统。
2. 进入“平台搜人”。
3. 如本地执行器未启动，先双击 start-local-runner.bat，或点击网页的一键唤起按钮。
4. 创建任务并启动，本地浏览器会弹出并执行平台登录、搜索和回传。

注意：
- 127.0.0.1 表示当前打开网页的这台电脑，不是服务器。
- BOSS 等平台出现验证码或扫码时，请在弹出的本地浏览器里手动完成。
- 浏览器出于安全原因不能完全静默启动本机程序；协议注册后仍可能弹出确认框。
"""


@router.get("/runner-package")
def download_runner_package(
    current_user: User = Depends(get_current_user),
):
    """下载给 HR 本机使用的最小 runner 包。

    包内不包含用户密钥或任务 token；任务 token 只在点击启动任务时临时下发。
    """
    root = _project_root()
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", _runner_package_readme())
        for source, target in RUNNER_PACKAGE_FILES:
            path = root / source
            if not path.exists():
                raise HTTPException(status_code=500, detail=f"本地执行器文件缺失：{source}")
            archive.write(path, target)
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="recruitment-local-runner.zip"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/platforms", response_model=list[PlatformAccount])
def list_platforms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    saved = db.query(SourcingPlatformAccount).filter(
        SourcingPlatformAccount.user_id == current_user.id
    ).all()
    saved_map = {item.platform: item for item in saved}
    username = current_user.username or "hr"
    return [
        serialize_platform_account(saved_map.get(platform), platform, username)
        for platform in PLATFORMS
    ]


@router.post("/platforms", response_model=PlatformAccount)
def save_platform_account(
    req: PlatformAccountUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.platform not in PLATFORMS:
        raise HTTPException(status_code=400, detail="暂不支持该平台")

    account = db.query(SourcingPlatformAccount).filter(
        SourcingPlatformAccount.user_id == current_user.id,
        SourcingPlatformAccount.platform == req.platform,
    ).first()
    if not account:
        account = SourcingPlatformAccount(user_id=current_user.id, platform=req.platform)
        db.add(account)

    account.account_name = req.account_name or f"{current_user.username}@{req.platform}"
    account.auth_type = req.auth_type
    account.credential = encrypt_secret(req.credential) if req.credential else None
    account.status = "已连接" if req.credential else "未连接"
    account.last_sync = datetime.now() if req.credential else None
    db.commit()
    db.refresh(account)
    return serialize_platform_account(account, account.platform, current_user.username or "hr")


@router.get("/tasks", response_model=list[SourcingTaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(SourcingTask, Position).join(
        Position, Position.id == SourcingTask.position_id
    ).filter(
        SourcingTask.user_id == current_user.id
    ).order_by(
        SourcingTask.created_at.desc(),
        SourcingTask.id.desc(),
    ).all()
    return [serialize_task(db, task, position) for task, position in rows]


@router.post("/tasks", response_model=SourcingTaskResponse)
def create_task(
    req: SourcingTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    position = _get_position_or_404(req.position_id, db, current_user)
    platforms = normalize_platforms(req.platforms, PLATFORMS)
    task = SourcingTask(
        user_id=current_user.id,
        position_id=position.id,
        name=req.name or f"{position.title} 平台搜人",
        platforms=",".join(platforms),
        keywords=req.keywords,
        locations=req.locations,
        min_score=req.min_score,
        target_count=req.target_count,
        auto_greeting=1 if req.auto_greeting else 0,
        greeting_template=req.greeting_template,
        status=TASK_STATUS_PENDING,
        status_detail="等待启动本地执行器",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    record_task_log(
        db,
        task=task,
        user_id=current_user.id,
        level="info",
        stage="task",
        message="已创建平台搜人任务",
        detail=f"目标岗位：{position.title}；平台：{', '.join(platforms)}",
    )
    db.commit()
    return serialize_task(db, task, position)


@router.get("/tasks/{task_id}", response_model=SourcingTaskDetail)
def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db, current_user)
    position = _get_position_or_404(task.position_id, db, current_user)
    return build_task_detail(db, task, position)


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db, current_user)

    # 删除关联的截图文件
    screenshots = db.query(SourcingTaskScreenshot).filter(
        SourcingTaskScreenshot.task_id == task.id,
        SourcingTaskScreenshot.user_id == current_user.id,
    ).all()
    for ss in screenshots:
        fp = Path(ss.file_path)
        if fp.exists():
            fp.unlink(missing_ok=True)

    # 删除关联数据（按依赖顺序）
    db.query(SourcingOutreachAudit).filter(SourcingOutreachAudit.task_id == task.id).delete()
    db.query(SourcingOutreach).filter(SourcingOutreach.task_id == task.id).delete()
    db.query(SourcingTaskScreenshot).filter(SourcingTaskScreenshot.task_id == task.id).delete()
    db.query(SourcingTaskLog).filter(SourcingTaskLog.task_id == task.id).delete()

    # 删除任务本身
    db.delete(task)
    db.commit()
    return {"message": f"任务「{task.name}」已删除"}


@router.delete("/tasks")
def batch_delete_tasks(
    task_ids: list[int] = Query(..., description="要删除的任务ID列表"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除搜人任务（一次请求完成，便于前端汇总结果）"""
    if not task_ids:
        raise HTTPException(status_code=400, detail="请提供要删除的任务ID列表")
    if len(task_ids) > 50:
        raise HTTPException(status_code=400, detail="单次最多删除50个任务")

    tasks = db.query(SourcingTask).filter(
        SourcingTask.id.in_(task_ids),
        SourcingTask.user_id == current_user.id,
    ).all()
    if not tasks:
        raise HTTPException(status_code=404, detail="未找到要删除的任务")

    deleted_names = []
    failed = []
    for task in tasks:
        try:
            # 删除关联的截图文件
            screenshots = db.query(SourcingTaskScreenshot).filter(
                SourcingTaskScreenshot.task_id == task.id,
            ).all()
            for ss in screenshots:
                fp = Path(ss.file_path)
                if fp.exists():
                    fp.unlink(missing_ok=True)
            # 删除关联数据
            db.query(SourcingOutreachAudit).filter(SourcingOutreachAudit.task_id == task.id).delete()
            db.query(SourcingOutreach).filter(SourcingOutreach.task_id == task.id).delete()
            db.query(SourcingTaskScreenshot).filter(SourcingTaskScreenshot.task_id == task.id).delete()
            db.query(SourcingTaskLog).filter(SourcingTaskLog.task_id == task.id).delete()
            db.delete(task)
            deleted_names.append(task.name)
        except Exception as e:
            failed.append(f"#{task.id}: {e}")
    db.commit()
    return {
        "message": f"已删除 {len(deleted_names)} 个任务" + (f"，{len(failed)} 个失败" if failed else ""),
        "deleted_count": len(deleted_names),
        "deleted_names": deleted_names,
        "failed": failed
    }


@router.post("/tasks/{task_id}/run", response_model=TaskLaunchResponse)
def launch_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db, current_user)
    position = _get_position_or_404(task.position_id, db, current_user)
    raw_token, session_id, expires_at = issue_runner_token(task)
    record_task_log(
        db,
        task=task,
        user_id=current_user.id,
        level="info",
        stage="launch",
        message="已生成本地执行器启动令牌",
        detail=f"任务：{task.name}；岗位：{position.title}",
    )
    db.commit()
    backend_base_url = _public_backend_base_url(request)
    return {
        "task_id": task.id,
        "status": task.status,
        "local_runner_url": LOCAL_RUNNER_URL,
        "backend_base_url": backend_base_url,
        "runner_token": raw_token,
        "session_id": session_id,
        "expires_at": expires_at.isoformat(),
    }


@router.post("/tasks/{task_id}/outreach/{outreach_id}/review")
def review_outreach(
    task_id: int,
    outreach_id: int,
    req: OutreachReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db, current_user)
    outreach = db.query(SourcingOutreach).filter(
        SourcingOutreach.id == outreach_id,
        SourcingOutreach.task_id == task.id,
        SourcingOutreach.user_id == current_user.id,
    ).first()
    if not outreach:
        raise HTTPException(status_code=404, detail="外联记录不存在")

    if req.action == "approve":
        outreach.review_status = OUTREACH_REVIEW_APPROVED
        outreach.approved_by_user_id = current_user.id
        outreach.approved_at = datetime.now()
        record_outreach_audit(
            db,
            task=task,
            user_id=current_user.id,
            actor_type="user",
            action="approved",
            detail=f"HR 已批准发送外联消息（outreach #{outreach.id}）",
            outreach_id=outreach.id,
        )
    else:
        outreach.review_status = OUTREACH_REVIEW_SKIPPED
        outreach.status = OUTREACH_STATUS_SKIPPED
        outreach.failure_reason = "HR 手动跳过"
        outreach.approved_by_user_id = current_user.id
        outreach.approved_at = datetime.now()
        record_outreach_audit(
            db,
            task=task,
            user_id=current_user.id,
            actor_type="user",
            action="skipped",
            detail=f"HR 已跳过外联消息（outreach #{outreach.id}）",
            outreach_id=outreach.id,
        )

    db.flush()
    counts = task_counts(db, task)
    if counts["pending_outreach_count"] > 0:
        task.status = TASK_STATUS_WAIT_CONFIRM
        task.pending_action = "confirm_send"
        task.status_detail = "仍有候选人待确认发送"
    else:
        task.status = TASK_STATUS_RUNNING
        task.pending_action = None
        task.status_detail = "已更新外联审批，等待本地执行器继续发送"

    db.commit()
    return {"message": "外联审批已更新"}


@router.get("/tasks/{task_id}/screenshots/{screenshot_id}/image")
def get_screenshot_image(
    task_id: int,
    screenshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db, current_user)
    screenshot = db.query(SourcingTaskScreenshot).filter(
        SourcingTaskScreenshot.id == screenshot_id,
        SourcingTaskScreenshot.task_id == task.id,
        SourcingTaskScreenshot.user_id == current_user.id,
    ).first()
    if not screenshot:
        raise HTTPException(status_code=404, detail="截图不存在")
    path = Path(screenshot.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="截图文件不存在")
    return FileResponse(path, media_type=screenshot.mime_type)


@router.post("/search")
def search_endpoint_deprecated():
    raise HTTPException(
        status_code=400,
        detail="平台搜人已切换为本地执行器模式，请先创建任务，再在工作台中启动本地 runner。",
    )


@router.get("/runner/tasks/{task_id}", response_model=RunnerTaskContext)
def get_runner_task_context(
    task_id: int,
    db: Session = Depends(get_db),
    task: SourcingTask = Depends(_get_runner_task_dependency),
):
    if task.id != task_id:
        raise HTTPException(status_code=403, detail="runner token 与任务不匹配")
    user = db.query(User).filter(User.id == task.user_id).first()
    position = db.query(Position).filter(Position.id == task.position_id).first()
    if not user or not position:
        raise HTTPException(status_code=404, detail="任务上下文不存在")
    accounts = db.query(SourcingPlatformAccount).filter(
        SourcingPlatformAccount.user_id == user.id,
        SourcingPlatformAccount.platform.in_(split_platforms(task.platforms)),
    ).all()
    return build_runner_context(db, task=task, position=position, accounts=accounts)


@router.post("/runner/tasks/{task_id}/status")
def runner_update_status(
    task_id: int,
    req: RunnerTaskStatusUpdate,
    db: Session = Depends(get_db),
    task: SourcingTask = Depends(_get_runner_task_dependency),
):
    if task.id != task_id:
        raise HTTPException(status_code=403, detail="runner token 与任务不匹配")

    set_task_status(
        task,
        status=req.status,
        status_detail=req.status_detail,
        pending_action=req.pending_action,
        current_platform=req.current_platform,
        runner_name=req.runner_name,
        last_error=req.last_error,
        finished=req.finished,
    )
    if req.status == TASK_STATUS_DONE and task.pending_action == "confirm_send":
        task.status = TASK_STATUS_WAIT_CONFIRM
    if req.status == TASK_STATUS_FAILED and req.last_error:
        record_task_log(
            db,
            task=task,
            user_id=task.user_id,
            level="error",
            stage="runner",
            message="本地执行器上报失败",
            detail=req.last_error,
        )
    db.commit()
    return {"message": "状态已更新"}


@router.post("/runner/tasks/{task_id}/logs")
def runner_add_log(
    task_id: int,
    req: RunnerTaskLogCreate,
    db: Session = Depends(get_db),
    task: SourcingTask = Depends(_get_runner_task_dependency),
):
    if task.id != task_id:
        raise HTTPException(status_code=403, detail="runner token 与任务不匹配")
    record_task_log(
        db,
        task=task,
        user_id=task.user_id,
        level=req.level,
        stage=req.stage,
        message=req.message,
        detail=req.detail,
    )
    task.last_heartbeat = datetime.now()
    db.commit()
    return {"message": "日志已记录"}


@router.post("/runner/tasks/{task_id}/screenshots")
def runner_add_screenshot(
    task_id: int,
    req: RunnerScreenshotCreate,
    db: Session = Depends(get_db),
    task: SourcingTask = Depends(_get_runner_task_dependency),
):
    if task.id != task_id:
        raise HTTPException(status_code=403, detail="runner token 与任务不匹配")
    save_task_screenshot(
        db,
        task=task,
        user_id=task.user_id,
        content_base64=req.content_base64,
        mime_type=req.mime_type,
        stage=req.stage,
        caption=req.caption,
        source_url=req.source_url,
    )
    task.last_heartbeat = datetime.now()
    db.commit()
    return {"message": "截图已保存"}


@router.delete("/tasks/{task_id}/logs")
def clear_task_logs(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db, current_user)
    deleted = db.query(SourcingTaskLog).filter(
        SourcingTaskLog.task_id == task_id,
        SourcingTaskLog.user_id == current_user.id,
    ).delete()
    db.commit()
    return {"message": f"已清除 {deleted} 条日志"}


@router.delete("/tasks/{task_id}/logs/{log_id}")
def delete_single_log(
    task_id: int,
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db, current_user)
    result = db.query(SourcingTaskLog).filter(
        SourcingTaskLog.id == log_id,
        SourcingTaskLog.task_id == task_id,
        SourcingTaskLog.user_id == current_user.id,
    ).delete()
    if not result:
        raise HTTPException(status_code=404, detail="日志记录不存在")
    db.commit()
    return {"message": "日志已删除"}


@router.delete("/tasks/{task_id}/screenshots")
def clear_task_screenshots(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db, current_user)
    screenshots = db.query(SourcingTaskScreenshot).filter(
        SourcingTaskScreenshot.task_id == task_id,
        SourcingTaskScreenshot.user_id == current_user.id,
    ).all()
    for ss in screenshots:
        from pathlib import Path
        fp = Path(ss.file_path)
        if fp.exists():
            fp.unlink(missing_ok=True)
    deleted = db.query(SourcingTaskScreenshot).filter(
        SourcingTaskScreenshot.task_id == task_id,
        SourcingTaskScreenshot.user_id == current_user.id,
    ).delete()
    db.commit()
    return {"message": f"已清除 {deleted} 张截图"}


@router.delete("/tasks/{task_id}/screenshots/{screenshot_id}")
def delete_single_screenshot(
    task_id: int,
    screenshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task_or_404(task_id, db, current_user)
    ss = db.query(SourcingTaskScreenshot).filter(
        SourcingTaskScreenshot.id == screenshot_id,
        SourcingTaskScreenshot.task_id == task_id,
        SourcingTaskScreenshot.user_id == current_user.id,
    ).first()
    if not ss:
        raise HTTPException(status_code=404, detail="截图不存在")
    from pathlib import Path
    fp = Path(ss.file_path)
    if fp.exists():
        fp.unlink(missing_ok=True)
    db.delete(ss)
    db.commit()
    return {"message": "截图已删除"}


@router.get("/positions/{position_id}/logs")
def get_position_logs(
    position_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    position = _get_position_or_404(position_id, db, current_user)
    task_ids = [t.id for t in db.query(SourcingTask.id).filter(
        SourcingTask.position_id == position_id,
        SourcingTask.user_id == current_user.id,
    ).all()]
    if not task_ids:
        return []
    logs = db.query(SourcingTaskLog).filter(
        SourcingTaskLog.task_id.in_(task_ids),
        SourcingTaskLog.user_id == current_user.id,
    ).order_by(SourcingTaskLog.created_at.desc(), SourcingTaskLog.id.desc()).limit(limit).all()
    return [serialize_log(item) for item in logs]


@router.get("/positions/{position_id}/screenshots")
def get_position_screenshots(
    position_id: int,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    position = _get_position_or_404(position_id, db, current_user)
    task_ids = [t.id for t in db.query(SourcingTask.id).filter(
        SourcingTask.position_id == position_id,
        SourcingTask.user_id == current_user.id,
    ).all()]
    if not task_ids:
        return []
    screenshots = db.query(SourcingTaskScreenshot).filter(
        SourcingTaskScreenshot.task_id.in_(task_ids),
        SourcingTaskScreenshot.user_id == current_user.id,
    ).order_by(SourcingTaskScreenshot.created_at.desc(), SourcingTaskScreenshot.id.desc()).limit(limit).all()
    return [serialize_screenshot(item) for item in screenshots]


@router.post("/runner/tasks/{task_id}/candidates/batch", response_model=RunnerCandidateBatchResult)
def runner_import_candidates(
    task_id: int,
    req: RunnerCandidateBatchUpsert,
    db: Session = Depends(get_db),
    task: SourcingTask = Depends(_get_runner_task_dependency),
):
    if task.id != task_id:
        raise HTTPException(status_code=403, detail="runner token 与任务不匹配")
    user = db.query(User).filter(User.id == task.user_id).first()
    position = db.query(Position).filter(Position.id == task.position_id).first()
    if not user or not position:
        raise HTTPException(status_code=404, detail="任务上下文不存在")

    result = import_runner_candidates(
        db,
        task=task,
        position=position,
        current_user=user,
        payloads=[item.model_dump() for item in req.candidates],
    )
    record_task_log(
        db,
        task=task,
        user_id=user.id,
        level="info",
        stage="import",
        message="本地执行器已回传候选人批次",
        detail=(
            f"入库 {result['imported_count']} 人，"
            f"重复 {result['duplicate_count']} 人，"
            f"低于阈值 {result['filtered_count']} 人"
        ),
    )
    db.commit()
    return result


@router.post("/runner/tasks/{task_id}/outreach/{outreach_id}/delivery")
def runner_update_outreach_delivery(
    task_id: int,
    outreach_id: int,
    req: RunnerOutreachDeliveryUpdate,
    db: Session = Depends(get_db),
    task: SourcingTask = Depends(_get_runner_task_dependency),
):
    if task.id != task_id:
        raise HTTPException(status_code=403, detail="runner token 与任务不匹配")
    outreach = db.query(SourcingOutreach).filter(
        SourcingOutreach.id == outreach_id,
        SourcingOutreach.task_id == task.id,
    ).first()
    if not outreach:
        raise HTTPException(status_code=404, detail="外联记录不存在")

    if req.status == "sent":
        if outreach.status != OUTREACH_STATUS_SENT:
            task.contacted_count += 1
        outreach.status = OUTREACH_STATUS_SENT
        outreach.sent_at = datetime.now()
        outreach.external_message_id = req.external_message_id
        outreach.external_thread_id = req.external_thread_id
        outreach.delivery_payload = _json_dump(req.payload)
        record_outreach_audit(
            db,
            task=task,
            user_id=task.user_id,
            actor_type="runner",
            action="sent",
            detail=req.detail or "本地执行器已完成发送",
            outreach_id=outreach.id,
            payload=req.payload,
        )
    elif req.status == "failed":
        outreach.status = OUTREACH_STATUS_FAILED
        outreach.failure_reason = req.detail
        outreach.delivery_payload = _json_dump(req.payload)
        record_outreach_audit(
            db,
            task=task,
            user_id=task.user_id,
            actor_type="runner",
            action="failed",
            detail=req.detail or "发送失败",
            outreach_id=outreach.id,
            payload=req.payload,
        )
    else:
        outreach.status = OUTREACH_STATUS_REPLIED
        outreach.external_message_id = req.external_message_id
        outreach.external_thread_id = req.external_thread_id
        outreach.delivery_payload = _json_dump(req.payload)
        record_outreach_audit(
            db,
            task=task,
            user_id=task.user_id,
            actor_type="runner",
            action="replied",
            detail=req.detail or "候选人已回复",
            outreach_id=outreach.id,
            payload=req.payload,
        )

    task.last_heartbeat = datetime.now()
    db.commit()
    return {"message": "外联回执已更新"}
