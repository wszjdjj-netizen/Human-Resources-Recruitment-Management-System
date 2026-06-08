"""
简历路由：上传、解析、查看
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.candidate import Candidate
from app.models.education import CandidateEducation
from app.models.experience import CandidateExperience
from app.models.skill import CandidateSkill
from app.models.match_result import MatchResult
from app.models.position import Position
from app.utils.file_handler import delete_uploaded_temp_file, save_upload_file, extract_text, is_allowed_file
from app.services.resume_parser import parse_resume
from app.middleware.jwt_middleware import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/api/resumes", tags=["简历管理"])
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_resumes(
    position_id: int = Query(..., description="关联的职位ID"),
    files: list[UploadFile] = File(..., description="简历文件列表"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量上传简历文件，提取原始文本并创建候选人记录"""
    settings = get_settings()
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    results = []
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id,
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    for file in files:
        # 校验文件类型
        if not is_allowed_file(file.filename):
            results.append({
                "filename": file.filename,
                "error": f"不支持的文件格式，请上传PDF或Word文件"
            })
            continue

        try:
            file_path = None
            # 读取文件内容
            content = await file.read()

            # 验证文件大小
            if len(content) > max_size_bytes:
                results.append({
                    "filename": file.filename,
                    "error": f"文件大小超过限制（最大{settings.max_upload_size_mb}MB）"
                })
                continue

            # 保存文件到磁盘
            file_path = save_upload_file(content, file.filename)

            # 提取文本（使用新的TextExtractionResult）
            extraction = extract_text(file_path)
            try:
                delete_uploaded_temp_file(file_path)
            except Exception:
                logger.warning("临时简历文件清理失败: %s", file_path)
            raw_text = extraction.text

            # 检测空文本情况
            status_msg = "已上传"
            if extraction.is_empty:
                status_msg = f"已上传(⚠️ {extraction.reason})"
                logger.warning(f"简历文件 {file.filename} 文本提取为空: {extraction.reason}")

            # 创建候选人记录（基本信息待AI解析后填充）
            candidate = Candidate(
                name=file.filename.rsplit(".", 1)[0],  # 临时用文件名作为姓名
                resume_filename=file.filename,
                resume_raw_text=raw_text,
                position_id=position_id,
                user_id=current_user.id,
                status="待联系"
            )
            db.add(candidate)
            db.commit()
            db.refresh(candidate)

            results.append({
                "id": candidate.id,
                "filename": file.filename,
                "status": status_msg,
                "text_empty": extraction.is_empty,       # 新增：标记是否为空
                "extraction_reason": extraction.reason if extraction.is_empty else None,  # 新增
            })
        except Exception as e:
            if "file_path" in locals() and file_path:
                try:
                    delete_uploaded_temp_file(file_path)
                except Exception:
                    pass
            results.append({
                "filename": file.filename,
                "error": str(e)
            })

    return results


