"""
职位管理路由：CRUD操作 + JD智能解析
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.position import Position
from app.models.candidate import Candidate
from app.schemas.position import (
    PositionCreate, PositionUpdate, PositionResponse,
    JDParseRequest, JDParseResponse
)
from app.services.jd_parser import parse_jd
from app.middleware.jwt_middleware import get_current_user

router = APIRouter(prefix="/api/positions", tags=["职位管理"])


VALID_POSITION_STATUSES = {"开放", "关闭"}


def _normalize_position_status(status_value: str | None) -> str:
    """Keep position status values consistent across create/list/stats."""
    if not status_value:
        return "开放"
    normalized = status_value.strip()
    return normalized if normalized in VALID_POSITION_STATUSES else "开放"


@router.get("", response_model=list[PositionResponse])
def list_positions(
    status: str | None = Query(None, description="职位状态筛选"),
    search: str | None = Query(None, description="搜索职位名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取职位列表（仅当前用户）"""
    query = db.query(Position).filter(Position.user_id == current_user.id)

    if status:
        query = query.filter(Position.status == _normalize_position_status(status))
    if search:
        query = query.filter(Position.title.like(f"%{search}%"))

    return query.order_by(Position.created_at.desc()).all()


@router.get("/stats/summary")
def position_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取首页统计，职位数量与职位管理默认列表保持同一口径"""
    positions = db.query(Position).filter(Position.user_id == current_user.id).all()
    open_positions = [p for p in positions if _normalize_position_status(p.status) == "开放"]
    position_ids = [p.id for p in open_positions]

    candidates = db.query(Candidate).filter(Candidate.user_id == current_user.id).all()
    distribution = []
    for position in positions:
        count = sum(1 for candidate in candidates if candidate.position_id == position.id)
        if count > 0:
            distribution.append({
                "title": position.title,
                "status": _normalize_position_status(position.status),
                "count": count,
            })

    return {
        "position_count": len(positions),
        "open_position_count": len(open_positions),
        "candidate_count": len(candidates),
        "contacted_count": sum(1 for c in candidates if c.status in ["待联系", "已联系", "面试中"]),
        "passed_count": sum(1 for c in candidates if c.status == "已通过"),
        "position_distribution": distribution,
        "open_position_ids": position_ids,
    }


@router.post("", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
def create_position(
    req: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新职位"""
    position = Position(
        title=req.title,
        department=req.department,
        location=req.location,
        salary_range=req.salary_range,
        job_description=req.job_description,
        requirements=req.requirements,
        status=_normalize_position_status(req.status),
        headcount=req.headcount,
        parsing_extra_prompt=req.parsing_extra_prompt,
        platform_url=req.platform_url,
        platform_name=req.platform_name,
        user_id=current_user.id
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


@router.post("/parse-jd", response_model=JDParseResponse)
def parse_jd_endpoint(
    req: JDParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    智能解析JD文本或URL，提取结构化职位信息（不保存到数据库，仅返回解析结果）
    支持：1. 粘贴JD文本  2. 粘贴招聘平台职位链接
    """
    if not req.text and not req.url:
        raise HTTPException(status_code=400, detail="请提供JD文本或职位链接")

    try:
        result = parse_jd(text=req.text, url=req.url, db=db, user_id=current_user.id)
        return JDParseResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JD解析失败：{e}")


@router.get("/{position_id}", response_model=PositionResponse)
def get_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取职位详情"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    return position


@router.put("/{position_id}", response_model=PositionResponse)
def update_position(
    position_id: int,
    req: PositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新职位"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    # 只更新非空字段
    update_data = req.model_dump(exclude_none=True)
    if "status" in update_data:
        update_data["status"] = _normalize_position_status(update_data["status"])
    for key, value in update_data.items():
        setattr(position, key, value)

    db.commit()
    db.refresh(position)
    return position


@router.delete("/{position_id}")
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除职位"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    db.delete(position)
    db.commit()
    return {"message": "删除成功"}
