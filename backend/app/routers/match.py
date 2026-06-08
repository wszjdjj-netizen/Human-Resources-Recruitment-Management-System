"""
AI匹配路由：单候选人匹配、批量匹配、匹配结果查看
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.candidate import Candidate
from app.models.position import Position
from app.models.match_result import MatchResult
from app.models.education import CandidateEducation
from app.models.experience import CandidateExperience
from app.models.skill import CandidateSkill
from app.services.ai_matcher import match_candidate_to_position
from app.middleware.jwt_middleware import get_current_user

router = APIRouter(prefix="/api/match", tags=["AI匹配"])


class MatchRequest(BaseModel):
    candidate_id: int
    position_id: int


class BatchMatchRequest(BaseModel):
    position_id: int


@router.post("")
def match_single(
    req: MatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """对单个候选人与职位进行AI匹配打分"""
    # 获取职位信息
    position = db.query(Position).filter(
        Position.id == req.position_id,
        Position.user_id == current_user.id
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    # 获取候选人信息
    candidate = db.query(Candidate).filter(
        Candidate.id == req.candidate_id,
        Candidate.user_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    # 获取候选人的教育/经历/技能
    educations = db.query(CandidateEducation).filter(
        CandidateEducation.candidate_id == candidate.id
    ).all()
    experiences = db.query(CandidateExperience).filter(
        CandidateExperience.candidate_id == candidate.id
    ).all()
    skills = db.query(CandidateSkill).filter(
        CandidateSkill.candidate_id == candidate.id
    ).all()

    try:
        # 调用AI匹配
        result = match_candidate_to_position(
            position={
                "title": position.title,
                "department": position.department,
                "location": position.location,
                "salary_range": position.salary_range,
                "job_description": position.job_description,
                "requirements": position.requirements,
            },
            candidate={
                "name": candidate.name,
                "current_position": candidate.current_position,
                "current_company": candidate.current_company,
                "work_years": candidate.work_years,
                "self_evaluation": candidate.self_evaluation,
            },
            educations=[{"school": e.school, "degree": e.degree, "major": e.major,
                         "start_date": e.start_date, "end_date": e.end_date} for e in educations],
            experiences=[{"company": e.company, "position": e.position,
                          "start_date": e.start_date, "end_date": e.end_date,
                          "description": e.description} for e in experiences],
            skills=[{"skill_name": s.skill_name, "proficiency": s.proficiency} for s in skills],
            db=db,
            user_id=current_user.id,
        )

        # 保存匹配结果（如有旧的则更新）
        existing = db.query(MatchResult).filter(
            MatchResult.candidate_id == candidate.id,
            MatchResult.position_id == position.id
        ).first()
        if existing:
            existing.score = result["score"]
            existing.analysis = result["analysis"]
        else:
            db.add(MatchResult(
                candidate_id=candidate.id,
                position_id=position.id,
                score=result["score"],
                analysis=result["analysis"]
            ))

        db.commit()
        return {"candidate_id": candidate.id, "score": result["score"], "analysis": result["analysis"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI匹配失败：{e}")


@router.post("/batch")
def match_batch(
    req: BatchMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量匹配：对某职位下的所有候选人进行匹配"""
    # 验证职位存在
    position = db.query(Position).filter(
        Position.id == req.position_id,
        Position.user_id == current_user.id
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    # 获取该职位下所有候选人
    candidates = db.query(Candidate).filter(
        Candidate.position_id == req.position_id,
        Candidate.user_id == current_user.id
    ).all()

    if not candidates:
        return {"matched_count": 0, "results": [], "message": "该职位下暂无候选人"}

    matched_count = 0
    results = []

    for candidate in candidates:
        try:
            # 获取关联数据
            educations = db.query(CandidateEducation).filter(
                CandidateEducation.candidate_id == candidate.id
            ).all()
            experiences = db.query(CandidateExperience).filter(
                CandidateExperience.candidate_id == candidate.id
            ).all()
            skills = db.query(CandidateSkill).filter(
                CandidateSkill.candidate_id == candidate.id
            ).all()

            # 调用AI匹配
            result = match_candidate_to_position(
                position={
                    "title": position.title,
                    "department": position.department,
                    "location": position.location,
                    "salary_range": position.salary_range,
                    "job_description": position.job_description,
                    "requirements": position.requirements,
                },
                candidate={
                    "name": candidate.name,
                    "current_position": candidate.current_position,
                    "current_company": candidate.current_company,
                    "work_years": candidate.work_years,
                    "self_evaluation": candidate.self_evaluation,
                },
                educations=[{"school": e.school, "degree": e.degree, "major": e.major,
                             "start_date": e.start_date, "end_date": e.end_date} for e in educations],
                experiences=[{"company": e.company, "position": e.position,
                              "start_date": e.start_date, "end_date": e.end_date,
                              "description": e.description} for e in experiences],
                skills=[{"skill_name": s.skill_name, "proficiency": s.proficiency} for s in skills],
                db=db,
                user_id=current_user.id,
            )

            # 保存匹配结果
            existing = db.query(MatchResult).filter(
                MatchResult.candidate_id == candidate.id,
                MatchResult.position_id == req.position_id
            ).first()
            if existing:
                existing.score = result["score"]
                existing.analysis = result["analysis"]
            else:
                db.add(MatchResult(
                    candidate_id=candidate.id,
                    position_id=req.position_id,
                    score=result["score"],
                    analysis=result["analysis"]
                ))

            matched_count += 1
            results.append({
                "candidate_id": candidate.id,
                "candidate_name": candidate.name,
                "score": result["score"]
            })

        except Exception as e:
            results.append({
                "candidate_id": candidate.id,
                "candidate_name": candidate.name,
                "error": str(e)
            })

    db.commit()
    return {"matched_count": matched_count, "results": results}


@router.get("/position/{position_id}")
def get_position_matches(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取某职位下所有候选人的匹配结果（按分数降序）"""
    results = db.query(
        MatchResult,
        Candidate.name.label("candidate_name")
    ).join(
        Candidate, Candidate.id == MatchResult.candidate_id
    ).filter(
        MatchResult.position_id == position_id,
        Candidate.user_id == current_user.id
    ).order_by(
        MatchResult.score.desc()
    ).all()

    return [{
        "candidate_id": r.MatchResult.candidate_id,
        "candidate_name": r.candidate_name,
        "position_id": r.MatchResult.position_id,
        "score": r.MatchResult.score,
        "analysis": r.MatchResult.analysis,
        "matched_at": r.MatchResult.matched_at.isoformat() if r.MatchResult.matched_at else None
    } for r in results]
