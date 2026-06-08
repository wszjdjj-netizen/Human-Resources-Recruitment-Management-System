"""
面试管理路由

接口（demo 范围）：
- GET    /api/interviews              列表（全部 HR 可见）
- POST   /api/interviews              新建
- GET    /api/interviews/{id}         详情
- PUT    /api/interviews/{id}         编辑
- DELETE /api/interviews/{id}         删除
- POST   /api/interviews/{id}/start   开始（切状态 + 返回 mock 剧本）
- POST   /api/interviews/{id}/end     结束（保存 transcript）
- POST   /api/interviews/{id}/summarize  生成 AI 总结
- PATCH  /api/interviews/{id}/notes   协作笔记
- GET    /api/interviews/{id}/script  获取内置演示剧本
- GET    /api/interviews/platforms    平台枚举
- GET    /api/candidates/{id}/interviews  候选人历史面试
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.jwt_middleware import get_current_user
from app.models.candidate import Candidate
from app.models.interview import (
    INTERVIEW_PLATFORMS,
    INTERVIEW_STATUS_CANCELLED,
    INTERVIEW_STATUS_LIST,
    INTERVIEW_STATUS_RUNNING,
    INTERVIEW_STATUS_SCHEDULED,
    INTERVIEW_STATUS_SUMMARIZED,
    INTERVIEW_STATUS_TRANSCRIBING,
    Interview,
    InterviewRecord,
)
from app.models.position import Position
from app.models.user import User
from app.schemas.interview import (
    InterviewCreate,
    InterviewListItem,
    InterviewNotesUpdate,
    InterviewResponse,
    InterviewSummaryRequest,
    InterviewSummaryResponse,
    InterviewTranscriptUpdate,
    InterviewUpdate,
    MessageResponse,
    MockScriptLine,
    MockScriptResponse,
)
from app.services.interview_summarizer import summarize_interview


router = APIRouter(prefix="/api", tags=["面试管理"])


# ============== 序列化 ==============

def _serialize_mini_candidate(c: Optional[Candidate]) -> Optional[dict]:
    if not c:
        return None
    return {
        "id": c.id,
        "name": c.name,
        "current_company": c.current_company,
        "current_position": c.current_position,
        "work_years": c.work_years,
    }


def _serialize_mini_position(p: Optional[Position]) -> Optional[dict]:
    if not p:
        return None
    return {
        "id": p.id,
        "title": p.title,
        "department": p.department,
    }


def _serialize_mini_user(u: Optional[User]) -> Optional[dict]:
    if not u:
        return None
    return {
        "id": u.id,
        "username": u.username,
        "full_name": getattr(u, "full_name", None) or u.company_name or u.username,
    }


def _default_title(candidate: Candidate, position: Optional[Position], scheduled_at: datetime) -> str:
    pos_name = position.title if position else "通用岗位"
    return f"{candidate.name} · {pos_name} · {scheduled_at.strftime('%m-%d %H:%M')}"


def _get_owned_candidate(db: Session, candidate_id: int, current_user: User) -> Candidate:
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.user_id == current_user.id,
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return candidate


def _get_owned_position(db: Session, position_id: int, current_user: User) -> Position:
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id,
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="关联岗位不存在")
    return position


def _get_owned_interview(db: Session, interview_id: int, current_user: User) -> Interview:
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id,
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="面试不存在")
    return interview


def _serialize(
    db: Session,
    interview: Interview,
    with_relations: bool = True,
) -> dict:
    data = {
        "id": interview.id,
        "candidate_id": interview.candidate_id,
        "position_id": interview.position_id,
        "user_id": interview.user_id,
        "title": interview.title,
        "platform": interview.platform,
        "meeting_url": interview.meeting_url,
        "scheduled_at": interview.scheduled_at,
        "duration_minutes": interview.duration_minutes,
        "status": interview.status,
        "started_at": interview.started_at,
        "ended_at": interview.ended_at,
        "created_at": interview.created_at,
        "updated_at": interview.updated_at,
    }
    if with_relations:
        candidate = db.query(Candidate).filter(
            Candidate.id == interview.candidate_id,
            Candidate.user_id == interview.user_id,
        ).first()
        position = None
        if interview.position_id:
            position = db.query(Position).filter(
                Position.id == interview.position_id,
                Position.user_id == interview.user_id,
            ).first()
        creator = db.query(User).filter(User.id == interview.user_id).first()
        data["candidate"] = _serialize_mini_candidate(candidate)
        data["position"] = _serialize_mini_position(position)
        data["creator"] = _serialize_mini_user(creator)
    else:
        data["candidate"] = None
        data["position"] = None
        data["creator"] = None
    # 列表场景不查 record；详情场景由调用方再覆盖
    data["record"] = None
    return data


# ============== 平台枚举 ==============

@router.get("/interviews/platforms")
def get_platforms():
    return INTERVIEW_PLATFORMS


# ============== 演示剧本（mock 转写流） ==============

_MOCK_SCRIPTS: List[List[dict]] = [
    # 脚本 1：技术岗
    [
        {"speaker": "面试官", "text": "你好，先做一下自我介绍吧，重点聊聊最近在做的项目。"},
        {"speaker": "候选人", "text": "你好面试官，我叫王磊，目前在一家电商公司担任高级前端工程师，主要负责商家端中后台的架构演进。"},
        {"speaker": "候选人", "text": "最近主导的一个项目是把旧 jQuery 模块逐步迁移到 Vue3 + TypeScript，并且引入 micro-app 做微前端拆分，把首屏加载从 4s 优化到 1.6s。"},
        {"speaker": "面试官", "text": "听起来不错。那在微前主子应用通信上你们怎么做的？有没有踩过什么坑？"},
        {"speaker": "候选人", "text": "通信主要用 props 下发和全局 store 这两种方式。我们用 qiankun 的 initGlobalState 做了 token 同步，避免子应用各自请求刷新。"},
        {"speaker": "候选人", "text": "踩过最大的坑是沙箱逃逸 —— 子应用里直接挂 window.xxx 会污染基座，最后通过严格 lint 规则 + postMessage 隔离解决。"},
        {"speaker": "面试官", "text": "好的。如果让你重新设计一次，你会怎么调整方案？"},
        {"speaker": "候选人", "text": "可能会更早做模块联邦，而不是微前端粒度。另外会先做依赖梳理再启动，避免迁移到一半发现公共包没法复用。"},
        {"speaker": "面试官", "text": "你如何评估一段代码的复杂度，并和团队一起制定技术债的还款计划？"},
        {"speaker": "候选人", "text": "我会用圈复杂度、重复率、依赖深度几个维度打分，把债按业务影响分 P0-P3，每两周迭代里固定留 20% 给技术债。"},
        {"speaker": "面试官", "text": "最后一个问题：你希望下一份工作给你带来什么？"},
        {"speaker": "候选人", "text": "希望参与更复杂的多端场景，同时能在工程效能方向有沉淀，比如内部 CLI、低代码平台。"},
    ],
    # 脚本 2：产品岗
    [
        {"speaker": "面试官", "text": "先聊聊你最近做的最有挑战的产品决策。"},
        {"speaker": "候选人", "text": "好。上一家做 SaaS，我们当时面临一个决策：是把报表功能做成模板化还是支持高度自定义。"},
        {"speaker": "候选人", "text": "我做了两周用户访谈，结论是 80% 的客户用不到自定义，于是选了模板化 + JSON 兜底。"},
        {"speaker": "面试官", "text": "如果老板坚持要做自定义呢？"},
        {"speaker": "候选人", "text": "我会用 ROI 模型把成本和潜在收益摆出来，并且提出分阶段方案，先用低代码做 MVP 验证。"},
        {"speaker": "面试官", "text": "你的产品怎么衡量成功？"},
        {"speaker": "候选人", "text": "北极星指标是周活跃报表数量，再拆留存、复购、跨部门使用率。"},
        {"speaker": "面试官", "text": "和研发冲突时你会怎么处理？"},
        {"speaker": "候选人", "text": "先确认是方案冲突还是目标冲突。如果是目标，我会拉三方对齐；如果是方案，我可以接受技术债，换上线速度。"},
    ],
    # 脚本 3：通用岗
    [
        {"speaker": "面试官", "text": "你为什么考虑看新机会？"},
        {"speaker": "候选人", "text": "主要是希望接触更大的业务规模和更体系化的工程团队。"},
        {"speaker": "面试官", "text": "你最大的优势和短板分别是什么？"},
        {"speaker": "候选人", "text": "优势是跨部门推动能力，能把模糊需求收敛成可执行方案。短板是过于关注细节，有时候会拉长交付周期。"},
        {"speaker": "面试官", "text": "可以接受加班吗？"},
        {"speaker": "候选人", "text": "项目冲刺期可以接受，但更希望从流程上减少不必要的加班。"},
        {"speaker": "面试官", "text": "你有什么问题想问我的？"},
        {"speaker": "候选人", "text": "我想了解下团队目前最大的痛点是什么，以及我入职后最需要解决的第一件事会是什么。"},
    ],
]


@router.get("/interviews/{interview_id}/script", response_model=MockScriptResponse)
def get_mock_script(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_owned_interview(db, interview_id, current_user)
    # 用 interview.id 作为种子让同一场面试拿到同一份剧本
    rng = random.Random(interview_id)
    script = rng.choice(_MOCK_SCRIPTS)
    return {
        "interview_id": interview.id,
        "script": [MockScriptLine(**line) for line in script],
    }


# ============== 候选人历史面试 ==============

@router.get("/candidates/{candidate_id}/interviews", response_model=List[InterviewListItem])
def list_candidate_interviews(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_candidate(db, candidate_id, current_user)
    rows = (
        db.query(Interview)
        .filter(
            Interview.candidate_id == candidate_id,
            Interview.user_id == current_user.id,
        )
        .order_by(Interview.scheduled_at.desc(), Interview.id.desc())
        .all()
    )
    return [_serialize(db, r) for r in rows]


# ============== 列表 ==============

@router.get("/interviews", response_model=List[InterviewListItem])
def list_interviews(
    status: Optional[str] = None,
    candidate_id: Optional[int] = None,
    position_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    仅返回当前登录用户创建的面试，避免多账号部署时数据串看。
    """
    q = db.query(Interview).filter(Interview.user_id == current_user.id)
    if status and status in INTERVIEW_STATUS_LIST:
        q = q.filter(Interview.status == status)
    if candidate_id:
        q = q.filter(Interview.candidate_id == candidate_id)
    if position_id:
        q = q.filter(Interview.position_id == position_id)
    if keyword:
        like = f"%{keyword.strip()}%"
        candidate_ids = [
            c.id for c in
            db.query(Candidate.id).filter(
                Candidate.user_id == current_user.id,
                Candidate.name.like(like),
            ).all()
        ]
        if candidate_ids:
            q = q.filter(
                (Interview.candidate_id.in_(candidate_ids))
                | (Interview.title.like(like))
            )
        else:
            q = q.filter(Interview.title.like(like))
    rows = q.order_by(Interview.scheduled_at.desc(), Interview.id.desc()).all()
    return [_serialize(db, r) for r in rows]


