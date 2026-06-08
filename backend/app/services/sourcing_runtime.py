"""
平台搜人运行时服务：
- 任务状态机与日志
- 截图落盘
- runner token 鉴权
- 候选人去重、解析、评分、外联审计
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import uuid
from binascii import Error as Base64Error
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.candidate import Candidate
from app.models.education import CandidateEducation
from app.models.experience import CandidateExperience
from app.models.match_result import MatchResult
from app.models.position import Position
from app.models.skill import CandidateSkill
from app.models.sourcing import (
    SourcingOutreach,
    SourcingOutreachAudit,
    SourcingPlatformAccount,
    SourcingTask,
    SourcingTaskLog,
    SourcingTaskScreenshot,
)
from app.models.user import User
from app.services.ai_matcher import match_candidate_to_position
from app.services.ai_client import decrypt_secret
from app.services.resume_parser import parse_resume
from app.utils.file_handler import get_upload_dir

TASK_STATUS_PENDING = "待运行"
TASK_STATUS_WAIT_LOGIN = "待登录"
TASK_STATUS_WAIT_CAPTCHA = "待验证码"
TASK_STATUS_WAIT_CONFIRM = "待确认发送"
TASK_STATUS_RUNNING = "运行中"
TASK_STATUS_DONE = "完成"
TASK_STATUS_FAILED = "失败"

OUTREACH_REVIEW_PENDING = "待确认"
OUTREACH_REVIEW_APPROVED = "已批准"
OUTREACH_REVIEW_SKIPPED = "已跳过"

OUTREACH_STATUS_PENDING = "待发送"
OUTREACH_STATUS_SENT = "已发送"
OUTREACH_STATUS_FAILED = "发送失败"
OUTREACH_STATUS_SKIPPED = "已跳过"
OUTREACH_STATUS_REPLIED = "已回复"


def split_platforms(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_platforms(platforms: list[str] | None, allowed: list[str]) -> list[str]:
    normalized = [item for item in (platforms or allowed) if item in allowed]
    return normalized or allowed


def mask_credential(value: str | None) -> bool:
    return bool(value and value.strip())


def decrypt_platform_credential(value: str | None) -> str | None:
    if not value:
        return value
    try:
        return decrypt_secret(value)
    except ValueError:
        return value


def hash_runner_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_runner_token(task: SourcingTask) -> tuple[str, str, datetime]:
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(minutes=get_settings().runner_token_ttl_minutes)
    task.runner_token_hash = hash_runner_token(raw_token)
    task.runner_session_id = uuid.uuid4().hex
    task.runner_token_expires_at = expires_at
    task.runner_name = None
    task.last_heartbeat = None
    task.started_at = None
    task.completed_at = None
    task.last_error = None
    task.status = TASK_STATUS_PENDING
    task.status_detail = "等待本地执行器连接"
    task.pending_action = None
    task.current_platform = None
    return raw_token, task.runner_session_id, expires_at


def verify_runner_token(task: SourcingTask, raw_token: str, session_id: str | None = None) -> bool:
    if not task.runner_token_hash or not raw_token:
        return False
    if session_id and task.runner_session_id and not secrets.compare_digest(task.runner_session_id, session_id):
        return False
    if task.runner_token_expires_at and task.runner_token_expires_at < datetime.now():
        return False
    return secrets.compare_digest(task.runner_token_hash, hash_runner_token(raw_token))


def revoke_runner_token(task: SourcingTask) -> None:
    task.runner_token_hash = None
    task.runner_session_id = None
    task.runner_token_expires_at = None


def set_task_status(
    task: SourcingTask,
    *,
    status: str,
    status_detail: str | None = None,
    pending_action: str | None = None,
    current_platform: str | None = None,
    runner_name: str | None = None,
    last_error: str | None = None,
    finished: bool = False,
):
    task.status = status
    task.status_detail = status_detail
    task.pending_action = pending_action
    if current_platform is not None:
        task.current_platform = current_platform
    if runner_name is not None:
        task.runner_name = runner_name
    if last_error is not None:
        task.last_error = last_error
    task.last_heartbeat = datetime.now()
    if not task.started_at and status in {TASK_STATUS_RUNNING, TASK_STATUS_WAIT_LOGIN, TASK_STATUS_WAIT_CAPTCHA}:
        task.started_at = datetime.now()
    if finished:
        task.completed_at = datetime.now()
        revoke_runner_token(task)


def record_task_log(
    db: Session,
    *,
    task: SourcingTask,
    user_id: int,
    level: str,
    message: str,
    stage: str | None = None,
    detail: str | None = None,
) -> SourcingTaskLog:
    item = SourcingTaskLog(
        user_id=user_id,
        task_id=task.id,
        runner_session_id=task.runner_session_id,
        level=level,
        stage=stage,
        message=message,
        detail=detail,
    )
    db.add(item)
    return item


def record_outreach_audit(
    db: Session,
    *,
    task: SourcingTask,
    user_id: int,
    actor_type: str,
    action: str,
    detail: str | None = None,
    outreach_id: int | None = None,
    payload: dict | None = None,
) -> SourcingOutreachAudit:
    item = SourcingOutreachAudit(
        user_id=user_id,
        task_id=task.id,
        outreach_id=outreach_id,
        actor_type=actor_type,
        action=action,
        detail=detail,
        payload=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
    )
    db.add(item)
    return item


def save_task_screenshot(
    db: Session,
    *,
    task: SourcingTask,
    user_id: int,
    content_base64: str,
    mime_type: str = "image/png",
    stage: str | None = None,
    caption: str | None = None,
    source_url: str | None = None,
) -> SourcingTaskScreenshot:
    settings = get_settings()
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=400, detail="不支持的截图类型")

    uploads_dir = get_upload_dir() / "sourcing_screenshots" / str(task.user_id) / str(task.id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    try:
        binary = base64.b64decode(content_base64, validate=True)
    except (ValueError, Base64Error):
        raise HTTPException(status_code=400, detail="截图内容不是合法Base64")
    max_size = settings.max_runner_screenshot_size_mb * 1024 * 1024
    if len(binary) > max_size:
        raise HTTPException(status_code=413, detail=f"截图超过大小限制（最大{settings.max_runner_screenshot_size_mb}MB）")
    ext = ".png"
    if mime_type == "image/jpeg":
        ext = ".jpg"
    elif mime_type == "image/webp":
        ext = ".webp"

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = uploads_dir / filename
    file_path.write_bytes(binary)

    screenshot = SourcingTaskScreenshot(
        user_id=user_id,
        task_id=task.id,
        stage=stage,
        caption=caption,
        mime_type=mime_type,
        file_path=str(file_path),
        source_url=source_url,
    )
    db.add(screenshot)
    return screenshot


def task_counts(db: Session, task: SourcingTask) -> dict:
    outreach_rows = db.query(SourcingOutreach).filter(SourcingOutreach.task_id == task.id).all()
    screenshots_count = db.query(SourcingTaskScreenshot).filter(SourcingTaskScreenshot.task_id == task.id).count()
    logs_count = db.query(SourcingTaskLog).filter(SourcingTaskLog.task_id == task.id).count()
    return {
        "pending_outreach_count": sum(1 for item in outreach_rows if item.review_status == OUTREACH_REVIEW_PENDING),
        "approved_outreach_count": sum(
            1
            for item in outreach_rows
            if item.review_status == OUTREACH_REVIEW_APPROVED and item.status == OUTREACH_STATUS_PENDING
        ),
        "failed_outreach_count": sum(1 for item in outreach_rows if item.status == OUTREACH_STATUS_FAILED),
        "screenshots_count": screenshots_count,
        "logs_count": logs_count,
    }


def serialize_platform_account(item: SourcingPlatformAccount | None, platform: str, username: str) -> dict:
    return {
        "id": item.id if item else None,
        "platform": platform,
        "status": item.status if item else "未连接",
        "account_name": item.account_name if item else f"{username}@{platform}",
        "auth_type": item.auth_type if item else "cookie",
        "has_credential": mask_credential(item.credential if item else None),
        "last_sync": item.last_sync.isoformat() if item and item.last_sync else None,
    }


def serialize_log(item: SourcingTaskLog) -> dict:
    return {
        "id": item.id,
        "level": item.level,
        "stage": item.stage,
        "message": item.message,
        "detail": item.detail,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def serialize_screenshot(item: SourcingTaskScreenshot) -> dict:
    return {
        "id": item.id,
        "stage": item.stage,
        "caption": item.caption,
        "source_url": item.source_url,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def serialize_outreach(item: SourcingOutreach, candidate_name: str | None = None) -> dict:
    return {
        "id": item.id,
        "candidate_id": item.candidate_id,
        "candidate_name": candidate_name,
        "platform": item.platform,
        "message": item.message,
        "review_status": item.review_status,
        "status": item.status,
        "profile_url": item.profile_url,
        "failure_reason": item.failure_reason,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
    }


def serialize_outreach_audit(item: SourcingOutreachAudit) -> dict:
    return {
        "id": item.id,
        "outreach_id": item.outreach_id,
        "actor_type": item.actor_type,
        "action": item.action,
        "detail": item.detail,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def serialize_task(db: Session, task: SourcingTask, position: Position | None = None) -> dict:
    counts = task_counts(db, task)
    payload = {
        "id": task.id,
        "position_id": task.position_id,
        "position_title": position.title if position else None,
        "name": task.name,
        "platforms": split_platforms(task.platforms),
        "keywords": task.keywords,
        "locations": task.locations,
        "min_score": task.min_score,
        "target_count": task.target_count,
        "auto_greeting": bool(task.auto_greeting),
        "greeting_template": task.greeting_template,
        "status": task.status,
        "status_detail": task.status_detail,
        "pending_action": task.pending_action,
        "current_platform": task.current_platform,
        "imported_count": task.imported_count,
        "reviewed_count": task.reviewed_count,
        "deduped_count": task.deduped_count,
        "contacted_count": task.contacted_count,
        "last_error": task.last_error,
        "runner_name": task.runner_name,
        "last_heartbeat": task.last_heartbeat.isoformat() if task.last_heartbeat else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }
    payload.update(counts)
    return payload


def build_task_detail(db: Session, task: SourcingTask, position: Position) -> dict:
    payload = serialize_task(db, task, position)
    logs = db.query(SourcingTaskLog).filter(
        SourcingTaskLog.task_id == task.id
    ).order_by(SourcingTaskLog.created_at.desc(), SourcingTaskLog.id.desc()).limit(40).all()
    screenshots = db.query(SourcingTaskScreenshot).filter(
        SourcingTaskScreenshot.task_id == task.id
    ).order_by(SourcingTaskScreenshot.created_at.desc(), SourcingTaskScreenshot.id.desc()).limit(24).all()
    outreach = db.query(SourcingOutreach, Candidate.name).outerjoin(
        Candidate, Candidate.id == SourcingOutreach.candidate_id
    ).filter(
        SourcingOutreach.task_id == task.id
    ).order_by(SourcingOutreach.created_at.desc(), SourcingOutreach.id.desc()).limit(60).all()
    audits = db.query(SourcingOutreachAudit).filter(
        SourcingOutreachAudit.task_id == task.id
    ).order_by(SourcingOutreachAudit.created_at.desc(), SourcingOutreachAudit.id.desc()).limit(80).all()

    payload.update({
        "position_location": position.location,
        "position_department": position.department,
        "position_platform_url": position.platform_url,
        "logs": [serialize_log(item) for item in logs],
        "screenshots": [serialize_screenshot(item) for item in screenshots],
        "outreach": [serialize_outreach(item, candidate_name=name) for item, name in outreach],
        "outreach_audit": [serialize_outreach_audit(item) for item in audits],
    })
    return payload


def build_runner_context(
    db: Session,
    *,
    task: SourcingTask,
    position: Position,
    accounts: list[SourcingPlatformAccount],
) -> dict:
    outreach = db.query(SourcingOutreach).filter(
        SourcingOutreach.task_id == task.id,
        SourcingOutreach.review_status == OUTREACH_REVIEW_APPROVED,
        SourcingOutreach.status == OUTREACH_STATUS_PENDING,
    ).order_by(SourcingOutreach.id.asc()).all()
    return {
        "task": {
            "id": task.id,
            "name": task.name,
            "platforms": split_platforms(task.platforms),
            "keywords": task.keywords,
            "locations": task.locations,
            "min_score": task.min_score,
            "target_count": task.target_count,
            "auto_greeting": bool(task.auto_greeting),
            "greeting_template": task.greeting_template,
            "status": task.status,
            "status_detail": task.status_detail,
            "pending_action": task.pending_action,
            "current_platform": task.current_platform,
        },
        "position": {
            "id": position.id,
            "title": position.title,
            "department": position.department,
            "location": position.location,
            "salary_range": position.salary_range,
            "job_description": position.job_description,
            "requirements": position.requirements,
            "platform_url": position.platform_url,
            "platform_name": position.platform_name,
            "parsing_extra_prompt": position.parsing_extra_prompt,
        },
        "platforms": [
            {
                "platform": item.platform,
                "account_name": item.account_name,
                "auth_type": item.auth_type,
                "credential": decrypt_platform_credential(item.credential),
                "status": item.status,
            }
            for item in accounts
        ],
        "pending_outreach": [
            {
                "id": item.id,
                "candidate_id": item.candidate_id,
                "platform": item.platform,
                "platform_candidate_id": item.platform_candidate_id,
                "profile_url": item.profile_url,
                "message": item.message,
            }
            for item in outreach
        ],
    }


def compute_candidate_fingerprint(payload: dict) -> str:
    platform = normalize_text(payload.get("platform"))
    external_id = normalize_text(payload.get("external_id"))
    if platform and external_id:
        return hashlib.sha256(f"{platform}|{external_id}".encode("utf-8")).hexdigest()

    parts = [
        normalize_text(payload.get("name")),
        normalize_text(payload.get("phone")),
        normalize_text(payload.get("email")),
        normalize_text(payload.get("current_company")),
        normalize_text(payload.get("current_position")),
        normalize_text(payload.get("profile_url")),
    ]
    token = "|".join(part for part in parts if part)
    return hashlib.sha256(token.encode("utf-8")).hexdigest() if token else ""


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip().lower()


def build_greeting_message(task: SourcingTask, position: Position, profile: dict) -> str:
    text = task.greeting_template or (
        "你好{name}，我是{company}的招聘负责人。看到你在{skills}方向的经历，"
        "和我们当前招聘的“{position}”比较匹配，想和你沟通一下机会。"
    )
    skills = "、".join([skill.get("skill_name", "") for skill in profile.get("skills", [])[:3] if skill.get("skill_name")]) or "相关岗位"
    return text.format(
        company=position.department or "招聘团队",
        position=position.title,
        name=profile.get("name") or "你好",
        skills=skills,
        current_company=profile.get("current_company") or "",
        current_position=profile.get("current_position") or "",
        score=profile.get("match_score") or profile.get("score") or "",
    )


def _fallback_profile_from_text(raw_text: str, seed: dict) -> dict:
    phone_match = re.search(r"1[3-9]\d{9}", raw_text)
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw_text)
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    title_line = lines[1] if len(lines) > 1 else (seed.get("current_position") or "平台候选人")
    return {
        "name": seed.get("name") or (lines[0][:50] if lines else "平台候选人"),
        "phone": phone_match.group(0) if phone_match else seed.get("phone"),
        "email": email_match.group(0) if email_match else seed.get("email"),
        "gender": seed.get("gender"),
        "age": seed.get("age"),
        "current_company": seed.get("current_company"),
        "current_position": seed.get("current_position") or title_line[:100],
        "work_years": seed.get("work_years"),
        "self_evaluation": seed.get("self_evaluation") or raw_text[:200],
        "educations": seed.get("educations") or [],
        "experiences": seed.get("experiences") or [],
        "skills": seed.get("skills") or [],
    }


def ensure_profile_structured(raw_payload: dict, position: Position, db: Session, user_id: int) -> dict:
    structured = {
        "name": raw_payload.get("name"),
        "phone": raw_payload.get("phone"),
        "email": raw_payload.get("email"),
        "gender": raw_payload.get("gender"),
        "age": raw_payload.get("age"),
        "current_company": raw_payload.get("current_company"),
        "current_position": raw_payload.get("current_position"),
        "work_years": raw_payload.get("work_years"),
        "self_evaluation": raw_payload.get("self_evaluation"),
        "educations": raw_payload.get("educations") or [],
        "experiences": raw_payload.get("experiences") or [],
        "skills": raw_payload.get("skills") or [],
    }
    has_core = structured["name"] and (structured["current_position"] or structured["current_company"])
    if has_core and structured["skills"]:
        return structured

    try:
        parsed = parse_resume(
            raw_payload.get("raw_text") or "",
            extra_prompt=position.parsing_extra_prompt,
            db=db,
            user_id=user_id,
        )
        return {
            "name": raw_payload.get("name") or parsed.get("name"),
            "phone": raw_payload.get("phone") or parsed.get("phone"),
            "email": raw_payload.get("email") or parsed.get("email"),
            "gender": raw_payload.get("gender") or parsed.get("gender"),
            "age": raw_payload.get("age") or parsed.get("age"),
            "current_company": raw_payload.get("current_company") or parsed.get("current_company"),
            "current_position": raw_payload.get("current_position") or parsed.get("current_position"),
            "work_years": raw_payload.get("work_years") or parsed.get("work_years"),
            "self_evaluation": raw_payload.get("self_evaluation") or parsed.get("self_evaluation"),
            "educations": raw_payload.get("educations") or parsed.get("educations") or [],
            "experiences": raw_payload.get("experiences") or parsed.get("experiences") or [],
            "skills": raw_payload.get("skills") or parsed.get("skills") or [],
        }
    except Exception as e:
        import logging
        logging.warning(f"简历解析失败，使用兜底方案: {type(e).__name__}: {str(e)}")
        return _fallback_profile_from_text(raw_payload.get("raw_text") or "", raw_payload)


def import_runner_candidates(
    db: Session,
    *,
    task: SourcingTask,
    position: Position,
    current_user: User,
    payloads: list[dict],
) -> dict:
    imported = []
    duplicates = []
    filtered = []

    for raw_item in payloads:
        task.reviewed_count += 1
        fingerprint = compute_candidate_fingerprint(raw_item)
        duplicate_query = db.query(Candidate).filter(Candidate.user_id == current_user.id)
        external_id = raw_item.get("external_id")
        if external_id:
            duplicate = duplicate_query.filter(
                Candidate.source_platform == raw_item.get("platform"),
                Candidate.source_uid == external_id,
            ).first()
        else:
            duplicate = duplicate_query.filter(
                Candidate.dedupe_fingerprint == fingerprint
            ).first() if fingerprint else None

        if duplicate:
            task.deduped_count += 1
            duplicates.append({
                "candidate_id": duplicate.id,
                "name": duplicate.name,
                "platform": raw_item.get("platform"),
            })
            continue

        structured = ensure_profile_structured(raw_item, position, db, current_user.id)
        skills = [item for item in (structured.get("skills") or []) if item.get("skill_name")]
        candidate_payload = {
            "name": structured.get("name") or raw_item.get("name") or "平台候选人",
            "phone": structured.get("phone"),
            "email": structured.get("email"),
            "gender": structured.get("gender"),
            "age": structured.get("age"),
            "current_company": structured.get("current_company"),
            "current_position": structured.get("current_position"),
            "work_years": structured.get("work_years"),
            "self_evaluation": structured.get("self_evaluation"),
        }
        match_result = match_candidate_to_position(
            {
                "title": position.title,
                "department": position.department,
                "location": position.location,
                "salary_range": position.salary_range,
                "job_description": position.job_description,
                "requirements": position.requirements,
            },
            candidate_payload,
            educations=structured.get("educations") or [],
            experiences=structured.get("experiences") or [],
            skills=skills,
            db=db,
            user_id=current_user.id,
        )

        if match_result["score"] < task.min_score:
            filtered.append({
                "name": candidate_payload["name"],
                "platform": raw_item.get("platform"),
                "score": match_result["score"],
            })
            continue

        candidate = Candidate(
            name=candidate_payload["name"],
            phone=candidate_payload["phone"],
            email=candidate_payload["email"],
            gender=candidate_payload["gender"],
            age=candidate_payload["age"],
            current_company=candidate_payload["current_company"],
            current_position=candidate_payload["current_position"],
            work_years=candidate_payload["work_years"],
            self_evaluation=candidate_payload["self_evaluation"],
            resume_filename=None,
            resume_raw_text=raw_item.get("raw_text"),
            status="待联系",
            source="平台搜寻",
            source_platform=raw_item.get("platform"),
            source_uid=raw_item.get("external_id"),
            source_profile_url=raw_item.get("profile_url"),
            dedupe_fingerprint=fingerprint or None,
            sourcing_task_id=task.id,
            last_sourced_at=datetime.now(),
            position_id=position.id,
            user_id=current_user.id,
        )
        db.add(candidate)
        db.flush()

        for edu in structured.get("educations") or []:
            db.add(CandidateEducation(
                candidate_id=candidate.id,
                school=edu.get("school") or "未知",
                degree=edu.get("degree") or "未知",
                major=edu.get("major") or "未知",
                start_date=edu.get("start_date"),
                end_date=edu.get("end_date"),
            ))

        for exp in structured.get("experiences") or []:
            db.add(CandidateExperience(
                candidate_id=candidate.id,
                company=exp.get("company") or "未知",
                position=exp.get("position") or "未知",
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                description=exp.get("description"),
            ))

        for skill in skills:
            db.add(CandidateSkill(
                candidate_id=candidate.id,
                skill_name=skill.get("skill_name"),
                proficiency=skill.get("proficiency"),
            ))

        db.add(MatchResult(
            candidate_id=candidate.id,
            position_id=position.id,
            score=match_result["score"],
            analysis=match_result["analysis"],
        ))

        if task.auto_greeting:
            outreach = SourcingOutreach(
                user_id=current_user.id,
                task_id=task.id,
                candidate_id=candidate.id,
                platform=raw_item.get("platform"),
                platform_candidate_id=raw_item.get("external_id"),
                profile_url=raw_item.get("profile_url"),
                message=raw_item.get("greeting_message") or build_greeting_message(task, position, {
                    **candidate_payload,
                    "skills": skills,
                    "match_score": match_result["score"],
                }),
                status=OUTREACH_STATUS_PENDING,
                review_status=OUTREACH_REVIEW_PENDING,
            )
            db.add(outreach)
            db.flush()
            record_outreach_audit(
                db,
                task=task,
                user_id=current_user.id,
                actor_type="system",
                action="created",
                detail=f"为候选人 {candidate.name} 生成待确认外联消息",
                outreach_id=outreach.id,
            )

        task.imported_count += 1
        imported.append({
            "candidate_id": candidate.id,
            "name": candidate.name,
            "platform": raw_item.get("platform"),
            "match_score": match_result["score"],
            "skills": [item.get("skill_name") for item in skills[:5]],
        })

    if task.auto_greeting and imported:
        task.status = TASK_STATUS_WAIT_CONFIRM
        task.pending_action = "confirm_send"
        task.status_detail = "候选人已入库，等待 HR 确认是否发送外联消息"
    elif imported and task.status not in {TASK_STATUS_WAIT_LOGIN, TASK_STATUS_WAIT_CAPTCHA}:
        task.status = TASK_STATUS_RUNNING
        task.pending_action = None
        task.status_detail = "候选人已回传，等待继续抓取或结束任务"

    return {
        "imported_count": len(imported),
        "duplicate_count": len(duplicates),
        "filtered_count": len(filtered),
        "imported_candidates": imported,
        "duplicates": duplicates,
    }