@router.post("/{candidate_id}/parse")
def parse_candidate_resume(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """使用AI解析候选人简历，提取结构化信息（支持岗位定制提示词）"""
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.user_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    if not candidate.resume_raw_text or not candidate.resume_raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="该简历文件未提取到文本内容（可能是扫描版/图片型PDF）。"
                    "请将PDF转换为可搜索文本的版本，或使用Word格式重新上传。"
        )

    # 获取关联职位的定制解析提示词
    extra_prompt = None
    if candidate.position_id:
        from app.models.position import Position
        position = db.query(Position).filter(
            Position.id == candidate.position_id,
            Position.user_id == current_user.id,
        ).first()
        if position and position.parsing_extra_prompt:
            extra_prompt = position.parsing_extra_prompt

    try:
        # 调用AI解析（传入岗位定制提示词）
        parsed = parse_resume(
            candidate.resume_raw_text,
            extra_prompt=extra_prompt,
            db=db,
            user_id=current_user.id,
        )

        # 更新候选人基本信息
        candidate.name = parsed.get("name") or candidate.name
        candidate.phone = parsed.get("phone")
        candidate.email = parsed.get("email")
        candidate.gender = parsed.get("gender")
        candidate.age = parsed.get("age")
        candidate.current_company = parsed.get("current_company")
        candidate.current_position = parsed.get("current_position")
        candidate.work_years = parsed.get("work_years")
        candidate.self_evaluation = parsed.get("self_evaluation")

        # 清除旧的教育/经历/技能数据（重新解析时覆盖）
        db.query(CandidateEducation).filter(CandidateEducation.candidate_id == candidate_id).delete()
        db.query(CandidateExperience).filter(CandidateExperience.candidate_id == candidate_id).delete()
        db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).delete()

        # 添加教育经历
        for edu in parsed.get("educations", []):
            db.add(CandidateEducation(
                candidate_id=candidate_id,
                school=edu.get("school") or "未知学校",
                degree=edu.get("degree") or "未知学历",
                major=edu.get("major") or "未知专业",
                start_date=edu.get("start_date"),
                end_date=edu.get("end_date")
            ))

        # 添加工作经历
        for exp in parsed.get("experiences", []):
            db.add(CandidateExperience(
                candidate_id=candidate_id,
                company=exp.get("company") or "未知公司",
                position=exp.get("position") or "未知职位",
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                description=exp.get("description")
            ))

        # 添加技能
        for skill in parsed.get("skills", []):
            skill_name = skill.get("skill_name")
            if not skill_name:
                continue
            db.add(CandidateSkill(
                candidate_id=candidate_id,
                skill_name=skill_name,
                proficiency=skill.get("proficiency")
            ))

        db.commit()
        db.refresh(candidate)

        return _build_candidate_detail(candidate, db)

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"简历解析失败: {type(e).__name__}: {str(e)}", exc_info=True)
        # 把真实错误原因返回给前端，方便排查（特别是AI Key/网络问题）
        err_msg = str(e)
        # 针对常见错误给出更友好的提示
        if "AI API密钥未配置" in err_msg or "your-api-key" in err_msg or "401" in err_msg or "Authentication" in err_msg:
            detail = "AI 接口未授权（API Key 无效或占位符）。请到「AI 配置」页面填入真实 API Key 后重试。"
        elif "未提取到文本" in err_msg or "扫描版" in err_msg:
            detail = err_msg
        elif "JSON" in err_msg:
            detail = f"AI 返回的内容无法解析为 JSON：{err_msg[:200]}"
        else:
            detail = f"简历解析失败：{err_msg[:300]}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/{candidate_id}")
def get_resume_detail(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取候选人简历详情（含解析后的结构化数据）"""
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.user_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    return _build_candidate_detail(candidate, db)


def _build_candidate_detail(candidate: Candidate, db: Session) -> dict:
    """构建候选人详情响应"""
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
    match_result = db.query(MatchResult).filter(
        MatchResult.candidate_id == candidate.id
    ).order_by(
        MatchResult.matched_at.desc()
    ).first()

    # 解析 dimension_scores（仅工作流匹配时存储在 analysis 字段中）
    dimension_scores = None
    if match_result and match_result.analysis:
        try:
            import re as _re
            # 工作流匹配时在 analysis 开头插入 [DIM_SCORES]{json}[/DIM_SCORES] 标记
            m = _re.search(r'\[DIM_SCORES\](.*?)\[/DIM_SCORES\]', match_result.analysis, _re.DOTALL)
            if m:
                dimension_scores = json.loads(m.group(1))
                # 从 analysis 中移除标记，仅显示正文
                match_result.analysis = _re.sub(r'\[DIM_SCORES\].*?\[/DIM_SCORES\]\s*', '', match_result.analysis, flags=_re.DOTALL)
        except Exception:
            pass

    return {
        "id": candidate.id,
        "name": candidate.name,
        "phone": candidate.phone,
        "email": candidate.email,
        "gender": candidate.gender,
        "age": candidate.age,
        "current_company": candidate.current_company,
        "current_position": candidate.current_position,
        "work_years": candidate.work_years,
        "self_evaluation": candidate.self_evaluation,
        "status": candidate.status,
        "position_id": candidate.position_id,
        "source": candidate.source,
        "resume_filename": candidate.resume_filename,
        "match_score": match_result.score if match_result else None,
        "educations": [{
            "id": e.id, "school": e.school, "degree": e.degree,
            "major": e.major, "start_date": e.start_date, "end_date": e.end_date
        } for e in educations],
        "experiences": [{
            "id": e.id, "company": e.company, "position": e.position,
            "start_date": e.start_date, "end_date": e.end_date, "description": e.description
        } for e in experiences],
        "skills": [{
            "id": s.id, "skill_name": s.skill_name, "proficiency": s.proficiency
        } for s in skills],
        "match_result": {
            "id": match_result.id,
            "score": match_result.score,
            "analysis": match_result.analysis,
            "matched_at": match_result.matched_at.isoformat() if match_result.matched_at else None
        } if match_result else None,
        "dimension_scores": dimension_scores,
        "created_at": candidate.created_at.isoformat() if candidate.created_at else None
    }
