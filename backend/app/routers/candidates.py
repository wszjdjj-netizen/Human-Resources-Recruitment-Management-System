"""
候选人管理路由（人才池）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models.user import User
from app.models.candidate import Candidate
from app.models.education import CandidateEducation
from app.models.experience import CandidateExperience
from app.models.skill import CandidateSkill
from app.models.match_result import MatchResult
from app.models.position import Position
from app.schemas.candidate import CandidateUpdate, CandidateBatchDelete
from app.middleware.jwt_middleware import get_current_user

router = APIRouter(prefix="/api/candidates", tags=["候选人管理"])


# 有效的状态流转
VALID_STATUS_TRANSITIONS = {
    "待联系": ["已联系", "已淘汰"],
    "已联系": ["面试中", "已淘汰"],
    "面试中": ["已通过", "已淘汰"],
    "已通过": [],  # 终态，不可变更
    "已淘汰": [],  # 终态，不可变更
}


@router.get("")
def list_candidates(
    position_id: int | None = Query(None, description="按职位ID筛选"),
    status: str | None = Query(None, description="按状态筛选"),
    search: str | None = Query(None, description="搜索姓名/邮箱/电话"),
    matched_only: bool = Query(False, description="仅返回已匹配候选人"),
    sort_by: str | None = Query("created_at", description="排序字段：match_score 或 created_at"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取候选人列表（人才池）"""
    from sqlalchemy import func

    # 子查询：获取每个候选人的最新匹配分数
    latest_match_subq = db.query(
        MatchResult.candidate_id,
        MatchResult.score,
        func.row_number().over(
            partition_by=MatchResult.candidate_id,
            order_by=MatchResult.matched_at.desc()
        ).label('rn')
    ).subquery()

    # 基础查询：仅查询当前用户的候选人，关联最新的匹配结果
    query = db.query(
        Candidate,
        latest_match_subq.c.score.label("match_score")
    ).outerjoin(
        latest_match_subq,
        (latest_match_subq.c.candidate_id == Candidate.id) &
        (latest_match_subq.c.rn == 1)
    ).filter(
        Candidate.user_id == current_user.id
    )

    # 筛选条件
    if position_id:
        query = query.filter(Candidate.position_id == position_id)
    if status:
        query = query.filter(Candidate.status == status)
    if search:
        # 限制搜索关键词长度，防止性能攻击
        search_term = search.strip()[:50]
        # 转义特殊字符，防止SQL注入
        search_term = search_term.replace('%', r'\%').replace('_', r'\_')
        query = query.filter(
            (Candidate.name.like(f"%{search_term}%", escape='\\')) |
            (Candidate.email.like(f"%{search_term}%", escape='\\')) |
            (Candidate.phone.like(f"%{search_term}%", escape='\\'))
        )
    if matched_only:
        query = query.filter(latest_match_subq.c.score.isnot(None))

    # 排序
    if sort_by == "match_score":
        query = query.order_by(desc("match_score"), desc(Candidate.created_at))
    else:
        query = query.order_by(desc(Candidate.created_at))

    # 总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()

    # 批量补充技能标签，避免列表页为了看标签再进入详情页
    candidate_ids = [cand.id for cand, _ in results]
    skills_by_candidate: dict[int, list[dict]] = {}
    if candidate_ids:
        skill_rows = db.query(CandidateSkill).filter(
            CandidateSkill.candidate_id.in_(candidate_ids)
        ).order_by(CandidateSkill.candidate_id, CandidateSkill.id).all()
        for skill in skill_rows:
            bucket = skills_by_candidate.setdefault(skill.candidate_id, [])
            if len(bucket) < 5:
                bucket.append({
                    "id": skill.id,
                    "skill_name": skill.skill_name,
                    "proficiency": skill.proficiency
                })

    # 构建响应
    items = []
    for cand, score in results:
        items.append({
            "id": cand.id,
            "name": cand.name,
            "phone": cand.phone,
            "email": cand.email,
            "current_company": cand.current_company,
            "current_position": cand.current_position,
            "work_years": cand.work_years,
            "status": cand.status,
            "position_id": cand.position_id,
            "source": cand.source,
            "match_score": score,
            "skills": skills_by_candidate.get(cand.id, []),
            "created_at": cand.created_at.isoformat() if cand.created_at else None
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{candidate_id}")
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取候选人详情（含教育/经历/技能/匹配结果）"""
    # 复用 resumes 模块的详情构建函数
    from app.routers.resumes import _build_candidate_detail

    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.user_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    return _build_candidate_detail(candidate, db)


@router.put("/{candidate_id}")
def update_candidate(
    candidate_id: int,
    req: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新候选人状态"""
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.user_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    # 校验状态流转
    if req.status not in ["待联系", "已联系", "面试中", "已通过", "已淘汰"]:
        raise HTTPException(status_code=400, detail="无效的状态值")

    allowed = VALID_STATUS_TRANSITIONS.get(candidate.status, [])
    if allowed and req.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不允许从「{candidate.status}」变更为「{req.status}」，允许的变更：{allowed}"
        )

    candidate.status = req.status
    db.commit()
    db.refresh(candidate)

    return {"id": candidate.id, "status": candidate.status, "message": "状态更新成功"}


@router.post("/batch-delete")
def batch_delete_candidates(
    req: CandidateBatchDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量删除候选人"""
    candidates = db.query(Candidate).filter(
        Candidate.id.in_(req.ids),
        Candidate.user_id == current_user.id
    ).all()
    if not candidates:
        raise HTTPException(status_code=404, detail="候选人不存在")

    candidate_ids = [c.id for c in candidates]
    db.query(MatchResult).filter(MatchResult.candidate_id.in_(candidate_ids)).delete(synchronize_session=False)
    db.query(CandidateSkill).filter(CandidateSkill.candidate_id.in_(candidate_ids)).delete(synchronize_session=False)
    db.query(CandidateExperience).filter(CandidateExperience.candidate_id.in_(candidate_ids)).delete(synchronize_session=False)
    db.query(CandidateEducation).filter(CandidateEducation.candidate_id.in_(candidate_ids)).delete(synchronize_session=False)
    db.query(Candidate).filter(Candidate.id.in_(candidate_ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": "批量删除成功", "deleted_count": len(candidate_ids)}


@router.delete("/{candidate_id}")
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除候选人"""
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.user_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    db.query(MatchResult).filter(MatchResult.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(CandidateExperience).filter(CandidateExperience.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(CandidateEducation).filter(CandidateEducation.candidate_id == candidate_id).delete(synchronize_session=False)
    db.delete(candidate)
    db.commit()
    return {"message": "删除成功"}