# ============== 详情 ==============

@router.get("/interviews/{interview_id}", response_model=InterviewResponse)
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_owned_interview(db, interview_id, current_user)
    data = _serialize(db, interview)
    # 顺带返回 record（可能为 None）
    record = (
        db.query(InterviewRecord)
        .filter(InterviewRecord.interview_id == interview_id)
        .first()
    )
    data["record"] = _serialize_record(record)
    return data


def _serialize_record(record: Optional[InterviewRecord]) -> Optional[dict]:
    if not record:
        return None
    summary = None
    if record.summary_json:
        try:
            summary = json.loads(record.summary_json)
        except Exception:
            summary = None
    return {
        "id": record.id,
        "interview_id": record.interview_id,
        "transcript": record.transcript,
        "summary": summary,
        "notes": record.notes,
        "summarized_by": record.summarized_by,
        "summarized_at": record.summarized_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


# ============== 新建 ==============

@router.post("/interviews", response_model=InterviewResponse)
def create_interview(
    req: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_owned_candidate(db, req.candidate_id, current_user)
    position = None
    if req.position_id:
        position = _get_owned_position(db, req.position_id, current_user)
    if req.platform not in {p["value"] for p in INTERVIEW_PLATFORMS}:
        raise HTTPException(status_code=400, detail="不支持的会议平台")
    if req.status not in INTERVIEW_STATUS_LIST:
        raise HTTPException(status_code=400, detail="非法的状态值")

    title = req.title or _default_title(candidate, position, req.scheduled_at)

    interview = Interview(
        user_id=current_user.id,
        candidate_id=candidate.id,
        position_id=position.id if position else None,
        title=title,
        platform=req.platform,
        meeting_url=req.meeting_url,
        scheduled_at=req.scheduled_at,
        duration_minutes=req.duration_minutes or 60,
        status=req.status or INTERVIEW_STATUS_SCHEDULED,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return _serialize(db, interview)


# ============== 编辑 ==============

@router.put("/interviews/{interview_id}", response_model=InterviewResponse)
def update_interview(
    interview_id: int,
    req: InterviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_owned_interview(db, interview_id, current_user)
    if req.title is not None:
        interview.title = req.title
    if req.platform is not None:
        if req.platform not in {p["value"] for p in INTERVIEW_PLATFORMS}:
            raise HTTPException(status_code=400, detail="不支持的会议平台")
        interview.platform = req.platform
    if req.meeting_url is not None:
        interview.meeting_url = req.meeting_url
    if req.scheduled_at is not None:
        interview.scheduled_at = req.scheduled_at
    if req.duration_minutes is not None:
        interview.duration_minutes = req.duration_minutes
    if req.status is not None:
        if req.status not in INTERVIEW_STATUS_LIST:
            raise HTTPException(status_code=400, detail="非法的状态值")
        interview.status = req.status
    db.commit()
    db.refresh(interview)
    return _serialize(db, interview)


# ============== 删除 ==============

@router.delete("/interviews/{interview_id}", response_model=MessageResponse)
def delete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_owned_interview(db, interview_id, current_user)
    # 关联 record 一起删
    db.query(InterviewRecord).filter(InterviewRecord.interview_id == interview_id).delete()
    db.delete(interview)
    db.commit()
    return {"message": f"面试 #{interview_id} 已删除", "interview_id": interview_id}


# ============== 开始面试 ==============

@router.post("/interviews/{interview_id}/start", response_model=InterviewResponse)
def start_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_owned_interview(db, interview_id, current_user)
    if interview.status in (INTERVIEW_STATUS_RUNNING, INTERVIEW_STATUS_TRANSCRIBING, INTERVIEW_STATUS_SUMMARIZED):
        raise HTTPException(status_code=400, detail=f"面试当前状态为「{interview.status}」，不可重复开始")
    interview.status = INTERVIEW_STATUS_RUNNING
    interview.started_at = datetime.now()
    interview.ended_at = None
    db.commit()
    db.refresh(interview)

    # 同步把候选人状态改成「面试中」
    candidate = db.query(Candidate).filter(
        Candidate.id == interview.candidate_id,
        Candidate.user_id == current_user.id,
    ).first()
    if candidate and candidate.status in ("待联系", "已联系"):
        candidate.status = "面试中"
        db.commit()

    return _serialize(db, interview)


# ============== 结束面试（保存 transcript） ==============

@router.post("/interviews/{interview_id}/end", response_model=InterviewResponse)
def end_interview(
    interview_id: int,
    req: InterviewTranscriptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_owned_interview(db, interview_id, current_user)
    if interview.status == INTERVIEW_STATUS_SCHEDULED:
        raise HTTPException(status_code=400, detail="面试尚未开始，无法结束")

    record = (
        db.query(InterviewRecord)
        .filter(InterviewRecord.interview_id == interview_id)
        .first()
    )
    if not record:
        record = InterviewRecord(interview_id=interview_id)
        db.add(record)
    record.transcript = req.transcript

    interview.status = INTERVIEW_STATUS_TRANSCRIBING
    interview.ended_at = datetime.now()
    db.commit()
    db.refresh(interview)
    return _serialize(db, interview)


# ============== 生成 AI 总结 ==============

@router.post("/interviews/{interview_id}/summarize", response_model=InterviewSummaryResponse)
def summarize(
    interview_id: int,
    req: InterviewSummaryRequest = InterviewSummaryRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_owned_interview(db, interview_id, current_user)
    record = (
        db.query(InterviewRecord)
        .filter(InterviewRecord.interview_id == interview_id)
        .first()
    )
    if not record or not (record.transcript or "").strip():
        raise HTTPException(status_code=400, detail="请先结束面试并保存转写内容")

    candidate = db.query(Candidate).filter(
        Candidate.id == interview.candidate_id,
        Candidate.user_id == current_user.id,
    ).first()
    position = None
    if interview.position_id:
        position = db.query(Position).filter(
            Position.id == interview.position_id,
            Position.user_id == current_user.id,
        ).first()

    # 是否真的走了 AI：用 record 之前是否已有 summary 判断避免重复计费
    is_mock = bool(record.summary_json)
    summary = summarize_interview(
        transcript=record.transcript or "",
        candidate={
            "name": candidate.name if candidate else "",
            "current_position": candidate.current_position if candidate else "",
            "work_years": candidate.work_years if candidate else 0,
        },
        position={
            "title": position.title if position else "",
            "job_description": position.job_description if position else "",
        },
        extra_context=req.extra_context or "",
        db=db,
        user_id=current_user.id,
    )
    record.summary_json = json.dumps(summary, ensure_ascii=False)
    record.summarized_by = current_user.username or "hr"
    record.summarized_at = datetime.now()
    interview.status = INTERVIEW_STATUS_SUMMARIZED
    db.commit()
    return {
        "interview_id": interview.id,
        "summary": summary,
        "is_mock": is_mock,
        "summarized_at": record.summarized_at,
    }


# ============== 协作笔记 ==============

@router.patch("/interviews/{interview_id}/notes", response_model=MessageResponse)
def update_notes(
    interview_id: int,
    req: InterviewNotesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_owned_interview(db, interview_id, current_user)
    record = (
        db.query(InterviewRecord)
        .filter(InterviewRecord.interview_id == interview_id)
        .first()
    )
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    user = current_user.username or "hr"
    new_line = f"[{now}][{user}] {req.notes.strip()}"
    if not record:
        record = InterviewRecord(interview_id=interview_id, notes=new_line)
        db.add(record)
    else:
        existing = (record.notes or "").rstrip()
        record.notes = (existing + "\n" + new_line).strip() if existing else new_line
    db.commit()
    return {"message": "笔记已保存", "interview_id": interview_id}
